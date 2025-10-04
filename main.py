import os
import io
import json
import time
import re
import asyncio
from typing import Dict, Any, List, Optional, Tuple

import discord
from discord import app_commands, Interaction, Embed, File
from discord.ext import commands
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# ========= ENV =========
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ========= BOT =========
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ========= DB(JSON) =========
DATA_PATH = "data.json"

def _load_db() -> Dict[str, Any]:
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump({"users": {}}, f, ensure_ascii=False, indent=2)
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_db(db: Dict[str, Any]):
    tmp = DATA_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_PATH)

def _ensure_user(uid: int) -> Dict[str, Any]:
    db = _load_db()
    u = db["users"].get(str(uid))
    if not u:
        u = {
            "wallet": 0, "total": 0, "count": 0, "recent": [],
            "roblox": {"cookie": None, "username": None, "password": None, "last_robux": 0, "last_username": None}
        }
        db["users"][str(uid)] = u
        _save_db(db)
    return u

def add_tx(uid: int, amount: int, desc: str, ttype: str = "other"):
    db = _load_db()
    u = db["users"].setdefault(str(uid), _ensure_user(uid))
    u["wallet"] = max(0, int(u.get("wallet", 0) + amount))
    if amount > 0:
        u["total"] = int(u.get("total", 0) + amount)
    u["count"] = int(u.get("count", 0) + 1)
    rec = u.get("recent", [])
    rec.insert(0, {"desc": desc, "amount": int(amount), "ts": int(time.time()), "type": ttype})
    u["recent"] = rec[:5]
    db["users"][str(uid)] = u
    _save_db(db)

def set_login_info(uid: int, cookie: Optional[str], username: Optional[str], password: Optional[str]):
    db = _load_db()
    u = _ensure_user(uid)
    r = u["roblox"]
    if cookie: r["cookie"] = cookie
    if username is not None: r["username"] = username
    if password is not None: r["password"] = password
    u["roblox"] = r
    db["users"][str(uid)] = u
    _save_db(db)

def set_login_result(uid: int, robux: int, username_hint: Optional[str]):
    db = _load_db()
    u = _ensure_user(uid)
    r = u["roblox"]
    r["last_robux"] = int(robux)
    if username_hint:
        r["last_username"] = username_hint
    u["roblox"] = r
    db["users"][str(uid)] = u
    _save_db(db)

# ========= PartialEmoji =========
def pe(eid: int, name: str = None, animated: bool = False) -> discord.PartialEmoji:
    return discord.PartialEmoji(name=name, id=eid, animated=animated)

EMOJI_NOTICE = pe(1424003478275231916, name="emoji_5", animated=False)
EMOJI_CHARGE = pe(1381244136627245066, name="charge",  animated=False)
EMOJI_INFO   = pe(1381244138355294300, name="info",    animated=False)
EMOJI_BUY    = pe(1381244134680957059, name="category",animated=False)

# ========= Roblox 로그인/파싱 =========
ROBLOX_HOME_URLS = ["https://www.roblox.com/ko/home", "https://www.roblox.com/home"]
ROBLOX_LOGIN_URLS= ["https://www.roblox.com/ko/Login", "https://www.roblox.com/Login"]
ROBLOX_TX_URL    = "https://www.roblox.com/ko/transactions"

BADGE_SELECTORS  = [
    "[data-testid*='nav-robux']",
    "a[aria-label*='Robux']",
    "a[aria-label*='로벅스']",
    "span[title*='Robux']",
    "span[title*='로벅스']",
]

# 거래 페이지 “내 잔액” 라벨 정밀 셀렉터 + 폴백
BALANCE_LABEL_SELECTORS = [
    "text=내 잔액",          # ko
    "text=My Balance",       # en
    "text=Balance",          # fallback
]
# “내 잔액” 영역 안쪽 숫자만 추출(콤마/공백/마침표 제거)
NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

def _to_int(text: str) -> Optional[int]:
    if not text: return None
    m = NUM_RE.search(text)
    if not m: return None
    try:
        return int(re.sub(r"[,\.\s]", "", m.group(1)))
    except Exception:
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
            viewport={"width": 1366, "height": 864}, java_script_enabled=True, locale="ko-KR"
        )
    except Exception:
        return None

async def _goto(page: Page, url: str) -> bool:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000); return True
    except Exception:
        return False

async def _wait_nav_ready(page: Page):
    for sel in BADGE_SELECTORS:
        try:
            await page.wait_for_selector(sel, timeout=20000); return
        except Exception:
            continue
    await asyncio.sleep(0.8)

async def _wait_tx_title(page: Page):
    try:
        await page.wait_for_selector("text=내 거래, text=My Transactions", timeout=25000)
    except Exception:
        await asyncio.sleep(0.8)

async def parse_home_badge(page: Page) -> Optional[int]:
    for sel in BADGE_SELECTORS:
        try:
            el = await page.query_selector(sel)
            if not el: continue
            txt = (await el.inner_text() or "").strip()
            v = _to_int(txt)
            if isinstance(v, int) and 0 <= v <= 100_000_000: return v
        except Exception:
            continue
    try:
        html = await page.content()
        nums = []
        for kw in ["Robux","로벅스"]:
            for m in re.finditer(kw, html, flags=re.IGNORECASE):
                s = max(0, m.start()-120); e = min(len(html), m.end()+120)
                chunk = html[s:e]
                for mm in re.finditer(NUM_RE, chunk):
                    v = _to_int(mm.group(0))
                    if isinstance(v, int) and 0 <= v <= 100_000_000: nums.append(v)
        if nums: return min(nums)
    except Exception:
        pass
    return None

async def parse_transactions_balance(page: Page) -> Optional[int]:
    await _wait_tx_title(page)
    # 1) 라벨 직접
    for sel in BALANCE_LABEL_SELECTORS:
        try:
            el = await page.query_selector(sel)
            if not el: continue
            # 형제/부모 컨테이너 쪽 숫자 추출(라벨 바로 옆)
            container = await el.evaluate_handle("e => e.parentElement || e")
            txt = await (await container.get_property("innerText")).json_value()
            v = _to_int(txt or "")
            if isinstance(v, int) and 0 <= v <= 100_000_000: return v
        except Exception:
            continue
    # 2) 폴백: 라벨 주변 윈도우 스캔
    try:
        html = await page.content()
        nums = []
        for kw in ["내 잔액","My Balance","Balance"]:
            for m in re.finditer(kw, html, flags=re.IGNORECASE):
                s = max(0, m.start()-240); e = min(len(html), m.end()+240)
                chunk = html[s:e]
                for mm in re.finditer(NUM_RE, chunk):
                    v = _to_int(mm.group(0))
                    if isinstance(v, int) and 0 <= v <= 100_000_000: nums.append(v)
        if nums: return min(nums)
    except Exception:
        pass
    return None

async def screenshot_bytes(page: Page) -> Optional[bytes]:
    try:
        return await page.screenshot(type="png", full_page=False)
    except Exception:
        return None

# -------- 로그인 검증 루틴 --------
async def cookie_session_login(ctx: BrowserContext, cookie: str) -> Tuple[bool, Optional[str]]:
    try:
        await ctx.add_cookies([{"name":".ROBLOSECURITY","value":cookie,"domain":".roblox.com","path":"/","httpOnly":True,"secure":True,"sameSite":"Lax"}])
        page = await ctx.new_page()
        ok = await _goto(page, ROBLOX_HOME_URLS[0]) or await _goto(page, ROBLOX_HOME_URLS[1])
        if not ok: await page.close(); return False, None
        html = await page.content()
        logged_in = any(k in html for k in ["로그아웃","Log Out","프로필","Profile"])
        uname = None
        if logged_in:
            try:
                t = await page.title()
                if t:
                    m = re.search(r"[A-Za-z0-9_]{3,20}", t); uname = m.group(0) if m else None
            except Exception:
                pass
        await page.close()
        return logged_in, uname
    except Exception:
        return False, None

async def robux_with_cookie(cookie: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str], Optional[bytes]]:
    try:
        async with async_playwright() as p:
            browser = await launch_browser(p)
            if not browser: return False, None, None, "브라우저 오류", None
            ctx = await new_context(browser)
            if not ctx: await browser.close(); return False, None, None, "컨텍스트 오류", None

            valid, uname = await cookie_session_login(ctx, cookie)
            if not valid:
                await browser.close(); return False, None, None, "세션 무효/쿠키 만료", None

            page = await ctx.new_page()
            v_tx, v_home, shot = None, None, None

            if await _goto(page, ROBLOX_TX_URL):
                v_tx = await parse_transactions_balance(page)
                shot = await screenshot_bytes(page)

            if not isinstance(v_tx, int):
                if await _goto(page, ROBLOX_HOME_URLS[0]) or await _goto(page, ROBLOX_HOME_URLS[1]):
                    await _wait_nav_ready(page)
                    v_home = await parse_home_badge(page)

            v_final = v_tx if isinstance(v_tx, int) else v_home
            src = "transactions" if isinstance(v_tx, int) else ("home" if isinstance(v_home, int) else None)

            await page.close(); await browser.close()
            if isinstance(v_final, int):
                return True, v_final, uname, src, shot
            return False, None, uname, "로벅스 파싱 실패", shot
    except Exception:
        return False, None, None, "예외", None

async def robux_with_login(username: str, password: str) -> Tuple[bool, Optional[int], Optional[str], Optional[bytes]]:
    try:
        async with async_playwright() as p:
            browser = await launch_browser(p)
            if not browser: return False, None, "브라우저 오류", None
            ctx = await new_context(browser)
            if not ctx: await browser.close(); return False, None, "컨텍스트 오류", None

            page = await ctx.new_page()
            if not (await _goto(page, ROBLOX_LOGIN_URLS[0]) or await _goto(page, ROBLOX_LOGIN_URLS[1])):
                await browser.close(); return False, None, "로그인 페이지 이동 실패", None

            try:
                # 입력/제출
                await page.wait_for_selector("input[name='username'], input#login-username, input[type='text']", timeout=25000)
                await page.fill("input[name='username'], input#login-username, input[type='text']", username)
                await page.wait_for_selector("input[name='password'], input#login-password, input[type='password']", timeout=25000)
                await page.fill("input[name='password'], input#login-password, input[type='password']", password)
                await page.click("button[type='submit'], button:has-text('로그인'), button:has-text('Log In')")
            except Exception:
                await browser.close(); return False, None, "로그인 입력/전송 실패", None

            # 오류 배너/텍스트 감지(실패 조기판정)
            try:
                await asyncio.sleep(1.0)
                html = await page.content()
                if any(k in html for k in ["비밀번호가", "잘못", "incorrect", "Try again", "Two-step", "2단계", "인증", "device verification"]):
                    await browser.close(); return False, None, "자격증명 오류/2FA/장치인증", None
            except Exception:
                pass

            # 거래 페이지 진입해서 잔액 뽑아야 성공으로 인정
            v_tx, v_home, shot = None, None, None
            if await _goto(page, ROBLOX_TX_URL):
                v_tx = await parse_transactions_balance(page)
                shot = await screenshot_bytes(page)
            if not isinstance(v_tx, int):
                if await _goto(page, ROBLOX_HOME_URLS[0]) or await _goto(page, ROBLOX_HOME_URLS[1]):
                    await _wait_nav_ready(page)
                    v_home = await parse_home_badge(page)

            v_final = v_tx if isinstance(v_tx, int) else v_home
            await page.close(); await browser.close()
            if isinstance(v_final, int):
                return True, v_final, "transactions" if isinstance(v_tx, int) else "home", shot
            return False, None, "자격증명 오류/2FA/장치인증 또는 파싱 실패", shot
    except Exception:
        return False, None, "예외", None

# ========= COLORS =========
PINK   = discord.Colour(int("ff5dd6", 16))  # 패널 임베드
GRAY   = discord.Colour.dark_grey()         # 공지/내정보
ORANGE = discord.Colour.orange()            # 로그인 중..
GREEN  = discord.Colour.green()             # 성공
RED    = discord.Colour.red()               # 실패

# ========= 패널 임베드/뷰 =========
def embed_panel() -> Embed:
    return Embed(title="자동 로벅스 자판기", description="아래 버튼을 눌려 이용해주세요!", colour=PINK)

def embed_notice() -> Embed:
    return Embed(title="공지", description="<#1419230737244229653> 필독 부탁드립니다", colour=GRAY)

def embed_myinfo(user: discord.User | discord.Member, stats: Dict[str, Any]) -> Embed:
    emb = Embed(title=f"{getattr(user,'display_name',getattr(user,'name','유저'))}님 정보", colour=GRAY)
    wallet = int(stats.get("wallet", 0)); total = int(stats.get("total", 0)); count = int(stats.get("count", 0))
    emb.description = "\n".join([
        f"### 보유 금액 : {wallet:,}원",
        f"### 누적 금액 : {total:,}원",
        f"### 거래 횟수 : {count:,}번",
    ])
    try: emb.set_thumbnail(url=user.display_avatar.url)
    except Exception: pass
    return emb

def make_tx_select(stats: Dict[str, Any]) -> discord.ui.View:
    entries: List[Dict[str, Any]] = stats.get("recent", [])
    filtered = []
    for e in entries:
        d = (e.get("desc","") or "").lower()
        t = (e.get("type","") or "").lower()
        if t in ("buy","order","trade") or any(k in d for k in ["구매","거래","주문","buy","order","trade"]):
            filtered.append(e)
    options = ([
        discord.SelectOption(label=f"{e.get('desc','거래')} / {int(e.get('amount',0)):,}원", value=str(i))
        for i, e in enumerate(filtered)
    ] if filtered else [discord.SelectOption(label="거래 내역 없음", value="none", default=True)])
    class TxSelect(discord.ui.Select):
        def __init__(self):
            super().__init__(placeholder="최근 거래내역 보기", min_values=1, max_values=1, options=options)
        async def callback(self, interaction: Interaction):
            try: await interaction.response.defer_update()
            except Exception: pass
    v = discord.ui.View(timeout=None); v.add_item(TxSelect()); return v

# 버튼 응답 경합 방지용 락 + 폴백
button_lock = asyncio.Lock()

class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="공지",   emoji=EMOJI_NOTICE, custom_id="panel_notice", row=0))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="충전",   emoji=EMOJI_CHARGE, custom_id="panel_charge", row=0))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="내 정보", emoji=EMOJI_INFO,   custom_id="panel_info",   row=1))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="구매",   emoji=EMOJI_BUY,    custom_id="panel_buy",    row=1))

    async def interaction_check(self, interaction: Interaction) -> bool:
        async with button_lock:
            try: await interaction.response.defer_update()
            except Exception: pass
            cid = (interaction.data or {}).get("custom_id")
            uid = interaction.user.id
            try:
                if cid == "panel_notice":
                    await interaction.followup.send(embed=embed_notice(), ephemeral=True)
                elif cid == "panel_info":
                    stats = _ensure_user(uid)
                    await interaction.followup.send(embed=embed_myinfo(interaction.user, stats), view=make_tx_select(stats), ephemeral=True)
                elif cid == "panel_charge":
                    add_tx(uid, 1000, "충전", "charge")
                    stats = _ensure_user(uid)
                    await interaction.followup.send(content="충전 완료!", embed=embed_myinfo(interaction.user, stats), view=make_tx_select(stats), ephemeral=True)
                elif cid == "panel_buy":
                    add_tx(uid, -500, "구매", "buy")
                    stats = _ensure_user(uid)
                    await interaction.followup.send(content="구매 처리 완료!", embed=embed_myinfo(interaction.user, stats), view=make_tx_select(stats), ephemeral=True)
            except discord.NotFound:
                # Unknown Webhook 404 폴백
                try:
                    await interaction.edit_original_response(content="요청 처리 완료!")
                except Exception:
                    pass
        return False

# ========= /버튼패널 =========
@tree.command(name="버튼패널", description="자동 로벅스 자판기 패널을 공개로 표시합니다.")
async def 버튼패널(inter: Interaction):
    await inter.response.send_message(embed=embed_panel(), view=PanelView(), ephemeral=False)

# ========= /재고 (모달 → 주황 로딩 → 같은 메시지 편집) =========
class StockLoginModal(discord.ui.Modal, title="로그인"):
    cookie = discord.ui.TextInput(label="cookie(.ROBLOSECURITY)", required=False, style=discord.TextStyle.short, max_length=4000, placeholder="쿠키값(선택)")
    uid    = discord.ui.TextInput(label="아이디", required=False, style=discord.TextStyle.short, max_length=100)
    pw     = discord.ui.TextInput(label="비밀번호", required=False, style=discord.TextStyle.short, max_length=100)

    def __init__(self, inter: Interaction):
        super().__init__(timeout=None)
        self.inter = inter

    async def on_submit(self, interaction: Interaction):
        loading = Embed(title="로그인 중..", description="로그인 중입니다 조금만 기다려주세요", colour=ORANGE)
        await interaction.response.send_message(embed=loading, ephemeral=True)
        _ = await interaction.original_response()

        uid_num = interaction.user.id
        cookie_val = (self.cookie.value or "").strip()
        id_val    = (self.uid.value or "").strip()
        pw_val    = (self.pw.value or "").strip()

        if not cookie_val and not (id_val and pw_val):
            fail = Embed(title="로그인 실패", description="쿠키나 아이디/비밀번호 중 하나 이상을 입력해줘.", colour=RED)
            await interaction.edit_original_response(embed=fail)
            return

        if cookie_val: set_login_info(uid_num, cookie_val, None, None)
        if id_val or pw_val: set_login_info(uid_num, None, id_val if id_val else None, pw_val if pw_val else None)

        ok, robux, name_hint, shot_bytes = False, None, None, None

        if cookie_val:
            c_ok, c_robux, c_uname, c_src, c_shot = await robux_with_cookie(cookie_val)
            if c_ok:
                ok, robux, name_hint, shot_bytes = True, c_robux, c_uname, c_shot

        if not ok and id_val and pw_val:
            l_ok, l_robux, l_src, l_shot = await robux_with_login(id_val, pw_val)
            if l_ok:
                ok, robux, name_hint, shot_bytes = True, l_robux, (name_hint or id_val), l_shot

        if ok and isinstance(robux, int):
            set_login_result(uid_num, robux, name_hint)
            succ = Embed(
                title="로그인 성공",
                description=f"{(name_hint or id_val or '알 수 없음')}계정에 로그인 성공 되었습니다\n로벅스 수량 {robux:,}\n쿠키값 저장 완료되었습니다",
                colour=GREEN
            )
            files = []
            if shot_bytes:
                files = [File(io.BytesIO(shot_bytes), filename="robux_balance.png")]
                succ.set_image(url="attachment://robux_balance.png")
            await interaction.edit_original_response(embed=succ, attachments=files)
        else:
            fail = Embed(title="로그인 실패", description="자격증명 오류/2FA/장치인증 또는 로벅스 파싱 실패", colour=RED)
            await interaction.edit_original_response(embed=fail)

@tree.command(name="재고", description="쿠키 또는 계정으로 로그인하고 로벅스 수량을 확인합니다.")
async def 재고(inter: Interaction):
    await inter.response.send_modal(StockLoginModal(inter))

# ========= READY =========
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        await tree.sync()
        print("[SYNC] global commands synced (/버튼패널, /재고)")
    except Exception as e:
        print("[SYNC][ERR]", e)

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN 비정상")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
