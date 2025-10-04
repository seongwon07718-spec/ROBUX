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

# ========== 설정 ==========
DATA_PATH = "data.json"
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

ROBLOX_LOGIN_URLS = ["https://www.roblox.com/ko/Login", "https://www.roblox.com/Login"]
ROBLOX_TX_URLS = ["https://www.roblox.com/ko/transactions", "https://www.roblox.com/transactions"]

BALANCE_CACHE_TTL_SEC = 30
PAGE_TIMEOUT = 15000
UPDATE_INTERVAL_SEC = 60  # 60초마다 실시간 업데이트

NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

# ========== 저장소 ==========
def _default_data() -> Dict[str, Any]:
    return {
        "users": {},  # { userId: { "roblox": {"username","password","cookie_raw","masked_cookie","cookie_set_at"}, "last_embed": {"channel_id","message_id"} } }
        "stats": {"total_sold": 0},
        "cache": {"balances": {}},  # { userId: {"value": int, "ts": iso} }
        "meta": {"version": 1}
    }

def _atomic_write(path: str, data: Dict[str, Any]):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    shutil.move(tmp, path)

def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_PATH):
        data = _default_data()
        _atomic_write(DATA_PATH, data)
        return data
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        data = _default_data()
        _atomic_write(DATA_PATH, data)
        return data

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

def set_total_sold(val: int):
    d = load_data()
    d["stats"]["total_sold"] = int(val)
    save_data(d)

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

# ========== Roblox 조회 ==========
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
            # 쿠키 우선
            if cookie_raw:
                bal = await _open_with_cookie(context, cookie_raw)
                await browser.close()
                if isinstance(bal, int):
                    cache_balance(uid, bal)
                    return bal
            # 로그인 폴백
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

# ========== Discord Bot ==========
INTENTS = discord.Intents.default()
BOT = commands.Bot(command_prefix="!", intents=INTENTS)
TREE = BOT.tree

# 유저별 자동 업데이트 태스크 상태
# { userId: {"guild_id": int, "channel_id": int, "message_id": int} }
active_updates: Dict[str, Dict[str, int]] = {}

def build_stock_embed(robux_balance: Optional[int], total_sold: int) -> Embed:
    # 형식 그대로(볼드/코드블록/구분선/링크) + 회색
    emb = Embed(title="실시간 로벅스 재고", colour=Colour.dark_grey(), timestamp=dt.datetime.utcnow())
    # 본문은 설명 또는 필드 조합으로 구현
    # 요구 포맷:
    # **로벅스 수량**
    # `디비값`로벅스
    # ——————————
    # **총 판매량**
    # `디비값`로벅스
    # ——————————
    # [로벅스 구매 바로가기](디스코드 채널 링크)
    stock = "불러오기 실패"
    if isinstance(robux_balance, int):
        stock = f"{robux_balance:,}"
    total = f"{total_sold:,}"

    desc_lines = [
        "**로벅스 수량**",
        f"`{stock}`로벅스",
        "——————————",
        "**총 판매량**",
        f"`{total}`로벅스",
        "——————————",
        "[로벅스 구매 바로가기](https://discord.com/channels/1419200424636055592/1419235238512427083)",
    ]
    emb.description = "\n".join(desc_lines)
    return emb

async def send_or_edit_stock(inter: Interaction, uid: int, force_new: bool = False):
    # 최신 잔액 조회
    bal = await fetch_balance(uid)
    total = get_total_sold()
    embed = build_stock_embed(bal, total)

    # 공개 메시지로 보내기(모든 유저 보이게)
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
        # 기존 메시지 못 찾으면 새로 보냄
        msg = await inter.channel.send(embed=embed)
        set_last_embed(uid, inter.channel.id, msg.id)
        active_updates[str(uid)] = {"guild_id": inter.guild_id, "channel_id": inter.channel.id, "message_id": msg.id}

@tasks.loop(seconds=UPDATE_INTERVAL_SEC)
async def updater_loop():
    # 등록된 사용자들 메시지를 60초마다 갱신
    for uid, loc in list(active_updates.items()):
        try:
            user_id = int(uid)
            # 최신 값
            bal = await fetch_balance(user_id)
            total = get_total_sold()
            embed = build_stock_embed(bal, total)
            ch = await BOT.fetch_channel(loc["channel_id"])
            msg = await ch.fetch_message(loc["message_id"])
            await msg.edit(embed=embed)
        except Exception:
            # 실패하면 일단 계속 진행(한두 번 튕겨도 다음 주기에 복구 가능)
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

# /실시간_재고_설정
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

# /재고표시
@TREE.command(name="재고표시", description="실시간 로벅스 재고 임베드를 공개로 표시합니다.")
async def cmd_show(inter: Interaction):
    # 공개로 보여야 하니, reply 대신 채널에 직접 메시지 전송(또는 followup 공개)
    await inter.response.defer(thinking=True, ephemeral=False)
    await send_or_edit_stock(inter, inter.user.id, force_new=True)
    await inter.followup.send("재고 임베드가 공개로 표시됐어. 60초마다 자동 갱신할게.", ephemeral=True)

# 총 판매량 누적(운영 훅)
@TREE.command(name="판매_누적", description="총 판매량을 누적합니다.")
@app_commands.describe(amount="증가 수량(정수)")
async def cmd_inc(inter: Interaction, amount: int):
    if amount < 0:
        await inter.response.send_message("음수 불가.", ephemeral=True)
        return
    cur = get_total_sold()
    set_total_sold(cur + amount)
    await inter.response.send_message(f"총 판매량 {amount:,} 증가! 현재 {cur+amount:,}", ephemeral=True)

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN이 비어있거나 형식이 이상함.")
    BOT.run(TOKEN)

if __name__ == "__main__":
    main()
