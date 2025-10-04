import os, io, json, time, re, asyncio
from typing import Dict, Any, List, Optional, Tuple

import discord
from discord import app_commands, Interaction, Embed, File
from discord.ext import commands
from dotenv import load_dotenv

# Playwright는 선택 설치. 미설치면 /재고 시 안내
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PwTimeout
    PLAYWRIGHT_OK = True
except Exception:
    PLAYWRIGHT_OK = False

# ========================================
# 기본설정
# ========================================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ========================================
# DB 최소 유틸
# ========================================
DATA_PATH = "data.json"
io_lock = asyncio.Lock()
button_lock = asyncio.Lock()   # 상호작용 경합 방지

INIT_DATA = {"users": {}}

def _load_db() -> Dict[str, Any]:
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(INIT_DATA, f, ensure_ascii=False, indent=2)
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_db(db: Dict[str, Any]):
    tmp = DATA_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_PATH)

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

def set_login_info(uid: int, cookie: Optional[str], username: Optional[str], password: Optional[str]):
    db = _load_db()
    u = _ensure_user(uid)
    r = u["roblox"]
    if cookie is not None and cookie != "": r["cookie"] = cookie
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
    if username_hint: r["last_username"] = username_hint
    u["roblox"] = r
    db["users"][str(uid)] = u
    _save_db(db)

def reset_db():
    _save_db(INIT_DATA)

# ========================================
# 이모지/색/임베드
# ========================================
def pe(eid: int, name: str = None, animated: bool = False) -> discord.PartialEmoji:
    return discord.PartialEmoji(name=name, id=eid, animated=animated)

# 네가 쓰던 커스텀 이모지 ID는 그대로 유지(없어도 동작)
EMOJI_NOTICE = pe(1424003478275231916, name="emoji_5")
EMOJI_CHARGE = pe(1381244136627245066, name="charge")
EMOJI_INFO   = pe(1381244138355294300, name="info")
EMOJI_BUY    = pe(1381244134680957059, name="category")

PINK   = discord.Colour(int("ff5dd6", 16))    # 패널
BLACK  = discord.Colour.dark_grey()           # 공지/정보(검정 계열)
ORANGE = discord.Colour.orange()              # 로딩
GREEN  = discord.Colour.green()               # 성공
RED    = discord.Colour.red()                 # 실패

def embed_panel() -> Embed:
    return Embed(title="자동 로벅스 자판기", description="아래 버튼을 눌러 이용해주세요!", colour=PINK)

def embed_notice() -> Embed:
    # 요청: 임베드 검정
    return Embed(title="공지", description="<#1419230737244229653> 필독 부탁드립니다", colour=BLACK)

def embed_myinfo(user: discord.User | discord.Member, stats: Dict[str, Any]) -> Embed:
    # 요청 포맷에 맞춤 + 검정
    name = getattr(user, 'display_name', getattr(user, 'name', '유저'))
    emb = Embed(title=f"{name}님 정보", colour=BLACK)
    wallet = int(stats.get("wallet", 0))
    total  = int(stats.get("total", 0))
    count  = int(stats.get("count", 0))
    emb.description = "\n".join([
        f"보유 금액 : `{wallet}`원",
        f"누적 금액 : `{total}`원",
        f"거래 횟수 : `{count}`번",
    ])
    try:
        emb.set_thumbnail(url=user.display_avatar.url)
    except Exception:
        pass
    return emb

def make_tx_select(stats: Dict[str, Any]) -> discord.ui.View:
    entries: List[Dict[str, Any]] = stats.get("recent", [])
    filtered = []
    for e in entries:
        t = (e.get("type","") or "").lower()
        d = (e.get("desc","") or "").lower()
        if t in ("buy","order","trade","charge") or any(k in d for k in ["구매","거래","주문","충전","buy","order","trade","charge"]):
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
    v = discord.ui.View(timeout=None)
    v.add_item(TxSelect())
    return v

# ========================================
# Roblox 로그인/파싱(실제 로그인)
# ========================================
ROBLOX_HOME_URLS = [
    "https://www.roblox.com/ko/home",
    "https://www.roblox.com/home"
]
ROBLOX_LOGIN_URLS= [
    "https://www.roblox.com/ko/Login",
    "https://www.roblox.com/Login",
    "https://www.roblox.com/vi/Login",
]
ROBLOX_TX_URL    = "https://www.roblox.com/ko/transactions"

BADGE_SELECTORS = [
    "[data-testid*='nav-robux']",
    "a[aria-label*='Robux']",
    "a[aria-label*='로벅스']",
    "span[title*='Robux']",
    "span[title*='로벅스']",
]
BALANCE_LABEL_SELECTORS = ["text=내 잔액", "text=My Balance", "text=Balance"]
NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

def _to_int(text: str) -> Optional[int]:
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
    except Exception:
        return None

async def _goto(page: Page, url: str) -> bool:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000); return True
    except Exception:
        return False

async def _wait_nav_ready(page: Page):
    # 상단 네비에 로벅스 뱃지 나타날 때까지 최대 대기
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
            v = _to_int(txt)
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
            v = _to_int(txt or "")
            if isinstance(v, int) and 0 <= v <= 100_000_000: return v
        except Exception: continue
    # 라벨 기반 실패 시 주변 문맥 스캔
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
    except Exception: pass
    return None

async def screenshot_bytes(page: Page) -> Optional[bytes]:
    try: return await page.screenshot(type="png", full_page=False)
    except Exception: return None

async def robux_with_login(username: str, password: str) -> Tuple[bool, Optional[int], Optional[str], Optional[bytes]]:
    if not PLAYWRIGHT_OK:
        return False, None, "자동화 모듈 미설치", None
    try:
        async with async_playwright() as p:
            browser = await launch_browser(p)
            if not browser: return False, None, "브라우저 오류", None
            ctx = await new_context(browser)
            if not ctx: await browser.close(); return False, None, "컨텍스트 오류", None
            page = await ctx.new_page()

            # 로그인 페이지 후보 여러 개 순회
            moved = False
            for url in ROBLOX_LOGIN_URLS:
                if await _goto(page, url):
                    moved = True; break
            if not moved:
                await browser.close(); return False, None, "로그인 페이지 이동 실패", None

            # 필드 대기를 강화하고 여러 셀렉터로 안전 입력
            try:
                await page.wait_for_selector("input[name='username'], input#login-username, input[type='text']", timeout=25000)
                # 일부 페이지는 같은 셀렉터가 여러 개 → 첫번째 필드 선택
                await page.fill("input#login-username", username).catch(lambda *_: None)
            except Exception:
                try:
                    await page.fill("input[name='username']", username)
                except Exception:
                    try:
                        inp = await page.query_selector("input[type='text']")
                        if inp: await inp.fill(username)
                    except Exception:
                        await browser.close(); return False, None, "아이디 입력 실패", None

            try:
                await page.wait_for_selector("input[name='password'], input#login-password, input[type='password']", timeout=25000)
                await page.fill("input#login-password", password).catch(lambda *_: None)
            except Exception:
                try:
                    await page.fill("input[name='password']", password)
                except Exception:
                    try:
                        pinp = await page.query_selector("input[type='password']")
                        if pinp: await pinp.fill(password)
                    except Exception:
                        await browser.close(); return False, None, "비밀번호 입력 실패", None

            # 로그인 버튼 클릭 후보들
            try:
                clicked = False
                for sel in ["button#login-button", "button[type='submit']", "button:has-text('로그인')", "button:has-text('Log In')"]:
                    try:
                        btn = await page.query_selector(sel)
                        if btn:
                            await btn.click(); clicked = True; break
                    except Exception:
                        continue
                if not clicked:
                    await browser.close(); return False, None, "로그인 버튼 클릭 실패", None
            except Exception:
                await browser.close(); return False, None, "로그인 전송 실패", None

            # 처리 대기 + 보안 이슈/오류 감지
            await asyncio.sleep(1.5)
            html = await page.content()
            security_keys = ["Two-step","2단계","Authenticator","device verification","Verify your device","captcha","hcaptcha","recaptcha"]
            cred_keys = ["비밀번호","잘못","일치하지 않","계정이 잠김","로그인 실패","오류","재시도","다시 시도","incorrect","wrong password","invalid","try again","blocked"]

            if any(k.lower() in html.lower() for k in security_keys):
                shot = await screenshot_bytes(page); await browser.close()
                return False, None, "보안인증(2FA/캡차/장치인증)", shot
            if any(k.lower() in html.lower() for k in cred_keys):
                shot = await screenshot_bytes(page); await browser.close()
                return False, None, "자격증명 오류", shot

            # 잔액 우선: 거래페이지 → 홈 네비
            v_tx, v_home, shot = None, None, None
            if await _goto(page, ROBLOX_TX_URL):
                v_tx = await parse_transactions_balance(page); shot = await screenshot_bytes(page)
            if not isinstance(v_tx, int):
                moved_home = False
                for hu in ROBLOX_HOME_URLS:
                    if await _goto(page, hu):
                        moved_home = True; break
                if moved_home:
                    await _wait_nav_ready(page); v_home = await parse_home_badge(page)
                    if not shot: shot = await screenshot_bytes(page)

            v_final = v_tx if isinstance(v_tx, int) else v_home
            await page.close(); await browser.close()
            if isinstance(v_final, int): return True, v_final, "ok", shot
            return False, None, "로벅스 파싱 실패", shot
    except PwTimeout:
        return False, None, "응답 지연", None
    except Exception:
        return False, None, "예외", None

# ========================================
# 패널 뷰(충전/구매 비활성, DB 변경 없음)
# ========================================
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="공지", emoji=EMOJI_NOTICE, style=discord.ButtonStyle.secondary, custom_id="panel_notice", row=0)
    async def notice_button(self, interaction: Interaction, button: discord.ui.Button):
        async with button_lock:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send(embed=embed_notice(), ephemeral=True)

    @discord.ui.button(label="충전", emoji=EMOJI_CHARGE, style=discord.ButtonStyle.secondary, custom_id="panel_charge", row=0)
    async def charge_button(self, interaction: Interaction, button: discord.ui.Button):
        async with button_lock:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send(content="충전 기능은 준비 중이야. 지금은 동작하지 않아.", ephemeral=True)

    @discord.ui.button(label="정보", emoji=EMOJI_INFO, style=discord.ButtonStyle.secondary, custom_id="panel_info", row=1)
    async def info_button(self, interaction: Interaction, button: discord.ui.Button):
        async with button_lock:
            await interaction.response.defer(ephemeral=True)
            uid = interaction.user.id
            stats = _ensure_user(uid)
            await interaction.followup.send(embed=embed_myinfo(interaction.user, stats), view=make_tx_select(stats), ephemeral=True)

    @discord.ui.button(label="구매", emoji=EMOJI_BUY, style=discord.ButtonStyle.secondary, custom_id="panel_buy", row=1)
    async def buy_button(self, interaction: Interaction, button: discord.ui.Button):
        async with button_lock:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send(content="구매 기능은 준비 중이야. 지금은 동작하지 않아.", ephemeral=True)

# ========================================
# 로그인 모달(/재고)
# ========================================
class StockLoginModal(discord.ui.Modal, title="로그인"):
    # 요청: id/pw 입력 기반으로 정확 입력
    uid    = discord.ui.TextInput(label="아이디", required=True, style=discord.TextStyle.short, max_length=100)
    pw     = discord.ui.TextInput(label="비밀번호", required=True, style=discord.TextStyle.short, max_length=100)

    def __init__(self, inter: Interaction):
        super().__init__(timeout=None)
        self.inter = inter

    async def on_submit(self, interaction: Interaction):
        await interaction.response.send_message(embed=Embed(title="로그인 중..", description="조금만 기다려줘!", colour=ORANGE), ephemeral=True)
        _ = await interaction.original_response()

        if not PLAYWRIGHT_OK:
            await interaction.edit_original_response(embed=Embed(title="실패", description="Playwright가 설치되지 않았어. 관리자가 환경을 설정해야 해.", colour=RED))
            return

        user_id = interaction.user.id
        id_val = (self.uid.value or "").strip()
        pw_val = (self.pw.value or "").strip()

        # DB에 최신 로그인 정보 저장
        set_login_info(user_id, None, id_val, pw_val)

        ok, robux, reason, shot = await robux_with_login(id_val, pw_val)
        if ok and isinstance(robux, int):
            set_login_result(user_id, robux, id_val)
            succ = Embed(
                title="로그인 성공",
                description=f"{id_val} 계정 로그인 성공\n로벅스 수량 {robux:,}",
                colour=GREEN
            )
            files = [File(io.BytesIO(shot), filename="robux_balance.png")] if shot else []
            if files: succ.set_image(url="attachment://robux_balance.png")
            await interaction.edit_original_response(embed=succ, attachments=files)
        else:
            fail = Embed(title="로그인 실패", description=reason or "자격증명/보안인증/파싱 실패", colour=RED)
            if shot:
                fail.set_image(url="attachment://robux_balance.png")
                await interaction.edit_original_response(embed=fail, attachments=[File(io.BytesIO(shot), filename="robux_balance.png")])
            else:
                await interaction.edit_original_response(embed=fail)

# ========================================
# 슬래시 명령
# ========================================
@tree.command(name="버튼패널", description="자동 로벅스 자판기 패널을 공개로 표시합니다.")
async def 버튼패널(inter: Interaction):
    await inter.response.send_message(embed=embed_panel(), view=PanelView(), ephemeral=False)

@tree.command(name="재고", description="아이디/비밀번호로 로그인하고 로벅스 수량을 확인합니다.")
async def 재고(inter: Interaction):
    await inter.response.send_modal(StockLoginModal(inter))

# 관리자용: DB 초기화 요청대로 추가
@tree.command(name="디비초기화", description="DB를 초기 상태로 되돌립니다(관리자만).")
@app_commands.checks.has_permissions(administrator=True)
async def 디비초기화(inter: Interaction):
    reset_db()
    await inter.response.send_message("DB 초기화 완료.", ephemeral=True)

# ========================================
# 이벤트
# ========================================
@bot.event
async def on_ready():
    print(f"[ready] Logged in as {bot.user}")
    try:
        # 글로벌 싱크(현 코드 명령 3개만 등록)
        cmds = await tree.sync()
        print(f"[SYNC] commands synced: {', '.join('/'+c.name for c in cmds)}")
        # 퍼시스턴트 뷰 등록
        bot.add_view(PanelView())
    except Exception as e:
        print(f"[SYNC][ERR] {e}")

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN이 .env에 없거나 비정상")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
