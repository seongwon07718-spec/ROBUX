import os, io, json, re, asyncio
from typing import Dict, Any, Optional, Tuple, List

import discord
from discord import app_commands, Interaction, Embed, File
from discord.ext import commands
from dotenv import load_dotenv

# Playwright 존재 확인
PLAYWRIGHT_OK = True
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PwTimeout
except Exception:
    PLAYWRIGHT_OK = False

# ================== 기본 설정 ==================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN", "")
intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ================== DB 유틸 ==================
DATA_PATH = "data.json"
INIT_DATA = {"users": {}}
_io_lock = asyncio.Lock()
_button_lock = asyncio.Lock()

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
            "roblox": {
                "cookie": None,
                "username": None,
                "password": None,
                "last_robux": 0,
                "last_username": None
            }
        }
        db_save(db); db = db_load()
    return db["users"][s]

def set_cookie(uid: int, cookie: Optional[str]):
    db = db_load()
    u = ensure_user(uid)
    if cookie:
        u["roblox"]["cookie"] = cookie
    db["users"][str(uid)] = u
    db_save(db)

def set_login_info(uid: int, username: Optional[str], password: Optional[str]):
    db = db_load()
    u = ensure_user(uid)
    if username is not None:
        u["roblox"]["username"] = username
    if password is not None:
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

# ================== 이모지/색/임베드 ==================
def pe(eid: int, name: str = None, animated: bool = False) -> discord.PartialEmoji:
    return discord.PartialEmoji(name=name, id=eid, animated=animated)

# 요구한 커스텀 이모지 그대로
EMOJI_NOTICE = pe(1424003478275231916, name="emoji_5")
EMOJI_CHARGE = pe(1381244136627245066, name="charge")
EMOJI_INFO   = pe(1381244138355294300, name="info")
EMOJI_BUY    = pe(1381244134680957059, name="category")

def color_hex(hex_str: str) -> discord.Colour:
    # "#000000" 또는 "000000" 모두 허용
    h = hex_str.lower().replace("#", "")
    return discord.Colour(int(h, 16))

COLOR_BLACK = color_hex("000000")

def embed_panel() -> Embed:
    return Embed(title="자동 로벅스 자판기", description="아래 버튼을 눌러 이용해줘!", colour=color_hex("ff5dd6"))

def embed_notice() -> Embed:
    return Embed(title="공지", description="<#1419230737244229653> 필독 부탁!", colour=COLOR_BLACK)

def embed_myinfo(user: discord.User | discord.Member, stats: Dict[str, Any]) -> Embed:
    e = Embed(title=f"{getattr(user,'display_name',user.name)}님 정보", colour=COLOR_BLACK)
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

def embed_state(title: str, desc: str) -> Embed:
    return Embed(title=title, description=desc, colour=COLOR_BLACK)

# ================== Roblox 로그인/파싱 ==================
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
BALANCE_LABELS = ["내 잔액", "My Balance", "Balance"]

BADGE_SELECTORS = [
    "[data-testid*='nav-robux']",
    "a[aria-label*='Robux']",
    "a[aria-label*='로벅스']",
    "span[title*='Robux']",
    "span[title*='로벅스']",
]

SECURITY_KEYS = [
    # 2FA/MFA
    ("two_factor", ["two-step", "2단계", "authenticator", "otp"]),
    # 디바이스 인증
    ("device_verification", ["verify your device", "장치 인증", "새 기기", "was this you", "device verification"]),
    # 캡차
    ("captcha", ["captcha", "hcaptcha", "recaptcha", "i’m not a robot", "i am not a robot"]),
]

CREDENTIAL_KEYS = ["incorrect", "wrong password", "invalid", "비밀번호", "아이디", "로그인 실패", "일치하지 않", "다시 시도", "재시도", "blocked", "suspended"]

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

async def _shot(page: Page) -> Optional[bytes]:
    try:
        return await page.screenshot(type="png", full_page=False)
    except Exception:
        return None

def _detect_security(html: str) -> Optional[str]:
    low = html.lower()
    for key, keywords in SECURITY_KEYS:
        for kw in keywords:
            if kw in low:
                if key == "two_factor": return "2단계 인증(MFA) 필요"
                if key == "device_verification": return "디바이스 인증(새 기기 확인) 필요"
                if key == "captcha": return "캡차(hCaptcha/reCAPTCHA) 발생"
    return None

def _detect_credential_error(html: str) -> bool:
    low = html.lower()
    return any(kw in low for kw in CREDENTIAL_KEYS)

async def _parse_tx(page: Page) -> Optional[int]:
    try:
        await page.wait_for_selector("text=내 거래, text=My Transactions", timeout=25000)
    except Exception:
        await asyncio.sleep(0.8)
    # 라벨 인접 텍스트 우선
    for label in BALANCE_LABELS:
        try:
            el = await page.query_selector(f"text={label}")
            if not el: continue
            container = await el.evaluate_handle("e => e.parentElement || e")
            txt = await (await container.get_property("innerText")).json_value()
            v = _to_int(txt or "")
            if isinstance(v, int) and 0 <= v <= 100_000_000:
                return v
        except Exception:
            continue
    # 정 안 되면 주변 문맥 스캔
    try:
        html = await page.content()
        nums = []
        for kw in BALANCE_LABELS:
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

async def _parse_home(page: Page) -> Optional[int]:
    # 상단 네비 로벅스 뱃지에서 숫자 추출
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

# cookie 세션 로그인
async def robux_with_cookie(cookie: str) -> Tuple[bool, Optional[int], str, Optional[bytes]]:
    if not PLAYWRIGHT_OK:
        return False, None, "Playwright 미설치", None
    if not cookie or ".ROBLOSECURITY" not in cookie:
        return False, None, "쿠키 형식 오류(.ROBLOSECURITY 필요)", None
    try:
        async with async_playwright() as p:
            browser = await _launch(p)
            if not browser: return False, None, "브라우저 오류", None
            ctx = await _ctx(browser)
            if not ctx: await browser.close(); return False, None, "컨텍스트 오류", None
            await ctx.add_cookies([{
                "name": ".ROBLOSECURITY",
                "value": cookie.strip(),
                "domain": ".roblox.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax"
            }])
            page = await ctx.new_page()

            # 거래 → 홈 순
            v_tx, v_home, shot = None, None, None
            if await _goto(page, ROBLOX_TX_URL):
                html = await page.content()
                sec = _detect_security(html)
                if sec:
                    shot = await _shot(page); await browser.close()
                    return False, None, sec, shot
                v_tx = await _parse_tx(page); shot = await _shot(page)
            if not isinstance(v_tx, int):
                for home in ROBLOX_HOME_URLS:
                    if await _goto(page, home):
                        html = await page.content()
                        sec = _detect_security(html)
                        if sec:
                            shot = await _shot(page); await browser.close()
                            return False, None, sec, shot
                        v_home = await _parse_home(page)
                        if not shot: shot = await _shot(page)
                        break
            v_final = v_tx if isinstance(v_tx, int) else v_home
            await page.close(); await browser.close()
            if isinstance(v_final, int):
                return True, v_final, "ok", shot
            return False, None, "로벅스 파싱 실패", shot
    except PwTimeout:
        return False, None, "응답 지연", None
    except Exception:
        return False, None, "예외", None

# id/pw 로그인
async def robux_with_login(username: str, password: str) -> Tuple[bool, Optional[int], str, Optional[bytes]]:
    if not PLAYWRIGHT_OK:
        return False, None, "Playwright 미설치", None
    try:
        async with async_playwright() as p:
            browser = await _launch(p)
            if not browser: return False, None, "브라우저 오류", None
            ctx = await _ctx(browser)
            if not ctx: await browser.close(); return False, None, "컨텍스트 오류", None
            page = await ctx.new_page()

            # 로그인 페이지 후보 순회
            moved = False
            for url in ROBLOX_LOGIN_URLS:
                if await _goto(page, url):
                    moved = True; break
            if not moved:
                await browser.close(); return False, None, "로그인 페이지 이동 실패", None

            # 입력
            id_ok = False
            for sel in ["input#login-username", "input[name='username']", "input[type='text']"]:
                try:
                    await page.fill(sel, username); id_ok = True; break
                except Exception:
                    continue
            if not id_ok:
                await browser.close(); return False, None, "아이디 입력 실패", None

            pw_ok = False
            for sel in ["input#login-password", "input[name='password']", "input[type='password']"]:
                try:
                    await page.fill(sel, password); pw_ok = True; break
                except Exception:
                    continue
            if not pw_ok:
                await browser.close(); return False, None, "비밀번호 입력 실패", None

            # 제출
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

            sec = _detect_security(html)
            if sec:
                shot = await _shot(page); await browser.close()
                return False, None, sec, shot

            if _detect_credential_error(html):
                shot = await _shot(page); await browser.close()
                return False, None, "자격증명 오류(아이디/비밀번호 불일치)", shot

            # 잔액 파싱
            v_tx, v_home, shot = None, None, None
            if await _goto(page, ROBLOX_TX_URL):
                v_tx = await _parse_tx(page); shot = await _shot(page)
            if not isinstance(v_tx, int):
                for home in ROBLOX_HOME_URLS:
                    if await _goto(page, home):
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

# ================== 패널 뷰 ==================
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="공지", emoji=EMOJI_NOTICE, style=discord.ButtonStyle.secondary, custom_id="panel_notice", row=0)
    async def notice_button(self, interaction: Interaction, button: discord.ui.Button):
        async with _button_lock:
            await interaction.response.send_message(embed=embed_notice(), ephemeral=True)

    @discord.ui.button(label="충전", emoji=EMOJI_CHARGE, style=discord.ButtonStyle.secondary, custom_id="panel_charge", row=0)
    async def charge_button(self, interaction: Interaction, button: discord.ui.Button):
        async with _button_lock:
            await interaction.response.send_message(embed=embed_state("충전", "충전 기능은 준비 중이야."), ephemeral=True)

    @discord.ui.button(label="정보", emoji=EMOJI_INFO, style=discord.ButtonStyle.secondary, custom_id="panel_info", row=1)
    async def info_button(self, interaction: Interaction, button: discord.ui.Button):
        async with _button_lock:
            stats = ensure_user(interaction.user.id)
            await interaction.response.send_message(embed=embed_myinfo(interaction.user, stats), ephemeral=True)

    @discord.ui.button(label="구매", emoji=EMOJI_BUY, style=discord.ButtonStyle.secondary, custom_id="panel_buy", row=1)
    async def buy_button(self, interaction: Interaction, button: discord.ui.Button):
        async with _button_lock:
            await interaction.response.send_message(embed=embed_state("구매", "구매 기능은 준비 중이야."), ephemeral=True)

# ================== /재고 모달 ==================
class StockLoginModal(discord.ui.Modal, title="로그인"):
    cookie_input = discord.ui.TextInput(label="cookie(.ROBLOSECURITY)", required=False, max_length=4000, placeholder=".ROBLOSECURITY=로_시작하는 값")
    id_input = discord.ui.TextInput(label="아이디", required=False, max_length=100, placeholder="아이디(선택, 쿠키 없을 때 사용)")
    pw_input = discord.ui.TextInput(label="비밀번호", required=False, max_length=100, placeholder="비밀번호(선택, 쿠키 없을 때 사용)")

    def __init__(self, inter: Interaction):
        super().__init__(timeout=None)
        self._inter = inter

    async def on_submit(self, interaction: Interaction):
        await interaction.response.send_message(embed=embed_state("로그인 중..", "잠시만 기다려줘!"), ephemeral=True)

        cookie = (self.cookie_input.value or "").strip()
        uid = (self.id_input.value or "").strip()
        pw = (self.pw_input.value or "").strip()

        # 저장
        if cookie:
            set_cookie(interaction.user.id, cookie)
        if uid or pw:
            set_login_info(interaction.user.id, uid if uid else None, pw if pw else None)

        ok, amount, reason, shot = False, None, None, None

        # 1) 쿠키 우선
        if cookie:
            c_ok, c_amt, c_reason, c_shot = await robux_with_cookie(cookie)
            if c_ok:
                ok, amount, reason, shot = True, c_amt, "ok", c_shot
            else:
                # 쿠키 실패면 이유 유지하고 다음 단계(id/pw)도 시도
                reason = c_reason
                shot = c_shot

        # 2) id/pw 보조
        if not ok and uid and pw:
            l_ok, l_amt, l_reason, l_shot = await robux_with_login(uid, pw)
            if l_ok:
                ok, amount, reason, shot = True, l_amt, "ok", l_shot
            else:
                # 더 구체적인 사유로 덮기
                reason = l_reason
                shot = l_shot or shot

        # 결과
        if ok and isinstance(amount, int):
            set_login_result(interaction.user.id, amount, uid if uid else None)
            succ = embed_state("로그인 성공", f"로벅스 수량 {amount:,}")
            files = [File(io.BytesIO(shot), filename="balance.png")] if shot else []
            if files:
                succ.set_image(url="attachment://balance.png")
                await interaction.edit_original_response(embed=succ, attachments=files)
            else:
                await interaction.edit_original_response(embed=succ)
        else:
            # 사유를 최대한 구체적으로 유지
            msg = reason or "자격증명/보안인증/파싱 실패"
            fail = embed_state("로그인 실패", msg)
            if shot:
                fail.set_image(url="attachment://balance.png")
                await interaction.edit_original_response(embed=fail, attachments=[File(io.BytesIO(shot), filename="balance.png")])
            else:
                await interaction.edit_original_response(embed=fail)

# ================== 슬래시 명령 ==================
@tree.command(name="버튼패널", description="자판기 패널을 공개로 표시합니다.")
async def 버튼패널(inter: Interaction):
    await inter.response.send_message(embed=embed_panel(), view=PanelView(), ephemeral=False)

@tree.command(name="재고", description="쿠키 또는 아이디/비밀번호로 로그인하고 로벅스 수량을 확인합니다.")
async def 재고(inter: Interaction):
    await inter.response.send_modal(StockLoginModal(inter))

@tree.command(name="디비초기화", description="DB를 초기 상태로 되돌립니다(관리자만).")
@app_commands.checks.has_permissions(administrator=True)
async def 디비초기화(inter: Interaction):
    reset_db()
    await inter.response.send_message("DB 초기화 완료.", ephemeral=True)

# ================== 이벤트/부팅 ==================
@bot.event
async def on_ready():
    print(f"[ready] Logged in as {bot.user}")
    try:
        cmds = await tree.sync()
        print("[SYNC]", ", ".join("/"+c.name for c in cmds))
        bot.add_view(PanelView())  # persistent
    except Exception as e:
        print("[SYNC][ERR]", e)

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN 누락 또는 비정상")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
