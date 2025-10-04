import os
import io
import json
import re
import shutil
import asyncio
from typing import Any, Dict, Optional, Tuple

import discord
from discord import app_commands, Interaction, Embed, File
from discord.ext import commands, tasks
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from dotenv import load_dotenv; load_dotenv()

DATA_PATH = "data.json"
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

# 이미지 모드: "url" → URL로 IMAGE 슬롯(실패 시 첨부 폴백), "attach_local" → 로컬 stock.png 첨부 고정
IMAGE_MODE = "url"
STOCK_IMAGE_URL = "https://cdn.discordapp.com/attachments/1420389790649421877/1423898721036271718/IMG_2038.png?ex=68e1fc85&is=68e0ab05&hm=267f34b38adac333d3bdd72c603867239aa843dd5c6c891b83434b151daa1006&"
LOCAL_IMAGE_PATH = "stock.png"

ROBLOX_LOGIN_URLS = ["https://www.roblox.com/ko/Login", "https://www.roblox.com/Login"]
ROBLOX_TX_URLS = ["https://www.roblox.com/ko/transactions", "https://www.roblox.com/transactions"]

BALANCE_CACHE_TTL_SEC = 30
PAGE_TIMEOUT = 20000
UPDATE_INTERVAL_SEC = 60
LOGIN_RETRY = 2

NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

def _default_data() -> Dict[str, Any]:
    return {"users": {}, "stats": {"total_sold": 0}, "cache": {"balances": {}}, "meta": {"version": 1}}

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

def save_data(d: Dict[str, Any]): _atomic_write(DATA_PATH, d)

def mask_cookie(c: str) -> str:
    if not c or len(c) < 7: return "***"
    return c[:3] + "***" + c[-3:]

def get_user_block(uid: int) -> Dict[str, Any]:
    d = load_data(); return d["users"].get(str(uid), {})

def set_user_block(uid: int, block: Dict[str, Any]):
    d = load_data(); d["users"][str(uid)] = block; save_data(d)

def set_user_cookie(uid: int, cookie: str, username_hint: Optional[str] = None):
    u = get_user_block(uid); r = u.get("roblox", {})
    r["cookie_raw"] = cookie; r["masked_cookie"] = mask_cookie(cookie); r["cookie_set_at"] = asyncio.get_running_loop().time()
    if username_hint: r["username"] = username_hint
    u["roblox"] = r; set_user_block(uid, u)

def set_user_login(uid: int, username: str, password: str):
    u = get_user_block(uid); r = u.get("roblox", {})
    r["username"] = username; r["password"] = password
    u["roblox"] = r; set_user_block(uid, u)

def set_last_embed(uid: int, channel_id: int, message_id: int):
    u = get_user_block(uid); u["last_embed"] = {"channel_id": channel_id, "message_id": message_id}; set_user_block(uid, u)

def get_last_embed(uid: int) -> Optional[Dict[str, int]]:
    u = get_user_block(uid); return u.get("last_embed")

def get_total_sold() -> int:
    d = load_data(); return int(d.get("stats", {}).get("total_sold", 0))

def cache_balance(uid: int, value: int):
    d = load_data(); d["cache"].setdefault("balances", {})
    d["cache"]["balances"][str(uid)] = {"value": int(value), "ts": asyncio.get_running_loop().time()}
    save_data(d)

def get_cached_balance(uid: int) -> Optional[int]:
    d = load_data(); item = d.get("cache", {}).get("balances", {}).get(str(uid))
    if not item: return None
    ts = float(item["ts"])
    if (asyncio.get_running_loop().time() - ts) <= BALANCE_CACHE_TTL_SEC: return int(item["value"])
    return None

async def launch_browser(p):
    args = ["--disable-dev-shm-usage","--no-sandbox","--disable-gpu","--disable-setuid-sandbox","--no-zygote"]
    try: return await p.chromium.launch(headless=True, args=args)
    except Exception:
        try: return await p.chromium.launch(headless=False, args=args)
        except Exception: return None

async def new_context(browser: Browser) -> Optional[BrowserContext]:
    try:
        return await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            java_script_enabled=True,
            locale="ko-KR"
        )
    except Exception:
        return None

async def _extract_balance_precise(page: Page) -> Optional[int]:
    cand = None
    try:
        txt = await page.content()
        for key in ["RobuxBalance","robuxBalance","Balance","CurrentBalance"]:
            m = re.search(rf'"{key}"\s*:\s*("?)(\d+)\1', txt)
            if m:
                v = int(m.group(2))
                if 0 <= v <= 100000000: cand = v; break
    except Exception: pass
    try:
        if cand is None:
            sels = ["[data-testid*='nav-robux']","a[aria-label*='Robux']","a[aria-label*='로벅스']","span[title*='Robux']","span[title*='로벅스']"]
            for sel in sels:
                el = await page.query_selector(sel)
                if not el: continue
                t = (await el.inner_text()).strip()
                m = re.search(r"(\d{1,3}(?:[,\.\s]\d{3})*|\d+)", t)
                if m:
                    v = int(re.sub(r"[,\.\s]", "", m.group(1)))
                    if 0 <= v <= 100000000: cand = v; break
    except Exception: pass
    try:
        if cand is None:
            html = await page.content()
            around = []
            for kw in ["Robux","로벅스"]:
                for m in re.finditer(kw, html, flags=re.IGNORECASE):
                    s = max(0, m.start()-100); e = min(len(html), m.end()+100)
                    around.append(html[s:e])
            nums = []
            for chunk in around:
                for m in re.finditer(r"(\d{1,3}(?:[,\.\s]\d{3})*|\d+)", chunk):
                    v = int(re.sub(r"[,\.\s]", "", m.group(1)))
                    if 0 <= v <= 100000000: nums.append(v)
            if nums: cand = min(nums)
    except Exception: pass
    return cand

async def _open_with_cookie(context: BrowserContext, cookie_raw: str) -> Optional[int]:
    try:
        await context.add_cookies([{"name":".ROBLOSECURITY","value":cookie_raw,"domain":".roblox.com","path":"/","httpOnly":True,"secure":True,"sameSite":"Lax"}])
        page = await context.new_page()
        for url in ROBLOX_TX_URLS:
            try: await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT); break
            except Exception: continue
        bal = await _extract_balance_precise(page)
        await page.close(); return bal
    except Exception:
        return None

async def _login_with_idpw(context: BrowserContext, username: str, password: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str], Optional[str]]:
    ok, bal, cookie_val, username_hint, reason = False, None, None, None, None
    page = await context.new_page()
    try:
        loaded = False
        for url in ROBLOX_LOGIN_URLS:
            try: await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT); loaded = True; break
            except Exception: continue
        if not loaded: reason = "로그인 페이지 로딩 실패"; return ok, bal, cookie_val, username_hint, reason
        user_sel = "input[name='username'], input#login-username, input[type='text']"
        pass_sel = "input[name='password'], input#login-password, input[type='password']"
        await page.wait_for_selector(user_sel, timeout=PAGE_TIMEOUT); await page.fill(user_sel, username)
        await page.wait_for_selector(pass_sel, timeout=PAGE_TIMEOUT); await page.fill(pass_sel, password)
        login_btn = "button[type='submit'], button[aria-label], button:has-text('로그인'), button:has-text('Log In')"
        await page.click(login_btn)
        try: await page.wait_for_load_state("networkidle", timeout=PAGE_TIMEOUT)
        except Exception: pass
        err = await page.query_selector("div:has-text('잘못') , div:has-text('Invalid') , div:has-text('incorrect')")
        if err: reason = "아이디/비밀번호 오류"; return ok, bal, cookie_val, username_hint, reason
        moved = False
        for url in ROBLOX_TX_URLS:
            try: await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT); moved = True; break
            except Exception: continue
        if not moved: reason = "거래 페이지 이동 실패(장치 인증/2FA 가능성)"; return ok, bal, cookie_val, username_hint, reason
        bal = await _extract_balance_precise(page)
        for c in await context.cookies():
            if c.get("name") == ".ROBLOSECURITY": cookie_val = c.get("value"); break
        try:
            title = await page.title()
            if title:
                m = re.search(r"[A-Za-z0-9_]{3,20}", title)
                if m: username_hint = m.group(0)
        except Exception: pass
        ok = (bal is not None)
        if not ok and not reason: reason = "잔액 파싱 실패"
        return ok, bal, cookie_val, username_hint, reason
    finally:
        await page.close()

async def fetch_balance(uid: int) -> int:
    cached = get_cached_balance(uid)
    if cached is not None: return int(cached)
    info = get_user_block(uid).get("roblox", {})
    cookie_raw, username, password = info.get("cookie_raw"), info.get("username"), info.get("password")
    for _ in range(LOGIN_RETRY):
        try:
            async with async_playwright() as p:
                browser = await launch_browser(p)
                if not browser: continue
                context = await new_context(browser)
                if not context: await browser.close(); continue
                if cookie_raw:
                    bal = await _open_with_cookie(context, cookie_raw); await browser.close()
                    if isinstance(bal, int): cache_balance(uid, bal); return int(bal)
                if username and password:
                    ok, bal, new_cookie, uname_hint, _ = await _login_with_idpw(context, username, password)
                    await browser.close()
                    if ok and isinstance(bal, int):
                        if new_cookie: set_user_cookie(uid, new_cookie, uname_hint)
                        cache_balance(uid, bal); return int(bal)
                else:
                    await browser.close()
        except Exception:
            continue
    return 0

async def fetch_image_bytes(url: str, timeout: int = 10) -> Optional[bytes]:
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as resp: return resp.read()
    except Exception:
        return None

def make_embed(guild: Optional[discord.Guild], robux_balance: int, total_sold: int, image_as_attachment: bool) -> Embed:
    colour = discord.Colour(int("ff5dd6", 16))
    emb = Embed(title="", colour=colour)  # timestamp 미사용 → 하단 시간 안 뜸
    if guild:
        icon = guild.icon.url if guild.icon else None
        emb.set_author(name=guild.name, icon_url=icon)
    stock = f"{robux_balance:,}"; total = f"{total_sold:,}"
    lines = [
        "### <a:upuoipipi:1423892277373304862>실시간 로벅스 재고",
        "### <a:thumbsuppp:1423892279612936294>로벅스 재고",
        f"<a:sakfnmasfagfamg:1423892278677602435>**`{stock}`로벅스**",
        "### <a:thumbsuppp:1423892279612936294>총 판매량",
        f"<a:sakfnmasfagfamg:1423892278677602435>**`{total}`로벅스**",
    ]
    emb.description = "\n".join(lines)
    if image_as_attachment: emb.set_image(url="attachment://stock.png")
    else: emb.set_image(url=STOCK_IMAGE_URL.strip())
    return emb

INTENTS = discord.Intents.default()
BOT = commands.Bot(command_prefix="!", intents=INTENTS)
TREE = BOT.tree

active_updates: Dict[str, Dict[str, Any]] = {}

async def send_or_edit_public(inter: Interaction, uid: int, force_new: bool = False):
    bal = await fetch_balance(uid); total = get_total_sold()
    image_as_attachment = IMAGE_MODE == "attach_local"
    file: Optional[File] = None
    if image_as_attachment:
        if os.path.exists(LOCAL_IMAGE_PATH):
            file = File(fp=LOCAL_IMAGE_PATH, filename="stock.png")
        else:
            img = await fetch_image_bytes(STOCK_IMAGE_URL)
            file = File(io.BytesIO(img), filename="stock.png") if img else None
    embed = make_embed(inter.guild, bal, total, image_as_attachment=image_as_attachment)

    if force_new or not get_last_embed(uid):
        if file: msg = await inter.channel.send(embed=embed, file=file)
        else:
            if IMAGE_MODE == "url":
                try: msg = await inter.channel.send(embed=embed)
                except Exception:
                    img = await fetch_image_bytes(STOCK_IMAGE_URL)
                    file = File(io.BytesIO(img), filename="stock.png") if img else None
                    msg = await inter.channel.send(embed=embed, file=file) if file else await inter.channel.send(embed=embed)
            else:
                msg = await inter.channel.send(embed=embed)
        set_last_embed(uid, inter.channel.id, msg.id)
        active_updates[str(uid)] = {"channel_id": inter.channel.id, "message_id": msg.id, "use_attachment": bool(file) or image_as_attachment}
        return

    last = get_last_embed(uid)
    try:
        ch = await BOT.fetch_channel(last["channel_id"])
        msg = await ch.fetch_message(last["message_id"])
        if image_as_attachment:
            if file: await msg.edit(embed=embed, attachments=[file])
            else: await msg.edit(embed=embed)
        else:
            try: await msg.edit(embed=embed)
            except Exception:
                img = await fetch_image_bytes(STOCK_IMAGE_URL)
                file = File(io.BytesIO(img), filename="stock.png") if img else None
                if file: await msg.edit(embed=embed, attachments=[file])
                else: await msg.edit(embed=embed)
        active_updates[str(uid)] = {"channel_id": ch.id, "message_id": msg.id, "use_attachment": image_as_attachment}
    except Exception:
        if file: msg = await inter.channel.send(embed=embed, file=file)
        else: msg = await inter.channel.send(embed=embed)
        set_last_embed(uid, inter.channel.id, msg.id)
        active_updates[str(uid)] = {"channel_id": inter.channel.id, "message_id": msg.id, "use_attachment": image_as_attachment}

@tasks.loop(seconds=UPDATE_INTERVAL_SEC)
async def updater_loop():
    for uid, loc in list(active_updates.items()):
        try:
            user_id = int(uid)
            ch = await BOT.fetch_channel(loc["channel_id"])
            msg = await ch.fetch_message(loc["message_id"])
            bal = await fetch_balance(user_id); total = get_total_sold()
            use_attach = loc.get("use_attachment", IMAGE_MODE == "attach_local")
            embed = make_embed(getattr(msg, "guild", None), bal, total, image_as_attachment=use_attach)
            if use_attach:
                file = File(fp=LOCAL_IMAGE_PATH, filename="stock.png") if os.path.exists(LOCAL_IMAGE_PATH) else None
                if not file:
                    img = await fetch_image_bytes(STOCK_IMAGE_URL)
                    file = File(io.BytesIO(img), filename="stock.png") if img else None
                if file: await msg.edit(embed=embed, attachments=[file])
                else: await msg.edit(embed=embed)
            else:
                try: await msg.edit(embed=embed)
                except Exception:
                    img = await fetch_image_bytes(STOCK_IMAGE_URL)
                    file = File(io.BytesIO(img), filename="stock.png") if img else None
                    if file: await msg.edit(embed=embed, attachments=[file])
                    else: await msg.edit(embed=embed)
        except Exception:
            continue

async def sync_tree():
    try:
        if GUILD_ID: await TREE.sync(guild=discord.Object(id=GUILD_ID))
        else: await TREE.sync()
    except Exception as e:
        print("Command sync err:", e)

@BOT.event
async def on_ready():
    load_data()
    print(f"Logged in as {BOT.user} (data.json ready)")
    await sync_tree()
    if not updater_loop.is_running(): updater_loop.start()

@TREE.command(name="실시간_재고_설정", description="쿠키/로그인 저장 후 즉시 검증하고 임베드에 반영합니다.")
@app_commands.describe(mode="cookie 또는 login", cookie=".ROBLOSECURITY 값", id="Roblox 아이디", pw="Roblox 비밀번호")
async def cmd_setup(inter: Interaction, mode: str, cookie: Optional[str] = None, id: Optional[str] = None, pw: Optional[str] = None):
    await inter.response.defer(ephemeral=True, thinking=True)
    mode = (mode or "").lower().strip()
    if mode not in ("cookie","login"):
        await inter.followup.send(embed=Embed(title="실패", description="mode는 cookie 또는 login", colour=discord.Colour.red()), ephemeral=True)
        return
    if mode == "cookie":
        if not cookie:
            await inter.followup.send(embed=Embed(title="실패", description="cookie(.ROBLOSECURITY) 값 필요", colour=discord.Colour.red()), ephemeral=True); return
        set_user_cookie(inter.user.id, cookie)
        bal = await fetch_balance(inter.user.id)
        await inter.followup.send(embed=Embed(title="연동 완료", description=f"현재 잔액: {bal:,} 로벅스", colour=discord.Colour.green()), ephemeral=True)
        await send_or_edit_public(inter, inter.user.id, force_new=False)
        return
    if mode == "login":
        if not id or not pw:
            await inter.followup.send(embed=Embed(title="실패", description="login 모드는 id, pw 필요", colour=discord.Colour.red()), ephemeral=True); return
        set_user_login(inter.user.id, id, pw)
        tried_ok, last_reason, bal_value = False, None, 0
        try:
            async with async_playwright() as p:
                browser = await launch_browser(p)
                if not browser: last_reason = "브라우저 실행 오류(install chromium 필요)"
                else:
                    ctx = await new_context(browser)
                    if not ctx: last_reason = "브라우저 컨텍스트 실패(샌드박스/권한)"
                    else:
                        for _ in range(LOGIN_RETRY):
                            _ok, _bal, new_cookie, uname_hint, fail_reason = await _login_with_idpw(ctx, id, pw)
                            if _ok and isinstance(_bal, int):
                                tried_ok = True; bal_value = _bal
                                if new_cookie: set_user_cookie(inter.user.id, new_cookie, uname_hint)
                                break
                            last_reason = fail_reason or "알 수 없는 오류"
                    await browser.close()
        except Exception:
            last_reason = "Playwright 실행 예외"
        if tried_ok:
            await inter.followup.send(embed=Embed(title="로그인 완료", description=f"현재 잔액: {bal_value:,} 로벅스", colour=discord.Colour.green()), ephemeral=True)
            await send_or_edit_public(inter, inter.user.id, force_new=False)
        else:
            await inter.followup.send(embed=Embed(title="로그인 실패", description=str(last_reason), colour=discord.Colour.red()), ephemeral=True)

@TREE.command(name="재고표시", description="실시간 로벅스 재고를 공개 임베드로 표시합니다.")
async def cmd_show(inter: Interaction):
    await inter.response.defer(thinking=True, ephemeral=False)
    await send_or_edit_public(inter, inter.user.id, force_new=True)
    await inter.followup.send("재고 임베드 공개 완료. 60초마다 자동 갱신해.", ephemeral=True)

def main():
    if not TOKEN or len(TOKEN) < 10: raise RuntimeError("DISCORD_TOKEN 비어있거나 형식 이상")
    BOT.run(TOKEN)

if __name__ == "__main__":
    main()
