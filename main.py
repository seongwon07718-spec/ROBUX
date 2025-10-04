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

# ===== 기본 설정 =====
DATA_PATH = "data.json"
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

# 이미지 모드: "url" 또는 "attach_local"
IMAGE_MODE = "url"
STOCK_IMAGE_URL = "https://cdn.discordapp.com/attachments/1420389790649421877/1423898721036271718/IMG_2038.png?ex=68e1fc85&is=68e0ab05&hm=267f34b38adac333d3bdd72c603867239aa843dd5c6c891b83434b151daa1006&"
LOCAL_IMAGE_PATH = "stock.png"

# Roblox 경로
ROBLOX_HOME_URLS = ["https://www.roblox.com/ko/home", "https://www.roblox.com/home"]
ROBLOX_LOGIN_URLS = ["https://www.roblox.com/ko/Login", "https://www.roblox.com/Login"]

# 타임아웃·주기
BALANCE_CACHE_TTL_SEC = 30
PAGE_TIMEOUT = 15000
UPDATE_INTERVAL_SEC = 60
LOGIN_RETRY = 2

NUM_RE = re.compile(r"(\d{1,3}(?:[,\.\s]\d{3})*|\d+)")

# ===== 데이터 유틸 =====
def _default_data() -> Dict[str, Any]:
    return {"users": {}, "stats": {"total_sold": 0}, "cache": {"balances": {}}, "meta": {"version": 1}}

def _atomic_write(path: str, data: Dict[str, Any]):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    shutil.move(tmp, path)

def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_PATH):
        d = _default_data(); _atomic_write(DATA_PATH, d); return d
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        d = _default_data(); _atomic_write(DATA_PATH, d); return d

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

# ===== Playwright 런처 =====
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
            viewport={"width": 1280, "height": 800}, java_script_enabled=True, locale="ko-KR"
        )
    except Exception:
        return None

# ===== Roblox 파싱(홈 우상단 뱃지) =====
ROBLOX_BADGE_SELECTORS = [
    "[data-testid*='nav-robux']",
    "a[aria-label*='Robux']",
    "a[aria-label*='로벅스']",
    "span[title*='Robux']",
    "span[title*='로벅스']",
]

async def _extract_robux_badge(page: Page) -> Optional[int]:
    # 상단 뱃지 영역만 본다
    for sel in ROBLOX_BADGE_SELECTORS:
        try:
            el = await page.query_selector(sel)
            if not el: continue
            txt = (await el.inner_text() or "").strip()
            m = NUM_RE.search(txt)
            if not m: continue
            v = int(re.sub(r"[,\.\s]", "", m.group(1)))
            if 0 <= v <= 100_000_000:
                return v
        except Exception:
            continue
    # 주변 텍스트 폴백(근접 80자)
    try:
        html = await page.content()
        around = []
        for kw in ["Robux","로벅스"]:
            for m in re.finditer(kw, html, flags=re.IGNORECASE):
                s = max(0, m.start()-80); e = min(len(html), m.end()+80)
                around.append(html[s:e])
        nums = []
        for chunk in around:
            for m in re.finditer(NUM_RE, chunk):
                v = int(re.sub(r"[,\.\s]", "", m.group(1)))
                if 0 <= v <= 100_000_000: nums.append(v)
        if nums:
            return min(nums)
    except Exception:
        pass
    return None

async def _goto_any(page: Page, urls: list[str]):
    for u in urls:
        try:
            await page.goto(u, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            return True
        except Exception:
            continue
    return False

async def _open_with_cookie_home(context: BrowserContext, cookie_raw: str) -> Optional[int]:
    try:
        await context.add_cookies([{"name":".ROBLOSECURITY","value":cookie_raw,"domain":".roblox.com","path":"/","httpOnly":True,"secure":True,"sameSite":"Lax"}])
        page = await context.new_page()
        ok = await _goto_any(page, ROBLOX_HOME_URLS)
        if not ok:
            await page.close(); return None
        # 상단 뱃지 바로 파싱(입력 대기 없이)
        bal = await _extract_robux_badge(page)
        await page.close()
        return bal
    except Exception:
        return None

async def _login_with_idpw_home(context: BrowserContext, username: str, password: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    ok, bal, cookie_val, username_hint = False, None, None, None
    page = await context.new_page()
    try:
        # 로그인 페이지 진입
        got = await _goto_any(page, ROBLOX_LOGIN_URLS)
        if not got:
            await page.close(); return False, None, None, None

        user_sel = "input[name='username'], input#login-username, input[type='text']"
        pass_sel = "input[name='password'], input#login-password, input[type='password']"
        await page.wait_for_selector(user_sel, timeout=PAGE_TIMEOUT)
        await page.fill(user_sel, username)
        await page.wait_for_selector(pass_sel, timeout=PAGE_TIMEOUT)
        await page.fill(pass_sel, password)
        # 빠른 클릭
        login_btn = "button[type='submit'], button[aria-label], button:has-text('로그인'), button:has-text('Log In')"
        await page.click(login_btn)
        # 네트워크 전체 대기 대신 짧게 DOM 상호작용 대기
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=PAGE_TIMEOUT)
        except Exception:
            pass
        # 홈으로 이동 후 우상단 뱃지
        ok_home = await _goto_any(page, ROBLOX_HOME_URLS)
        if not ok_home:
            await page.close(); return False, None, None, None
        bal = await _extract_robux_badge(page)

        # 쿠키 추출
        for c in await context.cookies():
            if c.get("name") == ".ROBLOSECURITY":
                cookie_val = c.get("value"); break
        try:
            t = await page.title()
            if t:
                m = re.search(r"[A-Za-z0-9_]{3,20}", t)
                if m: username_hint = m.group(0)
        except Exception:
            pass
        ok = bal is not None
        return ok, bal, cookie_val, username_hint
    finally:
        await page.close()

async def fetch_balance(uid: int) -> int:
    cached = get_cached_balance(uid)
    if cached is not None:
        return int(cached)

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
                    bal = await _open_with_cookie_home(context, cookie_raw); await browser.close()
                    if isinstance(bal, int):
                        cache_balance(uid, bal); return int(bal)

                if username and password:
                    ok, bal, new_cookie, uname_hint = await _login_with_idpw_home(context, username, password)
                    await browser.close()
                    if ok and isinstance(bal, int):
                        if new_cookie: set_user_cookie(uid, new_cookie, uname_hint)
                        cache_balance(uid, bal); return int(bal)
                else:
                    await browser.close()
        except Exception:
            continue
    return 0

# ===== 이미지 유틸 =====
async def fetch_image_bytes(url: str, timeout: int = 10) -> Optional[bytes]:
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None

# ===== 임베드 템플릿 =====
def make_stock_embed(guild: Optional[discord.Guild], robux_balance: int, total_sold: int, image_as_attachment: bool) -> Embed:
    colour = discord.Colour(int("ff5dd6", 16))
    emb = Embed(title="", colour=colour)
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

def make_panel_embed(guild: Optional[discord.Guild]) -> Embed:
    colour = discord.Colour(int("ff5dd6", 16))
    emb = Embed(title="", colour=colour)
    if guild:
        icon = guild.icon.url if guild.icon else None
        emb.set_author(name=guild.name, icon_url=icon)
    desc = []
    desc.append("## 24시간 자동 자판기")
    desc.append("**아래 원하시는 버튼을 눌려 이용해주세요**")
    emb.description = "\n".join(desc)
    return emb

# ===== 디스코드 봇 =====
INTENTS = discord.Intents.default()
BOT = commands.Bot(command_prefix="!", intents=INTENTS)
TREE = BOT.tree

active_updates: Dict[str, Dict[str, Any]] = {}

async def send_or_edit_stock(inter: Interaction, uid: int, force_new: bool = False):
    bal = await fetch_balance(uid); total = get_total_sold()
    image_as_attachment = (IMAGE_MODE == "attach_local")
    file: Optional[File] = None
    if image_as_attachment:
        if os.path.exists(LOCAL_IMAGE_PATH):
            file = File(fp=LOCAL_IMAGE_PATH, filename="stock.png")
        else:
            img = await fetch_image_bytes(STOCK_IMAGE_URL)
            if img: file = File(io.BytesIO(img), filename="stock.png")
    embed = make_stock_embed(inter.guild, bal, total, image_as_attachment)

    if force_new or not get_last_embed(uid):
        msg = await inter.channel.send(embed=embed, file=file) if file else await inter.channel.send(embed=embed)
        set_last_embed(uid, inter.channel.id, msg.id)
        active_updates[str(uid)] = {"channel_id": inter.channel.id, "message_id": msg.id, "use_attachment": bool(file) or image_as_attachment}
        return

    last = get_last_embed(uid)
    try:
        ch = await BOT.fetch_channel(last["channel_id"])
        msg = await ch.fetch_message(last["message_id"])
        if image_as_attachment and file:
            await msg.edit(embed=embed, attachments=[file])
        else:
            try:
                await msg.edit(embed=embed)
            except Exception:
                img = await fetch_image_bytes(STOCK_IMAGE_URL)
                file = File(io.BytesIO(img), filename="stock.png") if img else None
                if file: await msg.edit(embed=embed, attachments=[file])
                else: await msg.edit(embed=embed)
        active_updates[str(uid)] = {"channel_id": ch.id, "message_id": msg.id, "use_attachment": image_as_attachment}
    except Exception:
        msg = await inter.channel.send(embed=embed, file=file) if file else await inter.channel.send(embed=embed)
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
            embed = make_stock_embed(getattr(msg, "guild", None), bal, total, image_as_attachment=use_attach)
            if use_attach:
                file = File(fp=LOCAL_IMAGE_PATH, filename="stock.png") if os.path.exists(LOCAL_IMAGE_PATH) else None
                if not file:
                    img = await fetch_image_bytes(STOCK_IMAGE_URL)
                    file = File(io.BytesIO(img), filename="stock.png") if img else None
                if file: await msg.edit(embed=embed, attachments=[file])
                else: await msg.edit(embed=embed)
            else:
                try:
                    await msg.edit(embed=embed)
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

# ===== PartialEmoji 준비(버튼용) =====
def pe(id_str: str, name: str = None, animated: bool = False) -> discord.PartialEmoji:
    # id_str는 문자열 숫자(스노우플레이크)
    return discord.PartialEmoji(name=name, id=int(id_str), animated=animated)

EMOJI_ACC = pe("1423544323735027763", name="Acc", animated=False)
EMOJI_CARD = pe("1423544325597560842", name="Card", animated=True)
EMOJI_DISCORD = pe("1423517142556610560", name="discord", animated=False)
EMOJI_NITRO = pe("1423517143730749490", name="Nitro", animated=False)

class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # 2x2 버튼, 회색(secondary)
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="공지사항", emoji=EMOJI_ACC, custom_id="p_notice", row=0))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="충전", emoji=EMOJI_CARD, custom_id="p_charge", row=0))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="내 정보", emoji=EMOJI_DISCORD, custom_id="p_me", row=1))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="구매", emoji=EMOJI_NITRO, custom_id="p_buy", row=1))

    @discord.ui.button(label="hidden", style=discord.ButtonStyle.secondary)
    async def dummy(self, interaction: Interaction, button: discord.ui.Button):
        pass

    async def interaction_check(self, interaction: Interaction) -> bool:
        # 상호작용 응답 노출 안 되게: 즉시 업데이트만 하고 메시지는 그대로
        try:
            await interaction.response.defer()  # 아무 메시지도 보내지 않음
        except Exception:
            pass
        return False

# ===== 명령어 =====
@TREE.command(name="실시간_재고_설정", description="쿠키/로그인 저장 후 즉시 검증하고 임베드에 반영합니다.")
@app_commands.describe(mode="cookie 또는 login", cookie=".ROBLOSECURITY 값", id="Roblox 아이디", pw="Roblox 비밀번호")
async def cmd_setup(inter: Interaction, mode: str, cookie: Optional[str] = None, id: Optional[str] = None, pw: Optional[str] = None):
    await inter.response.defer(ephemeral=True, thinking=True)
    mode = (mode or "").lower().strip()
    if mode not in ("cookie","login"):
        await inter.followup.send("mode는 cookie 또는 login이야.", ephemeral=True); return

    if mode == "cookie":
        if not cookie:
            await inter.followup.send("cookie(.ROBLOSECURITY) 값이 필요해.", ephemeral=True); return
        set_user_cookie(inter.user.id, cookie)
        bal = await fetch_balance(inter.user.id)
        await inter.followup.send(f"연동 완료! 현재 잔액: {bal:,} 로벅스", ephemeral=True)
        await send_or_edit_stock(inter, inter.user.id, force_new=False)
        return

    if mode == "login":
        if not id or not pw:
            await inter.followup.send("login 모드는 id랑 pw 둘 다 필요해.", ephemeral=True); return
        set_user_login(inter.user.id, id, pw)
        tried_ok, bal_value = False, 0
        try:
            async with async_playwright() as p:
                browser = await launch_browser(p)
                if browser:
                    ctx = await new_context(browser)
                    if ctx:
                        for _ in range(LOGIN_RETRY):
                            ok, bal, new_cookie, uname_hint = await _login_with_idpw_home(ctx, id, pw)
                            if ok and isinstance(bal, int):
                                tried_ok = True; bal_value = bal
                                if new_cookie: set_user_cookie(inter.user.id, new_cookie, uname_hint)
                                break
                    await browser.close()
        except Exception:
            pass
        if tried_ok:
            await inter.followup.send(f"로그인 완료! 현재 잔액: {bal_value:,} 로벅스", ephemeral=True)
            await send_or_edit_stock(inter, inter.user.id, force_new=False)
        else:
            await inter.followup.send("로그인 실패(계정 보호/2FA/장치인증 가능성). 쿠키 방식 추천.", ephemeral=True)

@TREE.command(name="재고표시", description="실시간 로벅스 재고 임베드를 공개로 표시합니다.")
async def cmd_show(inter: Interaction):
    await inter.response.defer(thinking=True, ephemeral=False)
    await send_or_edit_stock(inter, inter.user.id, force_new=True)
    await inter.followup.send("재고 임베드 공개 완료. 60초마다 자동 갱신해.", ephemeral=True)

@TREE.command(name="버튼패널", description="24시간 자동 자판기 패널을 공개로 표시합니다.")
async def cmd_panel(inter: Interaction):
    await inter.response.defer(thinking=True, ephemeral=False)
    emb = make_panel_embed(inter.guild)
    view = PanelView()
    # 노출만 하고, 누르면 응답 메시지 안 뜨도록 View에 처리함
    await inter.followup.send(embed=emb, view=view, ephemeral=False)

# ===== 메인 =====
def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN 비어있거나 형식 이상")
    BOT.run(TOKEN)

if __name__ == "__main__":
    main()
