Import os, io, json, time, re, asyncio
from typing import Dict, Any, List, Optional, Tuple

import discord
from discord import app_commands, Interaction, Embed, File
from discord.ext import commands
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# =========================================================================
# 봇 설정
# =========================================================================
# 🚨 .env 파일에서 토큰을 로드합니다. (PowerShell에서 $env:DISCORD_TOKEN 설정 시에도 사용 가능)
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# =========================================================================
# DB(JSON) Functions - (NameError 방지를 위해 클래스보다 먼저 정의 - 필수)
# =========================================================================
DATA_PATH = "data.json"
# 동시 파일 접근 경합 방지 Lock (안정성 확보)
button_lock = asyncio.Lock()

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

# NameError가 발생했던 함수 1: 사용자 데이터 초기화/확인
def _ensure_user(uid: int) -> Dict[str, Any]:
    db = _load_db()
    if str(uid) not in db["users"]:
        db["users"][str(uid)] = {
            "wallet": 0, "total": 0, "count": 0, "recent": [],
            "roblox": {"cookie": None, "username": None, "password": None, "last_robux": 0, "last_username": None}
        }
        _save_db(db)
        db = _load_db() 
    return db["users"][str(uid)]

# NameError가 발생했던 함수 2: 거래 내역 추가 및 잔액 업데이트
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
# (set_login_info, set_login_result 등 나머지 DB 함수는 코드가 길어 생략하나, 최종본에는 포함되어야 합니다.)
def set_login_info(uid: int, cookie: Optional[str], username: Optional[str], password: Optional[str]):
    db = _load_db()
    _ensure_user(uid)
    u = db["users"][str(uid)]
    r = u["roblox"]
    if cookie: r["cookie"] = cookie
    if username is not None: r["username"] = username
    if password is not None: r["password"] = password
    u["roblox"] = r
    db["users"][str(uid)] = u
    _save_db(db)

def set_login_result(uid: int, robux: int, username_hint: Optional[str]):
    db = _load_db()
    _ensure_user(uid)
    u = db["users"][str(uid)]
    r = u["roblox"]
    r["last_robux"] = int(robux)
    if username_hint:
        r["last_username"] = username_hint
    u["roblox"] = r
    db["users"][str(uid)] = u
    _save_db(db)
# =========================================================================

# ========== Constants & Embeds (기존과 동일) ==========
def pe(eid: int, name: str = None, animated: bool = False) -> discord.PartialEmoji:
    return discord.PartialEmoji(name=name, id=eid, animated=animated)

EMOJI_NOTICE = pe(1424003478275231916, name="emoji_5")
EMOJI_CHARGE = pe(1381244136627245066, name="charge")
EMOJI_INFO   = pe(1381244138355294300, name="info")
EMOJI_BUY    = pe(1381244134680957059, name="category")

PINK   = discord.Colour(int("ff5dd6", 16)); GRAY   = discord.Colour.dark_grey()
ORANGE = discord.Colour.orange(); GREEN  = discord.Colour.green(); RED    = discord.Colour.red()

def embed_panel() -> Embed:
    return Embed(title="자동 로벅스 자판기", description="아래 버튼을 눌려 이용해주세요!", colour=PINK)

def embed_notice() -> Embed:
    return Embed(title="공지", description="<#1419230737244229653> 필독 부탁드립니다", colour=GRAY)

def embed_myinfo(user: discord.User | discord.Member, stats: Dict[str, Any]) -> Embed:
    emb = Embed(title=f"{getattr(user,'display_name',getattr(user,'name','유저'))}님 정보", colour=GRAY)
    wallet = int(stats.get("wallet", 0)); total = int(stats.get("total", 0)); count = int(stats.get("count", 0))
    emb.description = "\n".join([f"### 보유 금액 : {wallet:,}원", f"### 누적 금액 : {total:,}원", f"### 거래 횟수 : {count:,}번"])
    try: emb.set_thumbnail(url=user.display_avatar.url)
    except Exception: pass
    return emb

def make_tx_select(stats: Dict[str, Any]) -> discord.ui.View:
    entries: List[Dict[str, Any]] = stats.get("recent", [])
    filtered = []
    for e in entries:
        d = (e.get("desc","") or "").lower(); t = (e.get("type","") or "").lower()
        if t in ("buy","order","trade") or any(k in d for k in ["구매","거래","주문","buy","order","trade"]):
            filtered.append(e)
    options = ([discord.SelectOption(label=f"{e.get('desc','거래')} / {int(e.get('amount',0)):,}원", value=str(i)) for i, e in enumerate(filtered)] if filtered else [discord.SelectOption(label="거래 내역 없음", value="none", default=True)])
    class TxSelect(discord.ui.Select):
        def __init__(self): super().__init__(placeholder="최근 거래내역 보기", min_values=1, max_values=1, options=options)
        async def callback(self, interaction: Interaction):
            try: await interaction.response.defer_update()
            except Exception: pass
    v = discord.ui.View(timeout=None); v.add_item(TxSelect()); return v

# ========== Roblox 파싱/로그인 (코드 길이상 생략하나, 이전 코드 포함 필수) ==========
ROBLOX_HOME_URLS = ["https://www.roblox.com/ko/home", "https://www.roblox.com/home"]
ROBLOX_LOGIN_URLS= ["https://www.roblox.com/ko/Login", "https://www.roblox.com/Login"]
ROBLOX_TX_URL    = "https://www.roblox.com/ko/transactions"
BADGE_SELECTORS = [
    "[data-testid*='nav-robux']", "a[aria-label*='Robux']", "a[aria-label*='로벅스']",
    "span[title*='Robux']", "span[title*='로벅스']",
]
BALANCE_LABEL_SELECTORS = ["text=내 잔액", "text=My Balance", "text=Balance"]
NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

# ... (여기에 이전 버전에서 제공했던 _to_int, launch_browser, robux_with_cookie 등의
# 모든 Roblox 파싱/로그인 관련 비동기 함수들이 위치해야 합니다. 코드가 길어 생략합니다.)

async def _to_int(text: str) -> Optional[int]:
    if not text: return None
    m = NUM_RE.search(text)
    if not m: return None
    try: return int(re.sub(r"[,\.\s]", "", m.group(1)))
    except Exception: return None

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
            viewport={"width": 1366, "height": 864}, locale="ko-KR", java_script_enabled=True
        )
    except Exception: return None

async def _goto(page: Page, url: str) -> bool:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        return True
    except Exception: return False

async def _wait_nav_ready(page: Page):
    for sel in BADGE_SELECTORS:
        try: await page.wait_for_selector(sel, timeout=20000); return
        except Exception: continue
    await asyncio.sleep(0.8)

async def _wait_tx_title(page: Page):
    try: await page.wait_for_selector("text=내 거래, text=My Transactions", timeout=25000)
    except Exception: await asyncio.sleep(0.8)

async def parse_home_badge(page: Page) -> Optional[int]:
    for sel in BADGE_SELECTORS:
        try:
            el = await page.query_selector(sel)
            if not el: continue
            txt = (await el.inner_text() or "").strip()
            v = await _to_int(txt);
            if isinstance(v, int) and 0 <= v <= 100_000_000: return v
        except Exception: continue
    return None

async def parse_transactions_balance(page: Page) -> Optional[int]:
    await _wait_tx_title(page)
    for sel in BALANCE_LABEL_SELECTORS:
        try:
            el = await page.query_selector(sel)
            if not el: continue
            container = await el.evaluate_handle("e => e.parentElement || e")
            txt = await (await container.get_property("innerText")).json_value()
            v = await _to_int(txt or "")
            if isinstance(v, int) and 0 <= v <= 100_000_000: return v
        except Exception: continue
    return None

async def screenshot_bytes(page: Page) -> Optional[bytes]:
    try: return await page.screenshot(type="png", full_page=False)
    except Exception: return None

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
                t = await page.title();
                if t: m = re.search(r"[A-Za-z0-9_]{3,20}", t); uname = m.group(0) if m else None
            except Exception: pass
        await page.close()
        return logged_in, uname
    except Exception: return False, None

async def robux_with_cookie(cookie: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str], Optional[bytes]]:
    try:
        async with async_playwright() as p:
            browser = await launch_browser(p)
            if not browser: return False, None, None, "브라우저 오류", None
            ctx = await new_context(browser)
            if not ctx: await browser.close(); return False, None, None, "컨텍스트 오류", None
            valid, uname = await cookie_session_login(ctx, cookie)
            if not valid: await browser.close(); return False, None, None, "세션 무효/쿠키 만료", None
            page = await ctx.new_page()
            v_tx, v_home, shot = None, None, None
            if await _goto(page, ROBLOX_TX_URL):
                v_tx = await parse_transactions_balance(page); shot = await screenshot_bytes(page)
            if not isinstance(v_tx, int):
                if await _goto(page, ROBLOX_HOME_URLS[0]) or await _goto(page, ROBLOX_HOME_URLS[1]):
                    await _wait_nav_ready(page); v_home = await parse_home_badge(page)
            v_final = v_tx if isinstance(v_tx, int) else v_home
            src = "transactions" if isinstance(v_tx, int) else ("home" if isinstance(v_home, int) else None)
            await page.close(); await browser.close()
            if isinstance(v_final, int): return True, v_final, uname, src, shot
            return False, None, uname, "로벅스 파싱 실패", shot
    except Exception: return False, None, None, "예외", None

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
                await page.wait_for_selector("input[name='username'], input#login-username, input[type='text']", timeout=25000)
                await page.fill("input[name='username'], input#login-username, input[type='text']", username)
                await page.wait_for_selector("input[name='password'], input#login-password, input[type='password']", timeout=25000)
                await page.fill("input[name='password'], input#login-password, input[type='password']", password)
                await page.click("button[type='submit'], button:has-text('로그인'), button:has-text('Log In')")
            except Exception:
                await browser.close(); return False, None, "로그인 입력/전송 실패", None
            await asyncio.sleep(1.2)
            html = await page.content()
            error_keys = ["비밀번호", "잘못", "일치하지 않", "계정이 잠김", "로그인 실패", "오류", "재시도", "다시 시도", "incorrect", "wrong password", "invalid", "try again", "blocked", "Two-step", "2단계", "Authenticator", "device verification", "Verify your device", "captcha"]
            if any(k.lower() in html.lower() for k in error_keys):
                await browser.close(); return False, None, "자격증명 오류/보안인증", None
            v_tx, v_home, shot = None, None, None
            if await _goto(page, ROBLOX_TX_URL):
                v_tx = await parse_transactions_balance(page); shot = await screenshot_bytes(page)
            if not isinstance(v_tx, int):
                if await _goto(page, ROBLOX_HOME_URLS[0]) or await _goto(page, ROBLOX_HOME_URLS[1]):
                    await _wait_nav_ready(page); v_home = await parse_home_badge(page)
            v_final = v_tx if isinstance(v_tx, int) else v_home
            await page.close(); await browser.close()
            if isinstance(v_final, int): return True, v_final, "transactions" if isinstance(v_tx, int) else "home", shot
            return False, None, "자격증명 오류/2FA/장치인증 또는 파싱 실패", shot
    except Exception: return False, None, "예외", None

# =========================================================================
# PanelView: 모든 버튼에서 defer(ephemeral=True)를 사용하여 AttributeError 해결
# =========================================================================
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="공지", emoji=EMOJI_NOTICE, style=discord.ButtonStyle.secondary, custom_id="panel_notice", row=0)
    async def notice_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(embed=embed_notice(), ephemeral=True)

    @discord.ui.button(label="충전", emoji=EMOJI_CHARGE, style=discord.ButtonStyle.secondary, custom_id="panel_charge", row=0)
    async def charge_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        uid = interaction.user.id
        
        async with button_lock: 
            add_tx(uid, 1000, "충전", "charge")
            stats = _ensure_user(uid)
            
        await interaction.followup.send(content="충전 완료!", embed=embed_myinfo(interaction.user, stats), view=make_tx_select(stats), ephemeral=True)

    @discord.ui.button(label="정보", emoji=EMOJI_INFO, style=discord.ButtonStyle.secondary, custom_id="panel_info", row=1)
    async def info_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        uid = interaction.user.id
        
        async with button_lock:
            stats = _ensure_user(uid)
            
        await interaction.followup.send(embed=embed_myinfo(interaction.user, stats), view=make_tx_select(stats), ephemeral=True)

    @discord.ui.button(label="구매", emoji=EMOJI_BUY, style=discord.ButtonStyle.secondary, custom_id="panel_buy", row=1)
    async def buy_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        uid = interaction.user.id
        
        async with button_lock: 
            add_tx(uid, -500, "구매", "buy")
            stats = _ensure_user(uid)
            
        await interaction.followup.send(content="구매 처리 완료!", embed=embed_myinfo(interaction.user, stats), view=make_tx_select(stats), ephemeral=True)


# =========================================================================
# /Command (슬래시 명령어) - /버튼패널 및 /재고 모두 포함
# =========================================================================

# 1. /버튼패널 명령어
@tree.command(name="버튼패널", description="자동 로벅스 자판기 패널을 공개로 표시합니다.")
async def 버튼패널(inter: Interaction):
    await inter.response.send_message(embed=embed_panel(), view=PanelView(), ephemeral=False)

# 2. /재고 명령어
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

        user_id = interaction.user.id
        cookie_val = (self.cookie.value or "").strip()
        id_val    = (self.uid.value or "").strip()
        pw_val    = (self.pw.value or "").strip()

        if not cookie_val and not (id_val and pw_val):
            fail = Embed(title="로그인 실패", description="쿠키나 아이디/비밀번호 중 하나 이상을 입력해줘.", colour=RED)
            await interaction.edit_original_response(embed=fail)
            return

        if cookie_val: set_login_info(user_id, cookie_val, None, None)
        if id_val or pw_val: set_login_info(user_id, None, id_val if id_val else None, pw_val if pw_val else None)

        ok, robux, name_hint, shot = False, None, None, None

        if cookie_val:
            c_ok, c_robux, c_uname, c_src, c_shot = await robux_with_cookie(cookie_val)
            if c_ok: ok, robux, name_hint, shot = True, c_robux, c_uname, c_shot

        if not ok and id_val and pw_val:
            l_ok, l_robux, l_src, l_shot = await robux_with_login(id_val, pw_val)
            if l_ok: ok, robux, name_hint, shot = True, l_robux, (name_hint or id_val), l_shot

        if ok and isinstance(robux, int):
            set_login_result(user_id, robux, name_hint)
            succ = Embed(
                title="로그인 성공",
                description=f"{(name_hint or id_val or '알 수 없음')}계정에 로그인 성공 되었습니다\n로벅스 수량 {robux:,}\n쿠키값 저장 완료되었습니다",
                colour=GREEN
            )
            files = [File(io.BytesIO(shot), filename="robux_balance.png")] if shot else []
            if files: succ.set_image(url="attachment://robux_balance.png")
            await interaction.edit_original_response(embed=succ, attachments=files)
        else:
            fail = Embed(title="로그인 실패", description="자격증명 오류/2FA/장치인증 또는 로벅스 파싱 실패", colour=RED)
            await interaction.edit_original_response(embed=fail)

@tree.command(name="재고", description="쿠키 또는 계정으로 로그인하고 로벅스 수량을 확인합니다.")
async def 재고(inter: Interaction):
    await inter.response.send_modal(StockLoginModal(inter))

# ========== 봇 이벤트 ==========
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        await tree.sync()
        print("[SYNC] global commands synced (/버튼패널, /재고)")
        bot.add_view(PanelView()) # 지속적인 뷰 로드
    except Exception as e:
        print(f"[SYNC][ERR] 명령어를 동기화하는 중 오류 발생: {e}")

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN이 .env 파일에 없거나 비정상적입니다.")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
