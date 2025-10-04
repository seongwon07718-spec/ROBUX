import os
import json
import time
import re
import asyncio
from typing import Dict, Any, List, Optional, Tuple

import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from dotenv import load_dotenv

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# ===== ENV =====
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ===== BOT =====
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ===== DB(JSON) =====
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
            "wallet": 0,
            "total": 0,
            "count": 0,
            "recent": [],
            "roblox": {
                "cookie": None,
                "username": None,
                "password": None,
                "last_robux": 0,
                "last_username": None
            }
        }
        db["users"][str(uid)] = u
        _save_db(db)
    return u

def get_user_stats(uid: int) -> Dict[str, Any]:
    return _ensure_user(uid)

def set_login_info(uid: int, cookie: Optional[str], username: Optional[str], password: Optional[str]):
    db = _load_db()
    u = _ensure_user(uid)
    r = u.get("roblox", {})
    if cookie: r["cookie"] = cookie
    if username is not None: r["username"] = username
    if password is not None: r["password"] = password
    u["roblox"] = r
    db["users"][str(uid)] = u
    _save_db(db)

def set_login_result(uid: int, robux: int, username_hint: Optional[str]):
    db = _load_db()
    u = _ensure_user(uid)
    r = u.get("roblox", {})
    r["last_robux"] = int(robux)
    if username_hint:
        r["last_username"] = username_hint
    u["roblox"] = r
    db["users"][str(uid)] = u
    _save_db(db)

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

# ===== Roblox 파싱 =====
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
NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

async def launch_browser(p):
    args = ["--disable-dev-shm-usage","--no-sandbox","--disable-gpu","--disable-setuid-sandbox","--no-zygote"]
    try:
        return await p.chromium.launch(headless=True, args=args)
    except Exception:
        try:
            return await p.chromium.launch(headless=False, args=args)
        except Exception:
            return None

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
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        return True
    except Exception:
        return False

async def _wait_nav_ready(page: Page):
    for sel in BADGE_SELECTORS:
        try:
            await page.wait_for_selector(sel, timeout=25000)
            return
        except Exception:
            continue
    await asyncio.sleep(1.2)

def _to_int(txt: str) -> Optional[int]:
    m = NUM_RE.search(txt or "")
    if not m: return None
    try:
        return int(re.sub(r"[,\.\s]", "", m.group(1)))
    except Exception:
        return None

async def parse_home_badge(page: Page) -> Optional[int]:
    # 경로 A: 홈 상단 뱃지
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
    # 폴백: html 스캔
    try:
        html = await page.content()
        nums = []
        for kw in ["Robux","로벅스"]:
            for m in re.finditer(kw, html, flags=re.IGNORECASE):
                s = max(0, m.start()-100); e = min(len(html), m.end()+100)
                chunk = html[s:e]
                for mm in re.finditer(NUM_RE, chunk):
                    v = _to_int(mm.group(0))
                    if isinstance(v, int) and 0 <= v <= 100_000_000:
                        nums.append(v)
        if nums: return min(nums)
    except Exception:
        pass
    return None

async def parse_transactions_balance(page: Page) -> Optional[int]:
    # 경로 B: 거래 페이지 “내 거래”에서 “내 잔액: [아이콘] 숫자” 추출
    # 대기: “내 거래” 또는 “My Transactions” 타이틀 영역
    try:
        await page.wait_for_selector("text=내 거래, text=My Transactions", timeout=25000)
    except Exception:
        await asyncio.sleep(1.0)
    # 1) “내 잔액” 텍스트 직접 찾기
    try:
        # 한국어/영문 모두 커버
        el = await page.query_selector("text=내 잔액, text=My Balance")
        if el:
            parent = await el.evaluate_handle("e => e.parentElement || e")
            txt = await (await parent.get_property("innerText")).json_value()
            v = _to_int(txt or "")
            if isinstance(v, int) and 0 <= v <= 100_000_000:
                return v
    except Exception:
        pass
    # 2) 아이콘 근처 숫자(로벅스 심볼) 주변에서 추출
    try:
        html = await page.content()
        # '내 잔액' 블록 주변 150자 윈도우
        chunks = []
        for kw in ["내 잔액", "My Balance", "balance"]:
            for m in re.finditer(kw, html, flags=re.IGNORECASE):
                s = max(0, m.start()-150); e = min(len(html), m.end()+150)
                chunks.append(html[s:e])
        nums = []
        for chunk in chunks:
            for mm in re.finditer(NUM_RE, chunk):
                v = _to_int(mm.group(0))
                if isinstance(v, int) and 0 <= v <= 100_000_000:
                    nums.append(v)
        if nums:
            # 보통 잔액은 근처 단일 수치이므로 최소값 반환
            return min(nums)
    except Exception:
        pass
    return None

async def robux_with_cookie(cookie: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    # return ok, robux, username_hint, source
    try:
        async with async_playwright() as p:
            browser = await launch_browser(p)
            if not browser: return False, None, None, None
            ctx = await new_context(browser)
            if not ctx:
                await browser.close(); return False, None, None, None
            await ctx.add_cookies([{
                "name":".ROBLOSECURITY","value":cookie,"domain":".roblox.com","path":"/","httpOnly":True,"secure":True,"sameSite":"Lax"
            }])
            page = await ctx.new_page()

            # 경로 A 시도(홈)
            if await _goto(page, ROBLOX_HOME_URLS[0]) or await _goto(page, ROBLOX_HOME_URLS[1]):
                await _wait_nav_ready(page)
                v = await parse_home_badge(page)
                uname = None
                try:
                    t = await page.title()
                    if t:
                        m = re.search(r"[A-Za-z0-9_]{3,20}", t); 
                        if m: uname = m.group(0)
                except Exception:
                    pass
                if isinstance(v, int):
                    await browser.close()
                    return True, v, uname, "home"

            # 경로 B 시도(거래)
            if await _goto(page, ROBLOX_TX_URL):
                v2 = await parse_transactions_balance(page)
                uname = None
                try:
                    h1 = await page.query_selector("h1,h2")
                    if h1:
                        ttl = (await h1.inner_text() or "").strip()
                        m = re.search(r"[A-Za-z0-9_]{3,20}", ttl)
                        if m: uname = m.group(0)
                except Exception:
                    pass
                await browser.close()
                if isinstance(v2, int):
                    return True, v2, uname, "transactions"

            await browser.close()
            return False, None, None, None
    except Exception:
        return False, None, None, None

async def robux_with_login(username: str, password: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str], Optional[str]]:
    # return ok, robux, cookie_out, username_hint, source
    try:
        async with async_playwright() as p:
            browser = await launch_browser(p)
            if not browser: return False, None, None, None, None
            ctx = await new_context(browser)
            if not ctx:
                await browser.close(); return False, None, None, None, None
            page = await ctx.new_page()
            # 로그인
            if not (await _goto(page, ROBLOX_LOGIN_URLS[0]) or await _goto(page, ROBLOX_LOGIN_URLS[1])):
                await browser.close(); return False, None, None, "로그인 페이지 이동 실패", None
            user_sel = "input[name='username'], input#login-username, input[type='text']"
            pass_sel = "input[name='password'], input#login-password, input[type='password']"
            try:
                await page.wait_for_selector(user_sel, timeout=25000); await page.fill(user_sel, username)
                await page.wait_for_selector(pass_sel, timeout=25000); await page.fill(pass_sel, password)
                await page.click("button[type='submit'], button:has-text('로그인'), button:has-text('Log In')")
            except Exception:
                await browser.close(); return False, None, None, "로그인 입력/전송 실패", None
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=25000)
            except Exception:
                pass

            # 경로 A(홈) → 실패 시 경로 B(거래)
            v, src = None, None
            if await _goto(page, ROBLOX_HOME_URLS[0]) or await _goto(page, ROBLOX_HOME_URLS[1]):
                await _wait_nav_ready(page)
                v = await parse_home_badge(page)
                src = "home"
            if not isinstance(v, int):
                if await _goto(page, ROBLOX_TX_URL):
                    v = await parse_transactions_balance(page)
                    src = "transactions"

            # 쿠키/유저명
            cookie_out, uname = None, None
            try:
                for c in await ctx.cookies():
                    if c.get("name") == ".ROBLOSECURITY":
                        cookie_out = c.get("value"); break
                t = await page.title()
                if t:
                    m = re.search(r"[A-Za-z0-9_]{3,20}", t)
                    if m: uname = m.group(0)
            except Exception:
                pass

            await browser.close()
            if isinstance(v, int):
                return True, v, cookie_out, uname, src
            return False, None, None, "로벅스 파싱 실패", src
    except Exception as e:
        return False, None, None, f"예외 발생: {e}", None

# ===== 색상 =====
BLACK = discord.Colour.dark_grey()
GREEN = discord.Colour.green()
RED   = discord.Colour.red()

# ===== 임베드 =====
def embed_panel() -> Embed:
    return Embed(
        title="자동 로벅스 자판기",
        description="아래 버튼을 눌려 이용해주세요!",
        colour=BLACK
    )

def embed_notice() -> Embed:
    return Embed(title="공지", description="<#1419230737244229653> 필독 부탁드립니다", colour=BLACK)

def embed_myinfo(user: discord.User | discord.Member, stats: Dict[str, Any]) -> Embed:
    emb = Embed(title=f"{getattr(user,'display_name',getattr(user,'name','유저'))}님 정보", colour=BLACK)
    wallet = int(stats.get("wallet", 0))
    total  = int(stats.get("total", 0))
    count  = int(stats.get("count", 0))
    emb.description = "\n".join([
        f"### 보유 금액 : {wallet:,}원",
        f"### 누적 금액 : {total:,}원",
        f"### 거래 횟수 : {count:,}번",
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
        d = (e.get("desc","") or "").lower()
        t = (e.get("type","") or "").lower()
        if t in ("buy","order","trade") or any(k in d for k in ["구매","거래","주문","buy","order","trade"]):
            filtered.append(e)
    options = []
    if filtered:
        for i, e in enumerate(filtered):
            label = f"{e.get('desc','거래')} / {int(e.get('amount',0)):,}원"
            options.append(discord.SelectOption(label=label[:100], value=str(i)))
    else:
        options = [discord.SelectOption(label="거래 내역 없음", value="none", default=True)]
    class TxSelect(discord.ui.Select):
        def __init__(self):
            super().__init__(placeholder="최근 거래내역 보기", min_values=1, max_values=1, options=options)
        async def callback(self, interaction: Interaction):
            try:
                await interaction.response.defer()
            except Exception:
                pass
    v = discord.ui.View(timeout=None)
    v.add_item(TxSelect())
    return v

# ===== 버튼 뷰 =====
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="공지",   custom_id="panel_notice", row=0))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="충전",   custom_id="panel_charge", row=0))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="내 정보", custom_id="panel_info",   row=1))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="구매",   custom_id="panel_buy",    row=1))
    async def interaction_check(self, interaction: Interaction) -> bool:
        try:
            await interaction.response.defer()
        except Exception:
            pass
        cid = (interaction.data or {}).get("custom_id")
        uid = interaction.user.id
        if cid == "panel_notice":
            try:
                await interaction.followup.send(embed=embed_notice(), ephemeral=True)
            except Exception:
                pass
        elif cid == "panel_info":
            stats = get_user_stats(uid)
            emb = embed_myinfo(interaction.user, stats)
            view = make_tx_select(stats)
            try:
                await interaction.followup.send(embed=emb, view=view, ephemeral=True)
            except Exception:
                pass
        elif cid == "panel_charge":
            add_tx(uid, 1000, "충전", "charge")
            stats = get_user_stats(uid)
            emb = embed_myinfo(interaction.user, stats)
            view = make_tx_select(stats)
            try:
                await interaction.followup.send(content="충전 완료!", embed=emb, view=view, ephemeral=True)
            except Exception:
                pass
        elif cid == "panel_buy":
            add_tx(uid, -500, "구매", "buy")
            stats = get_user_stats(uid)
            emb = embed_myinfo(interaction.user, stats)
            view = make_tx_select(stats)
            try:
                await interaction.followup.send(content="구매 처리 완료!", embed=emb, view=view, ephemeral=True)
            except Exception:
                pass
        return False

# ===== /버튼패널 =====
@tree.command(name="버튼패널", description="자동 로벅스 자판기 패널을 공개로 표시합니다.")
async def 버튼패널(inter: Interaction):
    await inter.response.send_message(embed=embed_panel(), view=PanelView(), ephemeral=False)

# ===== /재고 (모달) =====
class StockLoginModal(discord.ui.Modal, title="로그인"):
    cookie = discord.ui.TextInput(label="cookie(.ROBLOSECURITY)", required=False, style=discord.TextStyle.short, max_length=4000, placeholder="쿠키값(선택)")
    uid    = discord.ui.TextInput(label="아이디", required=False, style=discord.TextStyle.short, max_length=100)
    pw     = discord.ui.TextInput(label="비밀번호", required=False, style=discord.TextStyle.short, max_length=100)

    def __init__(self, inter: Interaction):
        super().__init__(timeout=None)
        self.inter = inter

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True, thinking=False)
        user_id = interaction.user.id
        cookie_val = str(self.cookie.value or "").strip()
        id_val    = str(self.uid.value or "").strip()
        pw_val    = str(self.pw.value or "").strip()

        if not cookie_val and not (id_val and pw_val):
            emb = Embed(title="로그인 실패", description="쿠키나 아이디/비밀번호 중 하나 이상을 입력해줘.", colour=RED)
            await interaction.followup.send(embed=emb, ephemeral=True)
            return

        # 입력된 자격 저장
        if cookie_val: set_login_info(user_id, cookie_val, None, None)
        if id_val or pw_val: set_login_info(user_id, None, id_val if id_val else None, pw_val if pw_val else None)

        # 파싱 시도(2중 경로)
        ok, robux, uname, source, fail_reason = False, None, None, None, None
        if cookie_val:
            c_ok, c_robux, c_uname, c_src = await robux_with_cookie(cookie_val)
            if c_ok:
                ok, robux, uname, source = True, c_robux, c_uname, c_src
        if not ok and id_val and pw_val:
            l_ok, l_robux, c_out, u_hint, l_src = await robux_with_login(id_val, pw_val)
            if l_ok:
                ok, robux, uname, source = True, l_robux, u_hint, l_src
                if c_out: set_login_info(user_id, c_out, None, None)
            else:
                fail_reason = u_hint if isinstance(u_hint, str) else "로그인 실패(2FA/장치인증/자격 오류)"

        if ok and isinstance(robux, int):
            set_login_result(user_id, robux, uname)
            name_txt = uname or (id_val if id_val else "알 수 없음")
            desc = f"{name_txt}계정에 로그인 성공 되었습니다\n로벅스 수량 {robux:,}\n쿠키값 저장 완료되었습니다"
            emb = Embed(title="로그인 성공", description=desc, colour=GREEN)
            await interaction.followup.send(embed=emb, ephemeral=True)
        else:
            reason = fail_reason or "쿠키/계정 정보가 유효하지 않거나 로벅스 파싱 실패"
            emb = Embed(title="로그인 실패", description=reason, colour=RED)
            await interaction.followup.send(embed=emb, ephemeral=True)

@tree.command(name="재고", description="쿠키 또는 계정으로 로그인하고 로벅스 수량을 확인합니다.")
async def 재고(inter: Interaction):
    await inter.response.send_modal(StockLoginModal(inter))

# ===== on_ready =====
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        await tree.sync()  # 전역 등록 → 여러 길드에서 사용 가능
        print("[SYNC] global commands synced (/버튼패널, /재고)")
    except Exception as e:
        print("[SYNC][ERR]", e)

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN 비정상")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
