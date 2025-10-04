import os
import json
import re
import shutil
import asyncio
import datetime as dt
from typing import Any, Dict, Optional, Tuple

import discord
from discord import app_commands, Interaction, Embed, Colour
from discord.ext import commands, tasks
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# ===== 설정 =====
DATA_PATH = "data.json"
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

ROBLOX_LOGIN_URLS = ["https://www.roblox.com/ko/Login", "https://www.roblox.com/Login"]
ROBLOX_TX_URLS = ["https://www.roblox.com/ko/transactions", "https://www.roblox.com/transactions"]

BALANCE_CACHE_TTL_SEC = 30
PAGE_TIMEOUT = 15000
UPDATE_INTERVAL_SEC = 60

NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

# ===== 저장소 유틸 =====
def _default_data() -> Dict[str, Any]:
    return {
        "users": {},  # { userId: { "roblox": {"username","password","cookie_raw","masked_cookie","cookie_set_at"}, "last_embed": {"channel_id","message_id"} } }
        "stats": {"total_sold": 0},  # 유지: 총 판매량 필드(표시만; 누적 명령 제거됨)
        "cache": {"balances": {}},   # { userId: {"value": int, "ts": iso} }
        "meta": {"version": 1}
    }

def _atomic_write(path: str, data: Dict[str, Any]):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    shutil.move(tmp, path)

def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_PATH):
        d = _default_data()
        _atomic_write(DATA_PATH, d)
        return d
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        d = _default_data()
        _atomic_write(DATA_PATH, d)
        return d

def save_data(d: Dict[str, Any]):
    _atomic_write(DATA_PATH, d)

def mask_cookie(cookie: str) -> str:
    if not cookie or len(cookie) < 7:
        return "***"
    return cookie[:3] + "***" + cookie[-3:]

def get_user_block(uid: int) -> Dict[str, Any]:
    d = load_data()
    return d["users"].get(str(uid), {})

def set_user_block(uid: int, block: Dict[str, Any]):
    d = load_data()
    d["users"][str(uid)] = block
    save_data(d)

def set_user_cookie(uid: int, cookie: str, username_hint: Optional[str] = None):
    u = get_user_block(uid)
    r = u.get("roblox", {})
    r["cookie_raw"] = cookie
    r["masked_cookie"] = mask_cookie(cookie)
    r["cookie_set_at"] = dt.datetime.utcnow().isoformat()
    if username_hint:
        r["username"] = username_hint
    u["roblox"] = r
    set_user_block(uid, u)

def set_user_login(uid: int, username: str, password: str):
    u = get_user_block(uid)
    r = u.get("roblox", {})
    r["username"] = username
    r["password"] = password
    u["roblox"] = r
    set_user_block(uid, u)

def set_last_embed(uid: int, channel_id: int, message_id: int):
    u = get_user_block(uid)
    u["last_embed"] = {"channel_id": channel_id, "message_id": message_id}
    set_user_block(uid, u)

def get_last_embed(uid: int) -> Optional[Dict[str, int]]:
    u = get_user_block(uid)
    return u.get("last_embed")

def get_total_sold() -> int:
    d = load_data()
    return int(d.get("stats", {}).get("total_sold", 0))

def cache_balance(uid: int, value: int):
    d = load_data()
    d["cache"].setdefault("balances", {})
    d["cache"]["balances"][str(uid)] = {"value": int(value), "ts": dt.datetime.utcnow().isoformat()}
    save_data(d)

def get_cached_balance(uid: int) -> Optional[int]:
    d = load_data()
    item = d.get("cache", {}).get("balances", {}).get(str(uid))
    if not item:
        return None
    try:
        ts = dt.datetime.fromisoformat(item["ts"])
    except Exception:
        return None
    if (dt.datetime.utcnow() - ts).total_seconds() <= BALANCE_CACHE_TTL_SEC:
        return int(item["value"])
    return None

# ===== Roblox 조회 =====
async def _extract_numbers_from_page(page: Page) -> Optional[int]:
    html = await page.content()
    nums = []
    for m in NUM_RE.finditer(html):
        raw = m.group(1)
        val = int(re.sub(r"[,\.\s]", "", raw))
        nums.append(val)
    if not nums:
        return None
    return max(nums)

async def _open_with_cookie(context: BrowserContext, cookie_raw: str) -> Optional[int]:
    try:
        await context.add_cookies([{
            "name": ".ROBLOSECURITY",
            "value": cookie_raw,
            "domain": ".roblox.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        }])
        page = await context.new_page()
        for url in ROBLOX_TX_URLS:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
                break
            except Exception:
                continue
        bal = await _extract_numbers_from_page(page)
        await page.close()
        return bal
    except Exception:
        return None

async def _login_with_idpw(context: BrowserContext, username: str, password: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    ok, bal, cookie_val, username_hint = False, None, None, None
    page = await context.new_page()
    for url in ROBLOX_LOGIN_URLS:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            break
        except Exception:
            continue
    user_sel = "input[name='username'], input#login-username, input[type='text']"
    pass_sel = "input[name='password'], input#login-password, input[type='password']"
    try:
        await page.wait_for_selector(user_sel, timeout=PAGE_TIMEOUT)
        await page.fill(user_sel, username)
        await page.wait_for_selector(pass_sel, timeout=PAGE_TIMEOUT)
        await page.fill(pass_sel, password)
        login_btn = "button[type='submit'], button[aria-label], button:has-text('로그인'), button:has-text('Log In')"
        await page.click(login_btn)
    except Exception:
        await page.close()
        return ok, bal, cookie_val, username_hint
    try:
        await page.wait_for_load_state("networkidle", timeout=PAGE_TIMEOUT)
    except Exception:
        pass
    try:
        for url in ROBLOX_TX_URLS:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
                break
            except Exception:
                continue
        bal = await _extract_numbers_from_page(page)
        cookies = await context.cookies()
        for c in cookies:
            if c.get("name") == ".ROBLOSECURITY":
                cookie_val = c.get("value")
                break
        try:
            title = await page.title()
            if title:
                m = re.search(r"[A-Za-z0-9_]{3,20}", title)
                if m:
                    username_hint = m.group(0)
        except Exception:
            pass
        ok = True if bal is not None else False
    finally:
        await page.close()
    return ok, bal, cookie_val, username_hint

async def fetch_balance(uid: int) -> Optional[int]:
    cached = get_cached_balance(uid)
    if cached is not None:
        return cached
    info = get_user_block(uid).get("roblox", {})
    cookie_raw = info.get("cookie_raw")
    username = info.get("username")
    password = info.get("password")
    try:
        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(headless=True)
            context: BrowserContext = await browser.new_context()
            if cookie_raw:
                bal = await _open_with_cookie(context, cookie_raw)
                await browser.close()
                if isinstance(bal, int):
                    cache_balance(uid, bal)
                    return bal
            if username and password:
                ok, bal, new_cookie, uname_hint = await _login_with_idpw(context, username, password)
                await browser.close()
                if ok:
                    if new_cookie:
                        set_user_cookie(uid, new_cookie, uname_hint)
                    if isinstance(bal, int):
                        cache_balance(uid, bal)
                        return bal
                return None
            await browser.close()
            return None
    except Exception:
        return None

# ===== Discord Bot =====
INTENTS = discord.Intents.default()
BOT = commands.Bot(command_prefix="!", intents=INTENTS)
TREE = BOT.tree

# 자동 업데이트 추적 { userId(str): {"guild_id": int, "channel_id": int, "message_id": int} }
active_updates: Dict[str, Dict[str, int]] = {}

def build_stock_embed(guild: Optional[discord.Guild], robux_balance: Optional[int], total_sold: int) -> Embed:
    # 색상 ff5dd6
    colour = discord.Colour(int("ff5dd6", 16))
    emb = Embed(title="", colour=colour, timestamp=dt.datetime.utcnow())

    # 서버프사/서버이름 작게 (author + thumbnail)
    if guild:
        emb.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else discord.Embed.Empty)
        if guild.icon:
            emb.set_thumbnail(url=guild.icon.url)

    # 본문: 요청 포맷 그대로
    stock = "불러오기 실패"
    if isinstance(robux_balance, int):
        stock = f"{robux_balance:,}"
    total = f"{total_sold:,}"

    desc = []
    desc.append("## <a:upuoipipi:1423892277373304862>실시간 로벅스 재고")
    desc.append("### <a:thumbsuppp:1423892279612936294>로벅스 재고")
    desc.append(f"<a:sakfnmasfagfamg:1423892278677602435>**`{stock}`로벅스** ( 60초 마다 갱신 )")
    desc.append("### <a:upuoipipi:1423892277373304862>총 로벅스 판매량")
    desc.append(f"<a:sakfnmasfagfamg:1423892278677602435>**`{total}`로벅스** ( 60초 마다 갱신 )")

    emb.description = "\n".join(desc)
    return emb

async def upsert_public_embed(inter: Interaction, uid: int, force_new: bool = False):
    bal = await fetch_balance(uid)
    total = get_total_sold()
    embed = build_stock_embed(inter.guild, bal, total)

    # 공개 메시지
    if force_new or not get_last_embed(uid):
        msg = await inter.channel.send(embed=embed)
        set_last_embed(uid, inter.channel.id, msg.id)
        active_updates[str(uid)] = {"guild_id": inter.guild_id, "channel_id": inter.channel.id, "message_id": msg.id}
        return

    last = get_last_embed(uid)
    try:
        ch = await BOT.fetch_channel(last["channel_id"])
        msg = await ch.fetch_message(last["message_id"])
        await msg.edit(embed=embed)
        active_updates[str(uid)] = {"guild_id": inter.guild_id, "channel_id": ch.id, "message_id": msg.id}
    except Exception:
        msg = await inter.channel.send(embed=embed)
        set_last_embed(uid, inter.channel.id, msg.id)
        active_updates[str(uid)] = {"guild_id": inter.guild_id, "channel_id": inter.channel.id, "message_id": msg.id}

@tasks.loop(seconds=UPDATE_INTERVAL_SEC)
async def updater_loop():
    for uid, loc in list(active_updates.items()):
        try:
            user_id = int(uid)
            # 최신 값
            bal = await fetch_balance(user_id)
            total = get_total_sold()
            # Guild 객체 없이도 안전하게 편집
            ch = await BOT.fetch_channel(loc["channel_id"])
            msg = await ch.fetch_message(loc["message_id"])
            # 가능한 guild 얻기
            guild = msg.guild if hasattr(msg, "guild") else None
            embed = build_stock_embed(guild, bal, total)
            await msg.edit(embed=embed)
        except Exception:
            continue

async def sync_tree():
    try:
        if GUILD_ID:
            await TREE.sync(guild=discord.Object(id=GUILD_ID))
        else:
            await TREE.sync()
    except Exception as e:
        print("Command sync err:", e)

@BOT.event
async def on_ready():
    load_data()
    print(f"Logged in as {BOT.user} (data.json ready)")
    await sync_tree()
    if not updater_loop.is_running():
        updater_loop.start()

# ===== 명령어 =====
@TREE.command(name="실시간_재고_설정", description="Roblox 실시간 재고 연동을 설정합니다. (cookie 또는 login)")
@app_commands.describe(mode="cookie 또는 login", cookie=".ROBLOSECURITY 값", id="Roblox 아이디", pw="Roblox 비밀번호")
async def cmd_setup(inter: Interaction, mode: str, cookie: Optional[str] = None, id: Optional[str] = None, pw: Optional[str] = None):
    mode = (mode or "").lower().strip()
    if mode not in ("cookie", "login"):
        await inter.response.send_message("mode는 cookie 또는 login 중 하나야.", ephemeral=True)
        return

    if mode == "cookie":
        if not cookie:
            await inter.response.send_message("cookie(.ROBLOSECURITY) 값을 넣어줘.", ephemeral=True)
            return
        set_user_cookie(inter.user.id, cookie)
        await inter.response.send_message(f"쿠키 저장 완료! /재고표시로 확인 가능. (저장: {mask_cookie(cookie)})", ephemeral=True)
        return

    if mode == "login":
        if not id or not pw:
            await inter.response.send_message("login 모드는 id, pw 모두 필요해.", ephemeral=True)
            return
        set_user_login(inter.user.id, id, pw)
        await inter.response.send_message("로그인 정보 저장 완료! /재고표시로 불러올게.", ephemeral=True)

@TREE.command(name="재고표시", description="실시간 로벅스 재고 임베드를 공개로 표시합니다.")
async def cmd_show(inter: Interaction):
    await inter.response.defer(thinking=True, ephemeral=False)
    await upsert_public_embed(inter, inter.user.id, force_new=True)
    await inter.followup.send("재고 임베드가 공개로 표시됐어. 60초마다 자동 갱신해.", ephemeral=True)

# /판매_누적 명령어는 요청대로 제거

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN이 비어있거나 형식이 이상함.")
    BOT.run(TOKEN)

if __name__ == "__main__":
    main()
