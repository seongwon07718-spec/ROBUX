import os, io, json, re, asyncio, time, statistics
from typing import Dict, Any, Optional, Tuple, List

import discord
from discord import app_commands, Interaction, Embed, File
from discord.ext import commands
from dotenv import load_dotenv

# Playwright
PLAYWRIGHT_OK = True
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PwTimeout
except Exception:
    PLAYWRIGHT_OK = False

# ===== 기본 =====
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ===== DB =====
DATA_PATH = "data.json"
INIT_DATA = {"guilds": {}}

def db_load() -> Dict[str, Any]:
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(INIT_DATA, f, ensure_ascii=False, indent=2)
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            data = {"guilds": {}}
    if "guilds" not in data or not isinstance(data["guilds"], dict):
        data["guilds"] = {}
    return data

def db_save(db: Dict[str, Any]):
    tmp = DATA_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_PATH)

def gslot(gid: int) -> Dict[str, Any]:
    db = db_load()
    s = db["guilds"].get(str(gid))
    if not s:
        s = {
            "stock": {"robux": 0, "totalSold": 0, "pricePer": 0, "lastMsg": {"channelId": 0, "messageId": 0}},
            "sessions": {}
        }
        db["guilds"][str(gid)] = s
        db_save(db)
    return s

def update_gslot(gid: int, gs: Dict[str, Any]):
    db = db_load()
    db["guilds"][str(gid)] = gs
    db_save(db)

def set_session(gid: int, uid: int, cookie: Optional[str], username: Optional[str], password: Optional[str]):
    gs = gslot(gid)
    sess = gs["sessions"].get(str(uid), {"cookie": None, "username": None, "password": None, "lastRobux": 0})
    if cookie is not None: sess["cookie"] = cookie
    if username is not None: sess["username"] = username
    if password is not None: sess["password"] = password
    gs["sessions"][str(uid)] = sess
    update_gslot(gid, gs)

def set_last_robux(gid: int, uid: int, amount: int):
    gs = gslot(gid)
    sess = gs["sessions"].get(str(uid), {"cookie": None, "username": None, "password": None, "lastRobux": 0})
    sess["lastRobux"] = int(amount)
    gs["sessions"][str(uid)] = sess
    update_gslot(gid, gs)

def set_stock_values(gid: int, robux: Optional[int] = None, totalSold: Optional[int] = None, pricePer: Optional[int] = None):
    gs = gslot(gid)
    if robux is not None: gs["stock"]["robux"] = max(0, int(robux))
    if totalSold is not None: gs["stock"]["totalSold"] = max(0, int(totalSold))
    if pricePer is not None: gs["stock"]["pricePer"] = max(0, int(pricePer))
    update_gslot(gid, gs)

def set_last_message(gid: int, channelId: int, messageId: int):
    gs = gslot(gid)
    gs["stock"]["lastMsg"] = {"channelId": int(channelId), "messageId": int(messageId)}
    update_gslot(gid, gs)

# ===== 색/이모지/임베드 =====
def color_hex(h: str) -> discord.Colour:
    return discord.Colour(int(h.lower().replace("#", ""), 16))

COLOR_BLACK = color_hex("000000")
COLOR_PINK  = color_hex("ff5dd6")

EMO_REALTIME = "<a:upuoipipi:1423892277373304862>"
EMO_THUMBS  = "<a:thumbsuppp:1423892279612936294>"
EMO_SAK     = "<a:sakfnmasfagfamg:1423892278677602435>"

FOOTER_IMAGE = "https://cdn.discordapp.com/attachments/1420389790649421877/1424077172435325091/IMG_2038.png?ex=68e2a2b7&is=68e15137&hm=712b0f434f2267c261dc260fd22a7a163d158b7c2f43fa618642abd80b17058c&"

def embed_panel() -> Embed:
    return Embed(title="자동 로벅스 자판기", description="아래 버튼을 눌러 이용해줘!", colour=COLOR_PINK)

def embed_notice() -> Embed:
    return Embed(title="공지", description="<#1419230737244229653> 필독 부탁!", colour=COLOR_BLACK)

def build_info_embed(user: discord.User | discord.Member, gid: int) -> Embed:
    wallet = 0; total = 0; count = 0
    e = Embed(title=f"{getattr(user,'display_name',user.name)}님 정보", colour=COLOR_BLACK)
    e.description = "\n".join([
        f"보유 금액 : `{wallet}`원",
        f"누적 금액 : `{total}`원",
        f"거래 횟수 : `{count}`번",
    ])
    try: e.set_thumbnail(url=user.display_avatar.url)
    except Exception: pass
    return e

def build_stock_embed(gid: int) -> Embed:
    gs = gslot(gid)
    robux = int(gs["stock"].get("robux", 0))
    total = int(gs["stock"].get("totalSold", 0))
    price = int(gs["stock"].get("pricePer", 0))
    desc = "\n".join([
        f"## {EMO_REALTIME}실시간 로벅스",
        f"### {EMO_THUMBS}로벅스 재고",
        f"### {EMO_SAK}`{robux}`로벅스",
        f"### {EMO_THUMBS}로벅스 가격",
        f"### {EMO_SAK}1당 `{price}`로벅스",
        f"### {EMO_THUMBS}총 판매량",
        f"### {EMO_SAK}`{total}`로벅스",
    ])
    e = Embed(description=desc, colour=COLOR_PINK)  # 제목 비움
    e.set_image(url=FOOTER_IMAGE)
    return e

# ===== Roblox 로그인/파싱(초정밀 5분 + 오류 미러링) =====
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

def normalize_cookie(raw: str) -> Optional[str]:
    if not raw: return None
    s = raw.strip()
    m1 = re.search(r"\.ROBLOSECURITY\s*=\s*([^;]+)", s, re.IGNORECASE)
    if m1: return m1.group(1).strip()
    m2 = re.search(r"(\_\|WARNING:.+?\|\_.+)", s, re.IGNORECASE)
    if m2: return m2.group(1).strip()
    if s.startswith("_|WARNING:"): return s
    if len(s) >= 100: return s
    return None

NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")
BALANCE_LABELS = ["내 잔액", "My Balance", "Balance"]
BADGE_SELECTORS = [
    "[data-testid*='nav-robux']",
    "a[aria-label*='Robux']",
    "a[aria-label*='로벅스']",
    "span[title*='Robux']",
    "span[title*='로벅스']",
]
SECURITY_MAP = {
    "two_factor": ["two-step", "2단계", "authenticator", "otp", "2-step"],
    "device_verification": ["verify your device", "장치 인증", "새 기기", "was this you", "device verification"],
    "captcha": ["captcha", "hcaptcha", "recaptcha", "i’m not a robot", "i am not a robot"],
    "rate_block": ["too many requests", "access denied", "forbidden", "403"],
}
CREDENTIAL_KEYS = ["incorrect", "wrong password", "invalid", "비밀번호", "아이디", "로그인 실패", "일치하지 않", "다시 시도", "재시도", "blocked", "suspended"]

def _to_int(txt: str) -> Optional[int]:
    if not txt: return None
    m = NUM_RE.search(txt)
    if not m: return None
    try: return int(re.sub(r"[,\.\s]", "", m.group(1)))
    except Exception: return None

async def _launch(p):
    args = ["--disable-dev-shm-usage","--no-sandbox","--disable-gpu","--disable-setuid-sandbox","--no-zygote"]
    try: return await p.chromium.launch(headless=True, args=args)
    except Exception: return None

async def _ctx(browser: Browser):
    try:
        return await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
            viewport={"width": 1366, "height": 864}, locale="ko-KR", java_script_enabled=True
        )
    except Exception: return None

async def _goto(page: Page, url: str, timeout=50000) -> bool:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        return True
    except Exception:
        return False

async def _shot(page: Page) -> Optional[bytes]:
    try: return await page.screenshot(type="png", full_page=False)
    except Exception: return None

def _cred_error(html: str) -> bool:
    low = html.lower()
    return any(kw in low for kw in CREDENTIAL_KEYS)

def _detect_issue(html: str) -> Optional[str]:
    low = html.lower()
    for label, kws in SECURITY_MAP.items():
        for kw in kws:
            if kw in low:
                if label == "two_factor": return "2단계 인증(MFA) 필요"
                if label == "device_verification": return "디바이스 인증(새 기기 확인) 필요"
                if label == "captcha": return "캡차(hCaptcha/reCAPTCHA) 발생"
                if label == "rate_block": return "네트워크/리전 차단 또는 요청 과다(Too Many Requests)"
    return None

async def extract_visible_errors(page: Page) -> str:
    selectors = [
        "[role='alert']",
        ".alert-content, .alert-danger, .alert-warning",
        "[data-testid*='error'], [data-testid*='message']",
        ".validation-message, .message, .text-error, .input-validation-error",
        "div:has-text('Two-step'), div:has-text('2단계'), div:has-text('Verify'), div:has-text('captcha')",
        "section:has-text('로그인'), section:has-text('오류')"
    ]
    texts = []
    for sel in selectors:
        try:
            els = await page.query_selector_all(sel)
            for el in els:
                t = (await el.inner_text() or "").strip()
                t = re.sub(r"\s+", " ", t)
                if t and t not in texts:
                    texts.append(t)
        except:
            continue
    if texts:
        return "\n".join(texts[:5])[:900]
    try:
        title = (await page.title()) or ""
    except:
        title = ""
    try:
        body = await page.inner_text("body")
    except:
        body = ""
    body = re.sub(r"\s+", " ", body).strip() if body else ""
    if body and len(body) > 900:
        body = body[:900] + " …"
    bits = []
    if title: bits.append(f"[페이지 제목] {title}")
    if body: bits.append(body)
    return "\n".join(bits)

async def _parse_tx(page: Page) -> Optional[int]:
    try:
        await page.wait_for_selector("text=내 거래, text=My Transactions", timeout=50000)
    except Exception:
        await asyncio.sleep(1.5)
    for label in BALANCE_LABELS:
        try:
            el = await page.query_selector(f"text={label}")
            if not el: continue
            container = await el.evaluate_handle("e => e.parentElement || e")
            txt = await (await container.get_property("innerText")).json_value()
            v = _to_int(txt or "")
            if isinstance(v, int) and 0 <= v <= 100_000_000: return v
        except Exception: continue
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
        if nums:
            return int(statistics.median(nums))
    except Exception:
        pass
    return None

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

async def read_balance_samples_tx(page, samples=3, delay=1.1):
    vals = []
    for _ in range(samples):
        v = await _parse_tx(page)
        if isinstance(v, int): vals.append(v)
        await asyncio.sleep(delay)
    return vals

async def read_balance_samples_home(page, samples=3, delay=1.0):
    vals = []
    for _ in range(samples):
        v = await _parse_home(page)
        if isinstance(v, int): vals.append(v)
        await asyncio.sleep(delay)
    return vals

def stable_value(values: List[int]) -> Optional[int]:
    if not values: return None
    if len(values) == 1: return values[0]
    med = int(statistics.median(values))
    tol = max(10, int(med * 0.02))
    if all(abs(v - med) <= tol for v in values):
        return med
    try:
        mode = statistics.mode(values)
        return mode
    except:
        return None

async def parse_balance_ultra_precise(page: Page, overall_deadline_s=300) -> Optional[int]:
    start = time.time()
    rounds = 0
    while time.time() - start < overall_deadline_s and rounds < 3:
        rounds += 1
        tx_stable = None
        if await _goto(page, ROBLOX_TX_URL, timeout=50000):
            await asyncio.sleep(3.0)
            tx_vals = await read_balance_samples_tx(page, samples=3, delay=1.1)
            tx_stable = stable_value(tx_vals)

        home_stable = None
        for hu in ROBLOX_HOME_URLS:
            if await _goto(page, hu, timeout=48000):
                await asyncio.sleep(2.0)
                home_vals = await read_balance_samples_home(page, samples=3, delay=1.0)
                home_stable = stable_value(home_vals)
                break

        if isinstance(tx_stable, int) and isinstance(home_stable, int):
            tol = max(10, int(max(tx_stable, home_stable) * 0.02))
            if abs(tx_stable - home_stable) <= tol:
                return int(statistics.median([tx_stable, home_stable]))
            # 거래 재시도
            if await _goto(page, ROBLOX_TX_URL, timeout=48000):
                await asyncio.sleep(2.0)
                tx_vals2 = await read_balance_samples_tx(page, samples=3, delay=0.9)
                comb = [tx_stable, home_stable] + [v for v in tx_vals2 if isinstance(v, int)]
                comb = [v for v in comb if isinstance(v, int)]
                st = stable_value(comb)
                if isinstance(st, int): return st
        elif isinstance(tx_stable, int):
            return tx_stable
        elif isinstance(home_stable, int):
            return home_stable

        await asyncio.sleep(1.5)
    return None

async def robux_with_cookie(raw_cookie: str) -> Tuple[bool, Optional[int], str, Optional[bytes]]:
    if not PLAYWRIGHT_OK: return False, None, "Playwright 미설치", None
    cookie = normalize_cookie(raw_cookie)
    if not cookie: return False, None, "쿠키 형식 오류(.ROBLOSECURITY 또는 _|WARNING:…|_ 필요)", None
    try:
        start = time.time()
        async with async_playwright() as p:
            browser = await _launch(p)
            if not browser: return False, None, "브라우저 오류", None
            ctx = await _ctx(browser)
            if not ctx: await browser.close(); return False, None, "컨텍스트 오류", None
            await ctx.add_cookies([{"name":".ROBLOSECURITY","value":cookie,"domain":".roblox.com","path":"/","httpOnly":True,"secure":True,"sameSite":"Lax"}])
            page = await ctx.new_page()

            if await _goto(page, ROBLOX_TX_URL, timeout=50000):
                await asyncio.sleep(1.5)
                html = await page.content()
                iss = _detect_issue(html)
                if iss:
                    shot = await _shot(page)
                    err_txt = await extract_visible_errors(page)
                    desc = iss if not err_txt else f"{iss}\n\n[화면 메시지]\n{err_txt}"
                    await page.close(); await browser.close()
                    return False, None, desc, shot

            v_final = await parse_balance_ultra_precise(page, overall_deadline_s=300)
            shot = await _shot(page)
            await page.close(); await browser.close()

            if isinstance(v_final, int): return True, v_final, "ok", shot
            err_txt = await extract_visible_errors(page)
            reason = "타임아웃(5분 초과)" if (time.time() - start > 300) else "로벅스 파싱 실패"
            desc = reason if not err_txt else f"{reason}\n\n[화면 메시지]\n{err_txt}"
            return False, None, desc, shot
    except PwTimeout:
        return False, None, "응답 지연", None
    except Exception:
        return False, None, "예외", None

async def robux_with_login(username: str, password: str) -> Tuple[bool, Optional[int], str, Optional[bytes]]:
    if not PLAYWRIGHT_OK: return False, None, "Playwright 미설치", None
    try:
        start = time.time()
        async with async_playwright() as p:
            browser = await _launch(p)
            if not browser: return False, None, "브라우저 오류", None
            ctx = await _ctx(browser)
            if not ctx: await browser.close(); return False, None, "컨텍스트 오류", None
            page = await ctx.new_page()

            moved = False
            for url in ROBLOX_LOGIN_URLS:
                if await _goto(page, url, timeout=50000):
                    moved = True; break
            if not moved:
                await browser.close(); return False, None, "로그인 페이지 이동 실패", None

            id_ok = False
            for sel in ["input#login-username", "input[name='username']", "input[type='text']"]:
                try: await page.fill(sel, username); id_ok = True; break
                except Exception: continue
            if not id_ok:
                await browser.close(); return False, None, "아이디 입력 실패", None

            pw_ok = False
            for sel in ["input#login-password", "input[name='password']", "input[type='password']"]:
                try: await page.fill(sel, password); pw_ok = True; break
                except Exception: continue
            if not pw_ok:
                await browser.close(); return False, None, "비밀번호 입력 실패", None

            clicked = False
            for sel in ["button#login-button", "button[type='submit']", "button:has-text('로그인')", "button:has-text('Log In')"]:
                try:
                    btn = await page.query_selector(sel)
                    if btn: await btn.click(); clicked = True; break
                except Exception: continue
            if not clicked:
                await browser.close(); return False, None, "로그인 버튼 클릭 실패", None

            await asyncio.sleep(2.5)
            html = await page.content()
            iss = _detect_issue(html)
            if iss:
                shot = await _shot(page)
                err_txt = await extract_visible_errors(page)
                desc = iss if not err_txt else f"{iss}\n\n[화면 메시지]\n{err_txt}"
                await browser.close()
                return False, None, desc, shot
            if _cred_error(html):
                shot = await _shot(page)
                err_txt = await extract_visible_errors(page)
                desc = "자격증명 오류(아이디/비밀번호 불일치)"
                desc = desc if not err_txt else f"{desc}\n\n[화면 메시지]\n{err_txt}"
                await browser.close()
                return False, None, desc, shot

            v_final = await parse_balance_ultra_precise(page, overall_deadline_s=300)
            shot = await _shot(page)
            await page.close(); await browser.close()

            if isinstance(v_final, int): return True, v_final, "ok", shot
            err_txt = await extract_visible_errors(page)
            reason = "타임아웃(5분 초과)" if (time.time() - start > 300) else "로벅스 파싱 실패"
            desc = reason if not err_txt else f"{reason}\n\n[화면 메시지]\n{err_txt}"
            return False, None, desc, shot
    except PwTimeout:
        return False, None, "응답 지연", None
    except Exception:
        return False, None, "예외", None

# ===== 패널 뷰 =====
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="공지", style=discord.ButtonStyle.secondary, custom_id="panel_notice", row=0)
    async def notice_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=embed_notice(), ephemeral=True)
    @discord.ui.button(label="정보", style=discord.ButtonStyle.secondary, custom_id="panel_info", row=0)
    async def info_button(self, interaction: Interaction, button: discord.ui.Button):
        e = build_info_embed(interaction.user, interaction.guild.id)
        await interaction.response.send_message(embed=e, ephemeral=True)
    @discord.ui.button(label="충전", style=discord.ButtonStyle.secondary, custom_id="panel_charge", row=1)
    async def charge_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=Embed(title="충전", description="준비 중이야.", colour=COLOR_BLACK), ephemeral=True)
    @discord.ui.button(label="구매", style=discord.ButtonStyle.secondary, custom_id="panel_buy", row=1)
    async def buy_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=Embed(title="구매", description="준비 중이야.", colour=COLOR_BLACK), ephemeral=True)

# ===== 모달(/재고추가) =====
class StockModal(discord.ui.Modal, title="세션/로그인 추가(초정밀 파싱 최대 5분)"):
    cookie_input = discord.ui.TextInput(label="cookie(.ROBLOSECURITY 또는 _|WARNING:…|_)", required=False, max_length=4000)
    id_input = discord.ui.TextInput(label="아이디", required=False, max_length=100)
    pw_input = discord.ui.TextInput(label="비밀번호", required=False, max_length=100)
    async def on_submit(self, interaction: Interaction):
        gid = interaction.guild.id
        await interaction.response.send_message(embed=Embed(title="", description="정확하게 확인 중(최대 5분)…", colour=COLOR_BLACK), ephemeral=True)

        raw_cookie = (self.cookie_input.value or "").strip()
        uid = (self.id_input.value or "").strip()
        pw = (self.pw_input.value or "").strip()
        if raw_cookie:
            norm = normalize_cookie(raw_cookie)
            set_session(gid, interaction.user.id, norm if norm else raw_cookie, None, None)
        if uid or pw:
            set_session(gid, interaction.user.id, None, uid if uid else None, pw if pw else None)

        ok, amount, reason, shot = False, None, None, None
        if raw_cookie:
            c_ok, c_amt, c_reason, c_shot = await robux_with_cookie(raw_cookie)
            if c_ok: ok, amount, reason, shot = True, c_amt, "ok", c_shot
            else: reason, shot = c_reason, c_shot

        if not ok and uid and pw:
            l_ok, l_amt, l_reason, l_shot = await robux_with_login(uid, pw)
            if l_ok: ok, amount, reason, shot = True, l_amt, "ok", l_shot
            else: reason, shot = l_reason, l_shot or shot

        if ok and isinstance(amount, int):
            set_last_robux(gid, interaction.user.id, amount)
            set_stock_values(gid, robux=amount)
            await try_update_stock_message(interaction.guild, gid)
            e = Embed(title="", description=f"로벅스 수량 {amount:,} (확정)", colour=COLOR_BLACK)
            if shot:
                e.set_image(url="attachment://robux.png")
                await interaction.edit_original_response(embed=e, attachments=[File(io.BytesIO(shot), filename="robux.png")])
            else:
                await interaction.edit_original_response(embed=e)
        else:
            e = Embed(title="로그인/파싱 실패", description=(reason or "파싱 실패"), colour=COLOR_BLACK)
            if shot:
                e.set_image(url="attachment://robux.png")
                await interaction.edit_original_response(embed=e, attachments=[File(io.BytesIO(shot), filename="robux.png")])
            else:
                await interaction.edit_original_response(embed=e)

# ===== /재고표시 갱신 =====
async def try_update_stock_message(guild: discord.Guild, gid: int):
    gs = gslot(gid)
    last = gs["stock"].get("lastMsg", {}) or {}
    ch_id = int(last.get("channelId") or 0)
    msg_id = int(last.get("messageId") or 0)
    if ch_id and msg_id:
        ch = guild.get_channel(ch_id)
        if isinstance(ch, discord.TextChannel):
            try:
                msg = await ch.fetch_message(msg_id)
                await msg.edit(embed=build_stock_embed(gid))
            except Exception:
                pass

# ===== 명령어 =====
@tree.command(name="버튼패널", description="자판기 패널을 공개로 표시합니다.")
async def 버튼패널(inter: Interaction):
    await inter.response.send_message(embed=embed_panel(), view=PanelView(), ephemeral=False)

@tree.command(name="재고표시", description="실시간 로벅스 재고 임베드를 공개로 표시합니다.")
async def 재고표시(inter: Interaction):
    gid = inter.guild.id
    e = build_stock_embed(gid)
    await inter.response.send_message(embed=e, ephemeral=False)
    try:
        sent = await inter.original_response()
        set_last_message(gid, inter.channel.id, sent.id)
    except Exception:
        pass

@tree.command(name="가격설정", description="1당 가격을 설정합니다(관리자).")
@app_commands.describe(일당="1당 가격(정수)")
@app_commands.checks.has_permissions(manage_guild=True)
async def 가격설정(inter: Interaction, 일당: int):
    gid = inter.guild.id
    set_stock_values(gid, pricePer=max(0, int(일당)))
    await try_update_stock_message(inter.guild, gid)
    e = Embed(title="", description="가격설정 완료", colour=COLOR_BLACK)
    await inter.response.send_message(embed=e, ephemeral=True)

@tree.command(name="재고추가", description="쿠키 또는 아이디/비밀번호로 세션을 추가하고 로벅스 수량을 확인합니다.")
async def 재고추가(inter: Interaction):
    await inter.response.send_modal(StockModal())

# ===== 부팅 =====
@bot.event
async def on_ready():
    print(f"[ready] Logged in as {bot.user}")
    try:
        cmds = await tree.sync()
        print("[SYNC]", ", ".join("/"+c.name for c in cmds))
        bot.add_view(PanelView())
    except Exception as e:
        print("[SYNC][ERR]", e)

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN 누락 또는 비정상")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
