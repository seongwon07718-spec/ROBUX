import os, io, json, re, asyncio
from typing import Dict, Any, Optional, Tuple, List

import discord
from discord import app_commands, Interaction, Embed, File
from discord.ext import commands
from dotenv import load_dotenv

# Playwright (설치 안 되어 있으면 /재고에서 안내)
PLAYWRIGHT_OK = True
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PwTimeout
except Exception:
    PLAYWRIGHT_OK = False

# ============== 기본 설정 ==============
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN", "")
intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ============== DB 유틸 ==============
DATA_PATH = "data.json"
INIT_DATA = {"users": {}}

def db_load() -> Dict[str, Any]:
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(INIT_DATA, f, ensure_ascii=False, indent=2)
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def db_save(db: Dict[str, Any]):
    tmp = DATA_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_PATH)

def ensure_user(uid: int) -> Dict[str, Any]:
    db = db_load()
    s = str(uid)
    if s not in db["users"]:
        db["users"][s] = {
            "wallet": 0, "total": 0, "count": 0, "recent": [],
            "roblox": {"username": None, "password": None, "last_robux": 0, "last_username": None}
        }
        db_save(db); db = db_load()
    return db["users"][s]

def set_login_info(uid: int, username: str, password: str):
    db = db_load()
    u = ensure_user(uid)
    u["roblox"]["username"] = username
    u["roblox"]["password"] = password
    db["users"][str(uid)] = u
    db_save(db)

def set_login_result(uid: int, robux: int, username_hint: Optional[str] = None):
    db = db_load()
    u = ensure_user(uid)
    u["roblox"]["last_robux"] = int(robux)
    if username_hint:
        u["roblox"]["last_username"] = username_hint
    db["users"][str(uid)] = u
    db_save(db)

def reset_db():
    db_save(INIT_DATA)

# ============== 색/임베드 ==============
BLACK  = discord.Colour.dark_grey()
ORANGE = discord.Colour.orange()
GREEN  = discord.Colour.green()
RED    = discord.Colour.red()
PINK   = discord.Colour(int("ff5dd6", 16))

def embed_panel() -> Embed:
    return Embed(title="자동 로벅스 자판기", description="아래 버튼을 눌러 이용해줘!", colour=PINK)

def embed_notice() -> Embed:
    return Embed(title="공지", description="<#1419230737244229653> 필독 부탁!", colour=BLACK)

def embed_myinfo(user: discord.User | discord.Member, stats: Dict[str, Any]) -> Embed:
    e = Embed(title=f"{getattr(user,'display_name',user.name)}님 정보", colour=BLACK)
    wallet = int(stats.get("wallet", 0))
    total = int(stats.get("total", 0))
    count = int(stats.get("count", 0))
    e.description = "\n".join([
        f"보유 금액 : `{wallet}`원",
        f"누적 금액 : `{total}`원",
        f"거래 횟수 : `{count}`번",
    ])
    try:
        e.set_thumbnail(url=user.display_avatar.url)
    except Exception:
        pass
    return e

def make_tx_select(stats: Dict[str, Any]) -> discord.ui.View:
    entries: List[Dict[str, Any]] = stats.get("recent", [])
    options = [discord.SelectOption(label="거래 내역 없음", value="none", default=True)] if not entries else [
        discord.SelectOption(label=f"{e.get('desc','거래')} / {int(e.get('amount',0)):,}원", value=str(i))
        for i, e in enumerate(entries)
    ]
    class TxSelect(discord.ui.Select):
        def __init__(self):
            super().__init__(placeholder="최근 거래내역 보기", min_values=1, max_values=1, options=options)
        async def callback(self, interaction: Interaction):
            try:
                await interaction.response.defer_update()
            except Exception:
                pass
    v = discord.ui.View(timeout=None)
    v.add_item(TxSelect())
    return v

# ============== Roblox 로그인/파싱 ==============
ROBLOX_LOGIN_URLS = [
    "https://www.roblox.com/Login",
    "https://www.roblox.com/ko/Login",
    "https://www.roblox.com/vi/Login",
]
ROBLOX_HOME_URLS = [
    "https://www.roblox.com/home",
    "https://www.roblox.com/ko/home",
]
ROBLOX_TX_URL = "https://www.roblox.com/ko/transactions"

NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

BADGE_SELECTORS = [
    "[data-testid*='nav-robux']",
    "a[aria-label*='Robux']",
    "a[aria-label*='로벅스']",
    "span[title*='Robux']",
    "span[title*='로벅스']",
]
BALANCE_LABEL_SELECTORS = ["text=내 잔액", "text=My Balance", "text=Balance"]

def _to_int(txt: str) -> Optional[int]:
    if not txt: return None
    m = NUM_RE.search(txt)
    if not m: return None
    try: return int(re.sub(r"[,\.\s]", "", m.group(1)))
    except Exception: return None

async def _launch(p):
    args = ["--disable-dev-shm-usage","--no-sandbox","--disable-gpu","--disable-setuid-sandbox","--no-zygote"]
    try:
        return await p.chromium.launch(headless=True, args=args)
    except Exception:
        return None

async def _ctx(browser: Browser):
    try:
        return await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
            viewport={"width": 1366, "height": 864}, locale="ko-KR", java_script_enabled=True
        )
    except Exception:
        return None

async def _goto(page: Page, url: str) -> bool:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        return True
    except Exception:
        return False

async def _wait_tx_title(page: Page):
    try:
        await page.wait_for_selector("text=내 거래, text=My Transactions", timeout=25000)
    except Exception:
        await asyncio.sleep(0.8)

async def _wait_nav_ready(page: Page):
    for sel in BADGE_SELECTORS:
        try:
            await page.wait_for_selector(sel, timeout=20000)
            return
        except Exception:
            continue
    await asyncio.sleep(0.8)

async def _parse_home(page: Page) -> Optional[int]:
    for sel in BADGE_SELECTORS:
        try:
            el = await page.query_selector(sel)
            if not el: continue
            txt = (await el.inner_text() or "").strip()
            v = _to_int(txt)
            if isinstance(v, int) and 0 <= v <= 100_000_000:
                return v
        except Exception:
            continue
    return None

async def _parse_tx(page: Page) -> Optional[int]:
    await _wait_tx_title(page)
    for sel in BALANCE_LABEL_SELECTORS:
        try:
            el = await page.query_selector(sel)
            if not el: continue
            container = await el.evaluate_handle("e => e.parentElement || e")
            txt = await (await container.get_property("innerText")).json_value()
            v = _to_int(txt or "")
            if isinstance(v, int) and 0 <= v <= 100_000_000:
                return v
        except Exception:
            continue
    # 텍스트 근처 스캔
    try:
        html = await page.content()
        nums = []
        for kw in ["내 잔액","My Balance","Balance"]:
            for m in re.finditer(kw, html, flags=re.IGNORECASE):
                s = max(0, m.start()-240); e = min(len(html), m.end()+240)
                chunk = html[s:e]
                for mm in re.finditer(NUM_RE, chunk):
                    v = _to_int(mm.group(0))
                    if isinstance(v, int) and 0 <= v <= 100_000_000:
                        nums.append(v)
        if nums: return min(nums)
    except Exception:
        pass
    return None

async def _shot(page: Page) -> Optional[bytes]:
    try:
        return await page.screenshot(type="png", full_page=False)
    except Exception:
        return None

async def roblox_login_and_balance(username: str, password: str) -> Tuple[bool, Optional[int], str, Optional[bytes]]:
    if not PLAYWRIGHT_OK:
        return False, None, "Playwright 미설치", None
    try:
        async with async_playwright() as p:
            browser = await _launch(p)
            if not browser: return False, None, "브라우저 오류", None
            ctx = await _ctx(browser)
            if not ctx: await browser.close(); return False, None, "컨텍스트 오류", None
            page = await ctx.new_page()

            moved = False
            for url in ROBLOX_LOGIN_URLS:
                if await _goto(page, url):
                    moved = True; break
            if not moved:
                await browser.close(); return False, None, "로그인 페이지 이동 실패", None

            # 아이디
            ok_id = False
            for sel in ["input#login-username", "input[name='username']", "input[type='text']"]:
                try:
                    await page.fill(sel, username)
                    ok_id = True; break
                except Exception:
                    continue
            if not ok_id:
                await browser.close(); return False, None, "아이디 입력 실패", None

            # 비밀번호
            ok_pw = False
            for sel in ["input#login-password", "input[name='password']", "input[type='password']"]:
                try:
                    await page.fill(sel, password)
                    ok_pw = True; break
                except Exception:
                    continue
            if not ok_pw:
                await browser.close(); return False, None, "비밀번호 입력 실패", None

            # 로그인 버튼
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

            await asyncio.sleep(1.5)
            html = await page.content()
            security_keys = ["Two-step","2단계","Authenticator","device verification","Verify your device","captcha","hcaptcha","recaptcha"]
            cred_keys = ["비밀번호","잘못","일치하지 않","계정이 잠김","로그인 실패","오류","재시도","다시 시도","incorrect","wrong password","invalid","try again","blocked"]
            if any(k.lower() in html.lower() for k in security_keys):
                shot = await _shot(page); await browser.close()
                return False, None, "보안인증(2FA/캡차/장치인증)", shot
            if any(k.lower() in html.lower() for k in cred_keys):
                shot = await _shot(page); await browser.close()
                return False, None, "자격증명 오류", shot

            v_tx, v_home, shot = None, None, None
            if await _goto(page, ROBLOX_TX_URL):
                v_tx = await _parse_tx(page); shot = await _shot(page)
            if not isinstance(v_tx, int):
                for home in ROBLOX_HOME_URLS:
                    if await _goto(page, home):
                        await _wait_nav_ready(page)
                        v_home = await _parse_home(page)
                        if not shot: shot = await _shot(page)
                        break

            v_final = v_tx if isinstance(v_tx, int) else v_home
            await page.close(); await browser.close()
            if isinstance(v_final, int):
                return True, v_final, "ok", shot
            else:
                return False, None, "로벅스 파싱 실패", shot
    except PwTimeout:
        return False, None, "응답 지연", None
    except Exception:
        return False, None, "예외", None

# ============== 패널 뷰 ==============
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="공지", style=discord.ButtonStyle.secondary, custom_id="panel_notice", row=0)
    async def notice_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=embed_notice(), ephemeral=True)

    @discord.ui.button(label="충전", style=discord.ButtonStyle.secondary, custom_id="panel_charge", row=0)
    async def charge_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message("충전 기능 준비 중이야.", ephemeral=True)

    @discord.ui.button(label="정보", style=discord.ButtonStyle.secondary, custom_id="panel_info", row=1)
    async def info_button(self, interaction: Interaction, button: discord.ui.Button):
        stats = ensure_user(interaction.user.id)
        await interaction.response.send_message(embed=embed_myinfo(interaction.user, stats), view=make_tx_select(stats), ephemeral=True)

    @discord.ui.button(label="구매", style=discord.ButtonStyle.secondary, custom_id="panel_buy", row=1)
    async def buy_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message("구매 기능 준비 중이야.", ephemeral=True)

# ============== 모달(/재고) ==============
class StockLoginModal(discord.ui.Modal, title="로그인"):
    id_input = discord.ui.TextInput(label="아이디", required=True, max_length=100)
    pw_input = discord.ui.TextInput(label="비밀번호", required=True, max_length=100)

    def __init__(self, inter: Interaction):
        super().__init__(timeout=None)
        self._inter = inter

    async def on_submit(self, interaction: Interaction):
        await interaction.response.send_message(embed=Embed(title="로그인 중..", description="잠시만 기다려줘!", colour=ORANGE), ephemeral=True)
        if not PLAYWRIGHT_OK:
            await interaction.edit_original_response(embed=Embed(title="실패", description="Playwright 미설치 상태야. 환경 먼저 구성해줘.", colour=RED))
            return

        username = (self.id_input.value or "").strip()
        password = (self.pw_input.value or "").strip()
        set_login_info(interaction.user.id, username, password)

        ok, amount, reason, shot = await roblox_login_and_balance(username, password)
        if ok and isinstance(amount, int):
            set_login_result(interaction.user.id, amount, username)
            succ = Embed(title="로그인 성공", description=f"{username} 계정 로그인 성공\n로벅스 수량 {amount:,}", colour=GREEN)
            files = [File(io.BytesIO(shot), filename="balance.png")] if shot else []
            if files: succ.set_image(url="attachment://balance.png")
            await interaction.edit_original_response(embed=succ, attachments=files)
        else:
            fail = Embed(title="로그인 실패", description=reason or "자격증명/보안인증/파싱 실패", colour=RED)
            if shot:
                fail.set_image(url="attachment://balance.png")
                await interaction.edit_original_response(embed=fail, attachments=[File(io.BytesIO(shot), filename="balance.png")])
            else:
                await interaction.edit_original_response(embed=fail)

# ============== 슬래시 명령 ==============
@tree.command(name="버튼패널", description="자판기 패널을 공개로 표시합니다.")
async def 버튼패널(inter: Interaction):
    await inter.response.send_message(embed=embed_panel(), view=PanelView(), ephemeral=False)

@tree.command(name="재고", description="아이디/비밀번호로 로그인하고 로벅스 수량을 확인합니다.")
async def 재고(inter: Interaction):
    await inter.response.send_modal(StockLoginModal(inter))

@tree.command(name="디비초기화", description="DB를 초기 상태로 되돌립니다(관리자만).")
@app_commands.checks.has_permissions(administrator=True)
async def 디비초기화(inter: Interaction):
    reset_db()
    await inter.response.send_message("DB 초기화 완료.", ephemeral=True)

# ============== 이벤트/부팅 ==============
@bot.event
async def on_ready():
    print(f"[ready] Logged in as {bot.user}")
    try:
        cmds = await tree.sync()
        print("[SYNC]", ", ".join("/"+c.name for c in cmds))
        bot.add_view(PanelView())  # persistent view
    except Exception as e:
        print("[SYNC][ERR]", e)

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN 누락 또는 비정상")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
