import os
import json
import re
import shutil
import asyncio
from typing import Any, Dict, Optional, Tuple

import discord
from discord import app_commands, Interaction, Embed
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
UPDATE_INTERVAL_SEC = 60  # 자동 갱신 주기(초)

NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

STOCK_IMAGE_URL = "https://cdn.discordapp.com/attachments/1420389790649421877/1423898721036271718/IMG_2038.png?ex=68e1fc85&is=68e0ab05&hm=267f34b38adac333d3bdd72c603867239aa843dd5c6c891b83434b151daa1006&"

# ===== 저장소 유틸 =====
def _default_data() -> Dict[str, Any]:
    return {
        "users": {},  # { userId: { "roblox": {...}, "last_embed": {"channel_id","message_id"} } }
        "stats": {"total_sold": 0},  # 총 판매량(표시용)
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
    r["cookie_set_at"] = asyncio.get_running_loop().time()
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
    d["cache"]["balances"][str(uid)] = {"value": int(value), "ts": asyncio.get_running_loop().time()}
    save_data(d)

def get_cached_balance(uid: int) -> Optional[int]:
    d = load_data()
    item = d.get("cache", {}).get("balances", {}).get(str(uid))
    if not item:
        return None
    ts = float(item["ts"])
    if (asyncio.get_running_loop().time() - ts) <= BALANCE_CACHE_TTL_SEC:
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

async def _login_with_idpw(context: BrowserContext, username: str, password: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str], Optional[str]]:
    ok, bal, cookie_val, username_hint, fail_reason = False, None, None, None, None
    page = await context.new_page()
    try:
        loaded = False
        for url in ROBLOX_LOGIN_URLS:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
                loaded = True
                break
            except Exception:
                continue
        if not loaded:
            fail_reason = "로그인 페이지 로딩 실패"
            return ok, bal, cookie_val, username_hint, fail_reason

        user_sel = "input[name='username'], input#login-username, input[type='text']"
        pass_sel = "input[name='password'], input#login-password, input[type='password']"

        await page.wait_for_selector(user_sel, timeout=PAGE_TIMEOUT)
        await page.fill(user_sel, username)
        await page.wait_for_selector(pass_sel, timeout=PAGE_TIMEOUT)
        await page.fill(pass_sel, password)
        login_btn = "button[type='submit'], button[aria-label], button:has-text('로그인'), button:has-text('Log In')"
        await page.click(login_btn)

        try:
            await page.wait_for_load_state("networkidle", timeout=PAGE_TIMEOUT)
        except Exception:
            pass

        # 실패 메시지 흔적
        error_box = await page.query_selector("div:has-text('잘못') , div:has-text('Invalid') , div:has-text('incorrect')")
        if error_box:
            fail_reason = "아이디/비밀번호가 올바르지 않음"
            return ok, bal, cookie_val, username_hint, fail_reason

        # 거래 페이지 이동
        moved = False
        for url in ROBLOX_TX_URLS:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
                moved = True
                break
            except Exception:
                continue
        if not moved:
            fail_reason = "거래 페이지 이동 실패(장치 인증/2FA 가능성)"
            return ok, bal, cookie_val, username_hint, fail_reason

        bal = await _extract_numbers_from_page(page)

        # 쿠키 추출
        cookies = await context.cookies()
        for c in cookies:
            if c.get("name") == ".ROBLOSECURITY":
                cookie_val = c.get("value")
                break

        # username 힌트
        try:
            title = await page.title()
            if title:
                m = re.search(r"[A-Za-z0-9_]{3,20}", title)
                if m:
                    username_hint = m.group(0)
        except Exception:
            pass

        ok = (bal is not None)
        if not ok and not fail_reason:
            fail_reason = "잔액 파싱 실패"
        return ok, bal, cookie_val, username_hint, fail_reason
    finally:
        await page.close()

async def fetch_balance(uid: int) -> int:
    # 실패 시 0 반환(요청사항)
    cached = get_cached_balance(uid)
    if cached is not None:
        return int(cached)

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
                    return int(bal)
                # 폴백: id/pw

            # 로그인 폴백
            if username and password:
                ok, bal, new_cookie, uname_hint, _ = await _login_with_idpw(context, username, password)
                await browser.close()
                if ok and isinstance(bal, int):
                    if new_cookie:
                        set_user_cookie(uid, new_cookie, uname_hint)
                    cache_balance(uid, bal)
                    return int(bal)
                return 0
            await browser.close()
            return 0
    except Exception:
        return 0

# ===== Discord Bot =====
INTENTS = discord.Intents.default()
BOT = commands.Bot(command_prefix="!", intents=INTENTS)
TREE = BOT.tree

# 자동 갱신 추적 { userId(str): {"guild_id": int, "channel_id": int, "message_id": int} }
active_updates: Dict[str, Dict[str, int]] = {}

def build_embed(guild: Optional[discord.Guild], robux_balance: int, total_sold: int) -> Embed:
    colour = discord.Colour(int("ff5dd6", 16))
    emb = Embed(title="", colour=colour)  # timestamp 미사용 → 아래 시간 안 뜸

    # 서버 이름 작게(텍스트). 썸네일/author 미사용 → 오른쪽 프사 안 뜸
    guild_line = f"*{guild.name}*" if guild else ""

    stock = f"{robux_balance:,}"
    total = f"{total_sold:,}"

    desc = []
    if guild_line:
        desc.append(guild_line)
    desc.append("### <a:upuoipipi:1423892277373304862>실시간 로벅스 재고")
    desc.append("### <a:thumbsuppp:1423892279612936294>로벅스 재고")
    desc.append(f"<a:sakfnmasfagfamg:1423892278677602435>**`{stock}`로벅스**")
    desc.append("### <a:thumbsuppp:1423892279612936294>총 판매량")
    desc.append(f"<a:sakfnmasfagfamg:1423892278677602435>**`{total}`로벅스**")

    emb.description = "\n".join(desc)
    emb.set_image(url=STOCK_IMAGE_URL)
    return emb

async def upsert_public_embed(inter: Interaction, uid: int, force_new: bool = False):
    bal = await fetch_balance(uid)  # 실패 시 0
    total = get_total_sold()
    embed = build_embed(inter.guild, bal, total)

    if force_new or not get_last_embed(uid):
        msg = await inter.channel.send(embed=embed)  # 공개
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
            bal = await fetch_balance(user_id)
            total = get_total_sold()
            ch = await BOT.fetch_channel(loc["channel_id"])
            msg = await ch.fetch_message(loc["message_id"])
            guild = msg.guild if hasattr(msg, "guild") else None
            embed = build_embed(guild, bal, total)
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
@TREE.command(name="실시간_재고_설정", description="Roblox 실시간 재고 연동을 설정(즉시 로그인/검증/반영)합니다.")
@app_commands.describe(mode="cookie 또는 login", cookie=".ROBLOSECURITY 값", id="Roblox 아이디", pw="Roblox 비밀번호")
async def cmd_setup(inter: Interaction, mode: str, cookie: Optional[str] = None, id: Optional[str] = None, pw: Optional[str] = None):
    await inter.response.defer(ephemeral=True, thinking=True)
    mode = (mode or "").lower().strip()
    if mode not in ("cookie", "login"):
        await inter.followup.send("mode는 cookie 또는 login 중 하나야.", ephemeral=True)
        return

    # 결과 임베드 템플릿
    def result_embed(title: str, desc: str, ok: bool) -> Embed:
        col = discord.Colour.green() if ok else discord.Colour.red()
        e = Embed(title=title, description=desc, colour=col)
        return e

    if mode == "cookie":
        if not cookie:
            await inter.followup.send(embed=result_embed("실패", "cookie(.ROBLOSECURITY) 값이 필요해.", False), ephemeral=True)
            return
        # 저장 후 즉시 검증/반영
        set_user_cookie(inter.user.id, cookie)
        bal = await fetch_balance(inter.user.id)
        if bal is not None:  # 실패 시 0이 일관 반환
            await inter.followup.send(embed=result_embed("연동 완료", f"쿠키 저장 및 잔액 확인: {bal:,} 로벅스", True), ephemeral=True)
            # 공개 임베드 즉시 새로고침(없으면 생성)
            await upsert_public_embed(inter, inter.user.id, force_new=False)
        else:
            await inter.followup.send(embed=result_embed("연동 실패", "쿠키로 잔액 확인 실패(0으로 표시될 수 있음).", False), ephemeral=True)
        return

    if mode == "login":
        if not id or not pw:
            await inter.followup.send(embed=result_embed("실패", "login 모드는 id, pw 모두 필요해.", False), ephemeral=True)
            return

        # 로그인 시도 → 결과 임베드
        # 내부적으로 fetch_balance는 쿠키 미보유 시 로그인 폴백으로 0/값을 반환
        set_user_login(inter.user.id, id, pw)

        # 좀 더 상세한 실패 사유를 위해 직접 로그인 루틴 한 번 실행
        try:
            async with async_playwright() as p:
                browser: Browser = await p.chromium.launch(headless=True)
                context: BrowserContext = await browser.new_context()
                ok, bal, new_cookie, uname_hint, fail_reason = await _login_with_idpw(context, id, pw)
                await browser.close()
        except Exception:
            ok, bal, new_cookie, uname_hint, fail_reason = False, None, None, None, "브라우저 실행 오류"

        if ok and isinstance(bal, int):
            if new_cookie:
                set_user_cookie(inter.user.id, new_cookie, uname_hint)
            cache_balance(inter.user.id, bal)
            await inter.followup.send(embed=result_embed("로그인 완료", f"잔액 확인: {bal:,} 로벅스", True), ephemeral=True)
            # 공개 임베드 즉시 반영
            await upsert_public_embed(inter, inter.user.id, force_new=False)
        else:
            reason = fail_reason or "알 수 없는 오류"
            await inter.followup.send(embed=result_embed("로그인 실패", reason, False), ephemeral=True)

@TREE.command(name="재고표시", description="실시간 로벅스 재고 임베드를 공개로 표시합니다.")
async def cmd_show(inter: Interaction):
    await inter.response.defer(thinking=True, ephemeral=False)  # 공개
    await upsert_public_embed(inter, inter.user.id, force_new=True)
    await inter.followup.send("재고 임베드 공개 완료. 60초마다 자동 갱신해.", ephemeral=True)

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN이 비어있거나 형식이 이상함.")
    BOT.run(TOKEN)

if __name__ == "__main__":
    main()
