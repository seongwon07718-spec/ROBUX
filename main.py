import os, io, json, re, asyncio, time, statistics, pathlib
from typing import Dict, Any, Optional, Tuple, List

import discord
from discord import app_commands, Interaction, Embed, File
from discord.ext import commands
from dotenv import load_dotenv

# Playwright 사용(로그인/파싱)
PLAYWRIGHT_OK = True
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PwTimeout
except Exception:
    PLAYWRIGHT_OK = False

# ============== 기본 ==============
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
HTTP_PROXY = os.getenv("HTTP_PROXY", "").strip() or None
HTTPS_PROXY = os.getenv("HTTPS_PROXY", "").strip() or None

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ============== DB/상태 ==============
DATA_PATH = "data.json"
CTX_SNAPSHOT_DIR = "ctx_snapshots"
pathlib.Path(CTX_SNAPSHOT_DIR).mkdir(parents=True, exist_ok=True)

db_lock = asyncio.Lock()

INIT_DATA = {"guilds": {}, "giftSessions": {}}

def db_load() -> Dict[str, Any]:
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(INIT_DATA, f, ensure_ascii=False, indent=2)
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            data = {"guilds": {}, "giftSessions": {}}
    if "guilds" not in data: data["guilds"] = {}
    if "giftSessions" not in data: data["giftSessions"] = {}
    return data

def db_save(data: Dict[str, Any]):
    tmp = DATA_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_PATH)

def gslot(gid: int) -> Dict[str, Any]:
    data = db_load()
    s = data["guilds"].get(str(gid))
    if not s:
        s = {
            "stock": {"robux": 0, "totalSold": 0, "pricePer": 0, "lastMsg": {"channelId": 0, "messageId": 0}},
            "sessions": {}  # uid -> {cookie, username, password, lastRobux, premium, accountName}
        }
        data["guilds"][str(gid)] = s
        db_save(data)
    return s

def update_gslot(gid: int, gs: Dict[str, Any]):
    data = db_load()
    data["guilds"][str(gid)] = gs
    db_save(data)

def set_session(gid: int, uid: int, cookie: Optional[str], username: Optional[str], password: Optional[str]):
    gs = gslot(gid)
    sess = gs["sessions"].get(str(uid), {"cookie": None, "username": None, "password": None, "lastRobux": 0, "premium": False, "accountName": None})
    if cookie is not None: sess["cookie"] = cookie
    if username is not None: sess["username"] = username
    if password is not None: sess["password"] = password
    gs["sessions"][str(uid)] = sess
    update_gslot(gid, gs)

def set_last_balance(gid: int, uid: int, robux: int, premium: bool, account_name: Optional[str] = None):
    gs = gslot(gid)
    sess = gs["sessions"].get(str(uid), {"cookie": None, "username": None, "password": None, "lastRobux": 0, "premium": False, "accountName": None})
    sess["lastRobux"] = int(robux)
    sess["premium"] = bool(premium)
    if account_name: sess["accountName"] = account_name
    gs["sessions"][str(uid)] = sess
    gs["stock"]["robux"] = max(0, int(robux))
    update_gslot(gid, gs)

def set_price(gid: int, price: int):
    gs = gslot(gid)
    gs["stock"]["pricePer"] = max(0, int(price))
    update_gslot(gid, gs)

def set_last_message(gid: int, channelId: int, messageId: int):
    gs = gslot(gid)
    gs["stock"]["lastMsg"] = {"channelId": int(channelId), "messageId": int(messageId)}
    update_gslot(gid, gs)

async def change_stock(gid: int, delta: int):
    async with db_lock:
        gs = gslot(gid)
        now = int(gs["stock"].get("robux", 0))
        newv = max(0, now + int(delta))
        gs["stock"]["robux"] = newv
        if delta < 0:
            gs["stock"]["totalSold"] = int(gs["stock"].get("totalSold", 0)) + (-delta)
        update_gslot(gid, gs)
        return newv

# giftSessions (파일 DB)
def gift_get(uid: int) -> Dict[str, Any]:
    data = db_load()
    return data["giftSessions"].get(str(uid), {})

def gift_set(uid: int, patch: Dict[str, Any]):
    data = db_load()
    cur = data["giftSessions"].get(str(uid), {})
    cur.update(patch)
    data["giftSessions"][str(uid)] = cur
    db_save(data)

def gift_clear(uid: int):
    data = db_load()
    if str(uid) in data["giftSessions"]:
        del data["giftSessions"][str(uid)]
        db_save(data)

# ============== 임베드 통일 ==============
def color_hex(h: str) -> discord.Colour:
    return discord.Colour(int(h.lower().replace("#", ""), 16))

COLOR_BLACK = color_hex("000000")
COLOR_PINK  = color_hex("ff5dd6")
COLOR_GREEN = discord.Colour.green()
COLOR_RED   = discord.Colour.red()
COLOR_ORANGE= discord.Colour.orange()

def pe(eid: int, name: str = None, animated: bool = False) -> discord.PartialEmoji:
    return discord.PartialEmoji(name=name, id=eid, animated=animated)

BTN_EMO_NOTICE = pe(1424003478275231916, name="emoji_5")
BTN_EMO_CHARGE = pe(1381244136627245066, name="charge")
BTN_EMO_INFO   = pe(1381244138355294300, name="info")
BTN_EMO_BUY    = pe(1381244134680957059, name="category")
EMO_ROBUX_STATIC = pe(1423661718776709303, name="robux")

FOOTER_IMAGE = "https://cdn.discordapp.com/attachments/1420389790649421877/1424077172435325091/IMG_2038.png?ex=68e2a2b7&is=68e15137&hm=712b0f434f2267c261dc260fd22a7a163d158b7c2f43fa618642abd80b17058c&"

def embed_unified(title: Optional[str], desc: str, colour: discord.Colour, image_url: Optional[str] = None) -> Embed:
    e = Embed(title=(title or "")[:256], description=desc, colour=colour)
    if image_url:
        e.set_image(url=image_url)
    return e

def embed_panel() -> Embed:
    return embed_unified("자동 로벅스 자판기", "아래 버튼을 눌러 이용해줘!", COLOR_PINK)

def embed_notice() -> Embed:
    return embed_unified("공지사항", "<#1419230737244229653> 필독 부탁!", COLOR_BLACK)

def build_info_embed(user: discord.User | discord.Member, gid: int) -> Embed:
    wallet = 0; total = 0; count = 0
    e = embed_unified(f"{getattr(user,'display_name',user.name)}님 정보", "\n".join([
        f"보유 금액 : `{wallet}`원",
        f"누적 금액 : `{total}`원",
        f"거래 횟수 : `{count}`번",
    ]), COLOR_BLACK)
    try: e.set_thumbnail(url=user.display_avatar.url)
    except: pass
    return e

def build_stock_embed(gid: int) -> Embed:
    gs = gslot(gid)
    robux = int(gs["stock"].get("robux", 0))
    total = int(gs["stock"].get("totalSold", 0))
    price = int(gs["stock"].get("pricePer", 0))
    desc = "\n".join([
        "## <a:upuoipipi:1423892277373304862>실시간 로벅스",
        "### <a:thumbsuppp:1423892279612936294>로벅스 재고",
        f"### <a:sakfnmasfagfamg:1423892278677602435>`{robux}`로벅스",
        "### <a:thumbsuppp:1423892279612936294>로벅스 가격",
        f"### <a:sakfnmasfagfamg:1423892278677602435>1당 `{price}`로벅스",
        "### <a:thumbsuppp:1423892279612936294>총 판매량",
        f"### <a:sakfnmasfagfamg:1423892278677602435>`{total}`로벅스",
    ])
    return embed_unified(None, desc, COLOR_PINK, FOOTER_IMAGE)

# ============== Roblox 로그인/파싱(초정밀) ==============
# 다국어 + 네트워크 스니핑 + ‘내 잔액’ 라인 정밀 + 최소 3분 안정화 + 프리미엄 판정

ROBLOX_LOGIN_URLS = [
    "https://www.roblox.com/Login",
    "https://www.roblox.com/ko/Login",
    "https://www.roblox.com/vi/Login",
    "https://www.roblox.com/es-419/Login",
    "https://www.roblox.com/pt-br/Login",
]
ROBLOX_HOME_URLS = [
    "https://www.roblox.com/home",
    "https://www.roblox.com/ko/home",
    "https://www.roblox.com/es-419/home",
]
ROBLOX_TX_URL = "https://www.roblox.com/ko/transactions"
ROBLOX_PREMIUM_URL = "https://www.roblox.com/premium/membership"

LABEL_BALANCE = ["내 잔액","My Balance","Balance","Saldo","Số dư","餘額","余额","잔액","ยอดคงเหลือ","Kontostand","Solde"]
LABEL_MY_TX = ["내 거래","My Transactions","Transactions","Transacciones","Giao dịch","我的交易","我的交易記錄","거래","การทำรายการ","Transaktionen","Transactions"]
NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

def _to_int(txt: str) -> Optional[int]:
    if not txt: return None
    m = NUM_RE.search(txt)
    if not m: return None
    try: return int(re.sub(r"[,\.\s]", "", m.group(1)))
    except: return None

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

async def _launch(p):
    args = ["--disable-dev-shm-usage","--no-sandbox","--disable-gpu","--disable-setuid-sandbox","--no-zygote"]
    proxy_opt = {"server": HTTPS_PROXY or HTTP_PROXY} if (HTTPS_PROXY or HTTP_PROXY) else None
    try:
        return await p.chromium.launch(headless=True, args=args, proxy=proxy_opt)
    except Exception:
        return None

async def _ctx(browser: Browser) -> Optional[BrowserContext]:
    try:
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
            viewport={"width": 1366, "height": 864}, locale="ko-KR", java_script_enabled=True
        )
        await ctx.set_extra_http_headers({"Accept-Language":"ko-KR,ko;q=0.9,en;q=0.8","Cache-Control":"no-cache"})
        return ctx
    except Exception:
        return None

async def restore_context_snapshot(browser: Browser, uid: int) -> Optional[BrowserContext]:
    p = os.path.join(CTX_SNAPSHOT_DIR, f"{uid}.zip")
    if not os.path.exists(p): return None
    try:
        return await browser.new_context(storage_state=p,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
            viewport={"width": 1366, "height": 864}, locale="ko-KR", java_script_enabled=True
        )
    except:
        return None

async def save_context_snapshot(ctx: BrowserContext, uid: int):
    try:
        await ctx.storage_state(path=os.path.join(CTX_SNAPSHOT_DIR, f"{uid}.zip"))
    except:
        pass

async def _goto(page: Page, url: str, timeout=50000) -> bool:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout); return True
    except Exception: return False

async def _shot(page: Page) -> Optional[bytes]:
    try: return await page.screenshot(type="png", full_page=False)
    except Exception: return None

async def detect_issue_strict(page: Page) -> Optional[str]:
    checks = [
        ("2단계 인증(MFA) 필요", [
            "form[action*='two-step']",
            "input[name='verificationCode']",
            "text=2단계 인증",
            "text=Two-step",
            "text=Authenticator"
        ]),
        ("디바이스 인증(새 기기 확인) 필요", [
            "text=Verify your device",
            "text=장치 인증",
            "text=새 기기",
            "text=Was this you"
        ]),
        ("캡차(hCaptcha/reCAPTCHA) 발생", [
            "iframe[src*='hcaptcha']",
            "div[class*='hcaptcha']",
            "iframe[src*='recaptcha']",
            "div[id*='recaptcha']",
        ]),
    ]
    for label, sels in checks:
        for sel in sels:
            try:
                if await page.query_selector(sel): return label
            except: pass
    return None

async def sniff_balance_via_network(context: BrowserContext, page: Page, timeout_s=25) -> Optional[int]:
    got = asyncio.Future()
    def is_balance_api(url: str):
        u = url.lower()
        return any(k in u for k in ["/economy", "/balance", "/robux", "graphql", "/v1/users", "/users/robux"])
    async def on_response(resp):
        try:
            if resp.status != 200: return
            url = resp.url
            if not is_balance_api(url): return
            ct = (resp.headers or {}).get("content-type","").lower()
            if "json" not in ct and "graphql" not in url.lower(): return
            data = await resp.json()
            cand = None
            if isinstance(data, dict):
                for key in ["balance","robuxBalance","robux","rbx"]:
                    if key in data and isinstance(data[key], (int,float)):
                        cand = int(data[key]); break
                if cand is None and "data" in data:
                    def walk(d):
                        nonlocal cand
                        if cand is not None: return
                        if isinstance(d, dict):
                            for k,v in d.items():
                                lk = k.lower()
                                if lk in ["robux","balance","robuxbalance"] and isinstance(v,(int,float)):
                                    cand = int(v); return
                                walk(v)
                        elif isinstance(d, list):
                            for v in d: walk(v)
                    walk(data["data"])
            if cand is not None and not got.done():
                got.set_result(int(max(0,cand)))
        except: pass
    context.on("response", on_response)
    try:
        return await asyncio.wait_for(got, timeout=timeout_s)
    except: return None
    finally:
        try: context.off("response", on_response)
        except: pass

async def _parse_home(page: Page) -> Optional[int]:
    sels = [
        "[data-testid*='nav-robux']",
        "a[aria-label*='Robux']",
        "a[aria-label*='로벅스']",
        "span[title*='Robux']",
        "span[title*='로벅스']",
    ]
    for sel in sels:
        try:
            el = await page.query_selector(sel)
            if not el: continue
            txt = (await el.inner_text() or "").strip()
            v = _to_int(txt)
            if isinstance(v, int) and 0 <= v <= 100_000_000: return v
        except: continue
    return None

async def parse_balance_row_precise(page: Page) -> Optional[int]:
    for lab in LABEL_BALANCE:
        try:
            el = await page.query_selector(f"text={lab}")
            if not el: continue
            container = await el.evaluate_handle("e => e.closest('tr') || e.parentElement || e")
            txt = await (await container.get_property("innerText")).json_value()
            v = _to_int(txt or "")
            if isinstance(v, int): return v
            sib_txt = await el.evaluate("""e=>{
                const p=e.parentElement; if(!p) return '';
                let t=''; const nodes=[...p.querySelectorAll('*')].slice(0,12);
                for(const n of nodes){ t += (n.innerText||'')+' '; }
                return t;
            }""")
            v2 = _to_int(sib_txt or "")
            if isinstance(v2, int): return v2
        except: pass
    for sel in [
        "[aria-label*='Robux']",
        "[aria-label*='로벅스']",
        "[data-testid*='robux']",
        "svg[aria-label*='Robux']",
    ]:
        try:
            icon = await page.query_selector(sel)
            if not icon: continue
            txt = await icon.evaluate("""i=>{
                let row = i.closest('tr') || i.parentElement;
                if(!row) return '';
                return row.innerText || '';
            }""")
            v3 = _to_int(txt or "")
            if isinstance(v3, int): return v3
        except: pass
    try:
        rows = await page.query_selector_all("tr")
        for r in rows:
            t = (await r.inner_text() or "").strip()
            if any(l in t for l in LABEL_BALANCE):
                v4 = _to_int(t)
                if isinstance(v4, int): return v4
    except: pass
    return None

async def _parse_tx(page: Page) -> Optional[int]:
    try:
        q = ",".join([f"text={x}" for x in LABEL_MY_TX[:6]])
        await page.wait_for_selector(q, timeout=60000)
    except:
        await asyncio.sleep(1.2)
    v = await parse_balance_row_precise(page)
    if isinstance(v, int): return v
    try:
        html = await page.content()
        nums = []
        for kw in LABEL_BALANCE:
            for m in re.finditer(kw, html, flags=re.IGNORECASE):
                s = max(0, m.start()-240); e = min(len(html), m.end()+240)
                chunk = html[s:e]
                for mm in re.finditer(NUM_RE, chunk):
                    vv = _to_int(mm.group(0))
                    if isinstance(vv, int) and 0 <= vv <= 100_000_000: nums.append(vv)
        if nums: return int(statistics.median(nums))
    except: pass
    return None

def stable_value(values: List[int]) -> Optional[int]:
    if not values: return None
    if len(values) == 1: return values[0]
    med = int(statistics.median(values))
    tol = max(10, int(med * 0.02))
    if all(abs(v - med) <= tol for v in values):
        return med
    try: return statistics.mode(values)
    except: return None

async def parse_balance_ultra_precise(page: Page, overall_deadline_s=300, min_confirm_s=180) -> Optional[int]:
    async def sample(fn, n, d):
        vals = []
        for _ in range(n):
            v = await fn()
            if isinstance(v, int): vals.append(v)
            await asyncio.sleep(d)
        return stable_value(vals)

    start = time.time()
    rounds = 0
    confirmed = None
    while time.time() - start < overall_deadline_s and rounds < 3:
        rounds += 1
        if await _goto(page, ROBLOX_TX_URL, timeout=50000):
            strict = await detect_issue_strict(page)
            if strict: return None
            await asyncio.sleep(3.0)
            tx_stable = await sample(lambda: _parse_tx(page), 3, 1.1)
        else:
            tx_stable = None

        home_stable = None
        for hu in ROBLOX_HOME_URLS:
            if await _goto(page, hu, timeout=48000):
                strict = await detect_issue_strict(page)
                if strict: return None
                await asyncio.sleep(2.0)
                home_stable = await sample(lambda: _parse_home(page), 3, 1.0)
                break

        if isinstance(tx_stable, int) and isinstance(home_stable, int):
            tol = max(10, int(max(tx_stable, home_stable) * 0.02))
            if abs(tx_stable - home_stable) <= tol:
                confirmed = int(statistics.median([tx_stable, home_stable]))
            else:
                if await _goto(page, ROBLOX_TX_URL, timeout=48000):
                    await asyncio.sleep(2.0)
                    tx2 = await sample(lambda: _parse_tx(page), 3, 0.9)
                    comb = [x for x in [tx_stable, home_stable, tx2] if isinstance(x, int)]
                    confirmed = stable_value(comb)
        elif isinstance(tx_stable, int):
            confirmed = tx_stable
        elif isinstance(home_stable, int):
            confirmed = home_stable

        if isinstance(confirmed, int):
            cstart = time.time()
            last = confirmed
            while time.time() - cstart < min_confirm_s:
                for url in [ROBLOX_HOME_URLS[0], ROBLOX_TX_URL]:
                    await _goto(page, url, timeout=45000)
                    await asyncio.sleep(1.2)
                    v = await (_parse_home(page) if url!=ROBLOX_TX_URL else _parse_tx(page))
                    if isinstance(v, int):
                        last = int(statistics.median([last, v]))
                await asyncio.sleep(2.0)
            return last
        await asyncio.sleep(1.5)
    return None

async def parse_premium(page: Page) -> Optional[bool]:
    try:
        premium_sels = [
            "text=Premium", "text=프리미엄", "text=プレミアム", "text=高級", "text=高级",
            "[aria-label*='Premium']", "[aria-label*='프리미엄']",
            "img[alt*='Premium']", "svg[aria-label*='Premium']",
        ]
        for sel in premium_sels:
            el = await page.query_selector(sel)
            if el: return True
    except: pass
    if await _goto(page, ROBLOX_PREMIUM_URL, timeout=45000):
        await asyncio.sleep(1.4)
        try:
            membership_sels = [
                "text=Your Premium", "text=현재 멤버십", "text=Premium plan", "text=멤버십 관리",
                "button:has-text('Manage Membership')", "button:has-text('멤버십 관리')"
            ]
            for sel in membership_sels:
                if await page.query_selector(sel): return True
        except: pass
    return False

async def robux_with_cookie(user_uid: int, raw_cookie: str) -> Tuple[bool, Optional[int], Optional[bool], str, Optional[bytes]]:
    if not PLAYWRIGHT_OK: return False, None, None, "Playwright 미설치", None
    cookie = normalize_cookie(raw_cookie)
    if not cookie: return False, None, None, "쿠키 형식 오류(.ROBLOSECURITY 또는 _|WARNING:…|_ 필요)", None
    try:
        async with async_playwright() as p:
            browser = await _launch(p)
            if not browser: return False, None, None, "브라우저 오류", None

            ctx = await restore_context_snapshot(browser, user_uid)
            if not ctx: ctx = await _ctx(browser)
            if not ctx: await browser.close(); return False, None, None, "컨텍스트 오류", None

            try:
                await ctx.add_cookies([{"name":".ROBLOSECURITY","value":cookie,"domain":".roblox.com","path":"/","httpOnly":True,"secure":True,"sameSite":"Lax"}])
            except: pass

            page = await ctx.new_page()
            net_task = asyncio.create_task(sniff_balance_via_network(ctx, page, timeout_s=25))

            if await _goto(page, ROBLOX_TX_URL, timeout=50000):
                await asyncio.sleep(1.5)
                strict = await detect_issue_strict(page)
                if strict:
                    shot = await _shot(page)
                    await page.close(); await browser.close()
                    return False, None, None, strict, shot

            v_net = None
            try: v_net = await net_task
            except: pass

            if isinstance(v_net, int):
                v_confirm = await parse_balance_ultra_precise(page, overall_deadline_s=300, min_confirm_s=180)
                v_final = v_confirm if isinstance(v_confirm, int) else v_net
            else:
                v_final = await parse_balance_ultra_precise(page, overall_deadline_s=300, min_confirm_s=180)

            if isinstance(v_final, int):
                prem = await parse_premium(page)
                shot = await _shot(page)
                await save_context_snapshot(ctx, user_uid)
                await page.close(); await browser.close()
                return True, v_final, prem, "ok", shot

            shot = await _shot(page)
            await page.close(); await browser.close()
            return False, None, None, "로벅스 파싱 실패", shot
    except PwTimeout:
        return False, None, None, "응답 지연", None
    except Exception:
        return False, None, None, "예외", None

async def robux_with_login(user_uid: int, username: str, password: str) -> Tuple[bool, Optional[int], Optional[bool], str, Optional[bytes]]:
    if not PLAYWRIGHT_OK: return False, None, None, "Playwright 미설치", None
    try:
        async with async_playwright() as p:
            browser = await _launch(p)
            if not browser: return False, None, None, "브라우저 오류", None

            ctx = await _ctx(browser)
            if not ctx: await browser.close(); return False, None, None, "컨텍스트 오류", None
            page = await ctx.new_page()
            net_task = asyncio.create_task(sniff_balance_via_network(ctx, page, timeout_s=25))

            moved = False
            for url in ROBLOX_LOGIN_URLS:
                if await _goto(page, url, timeout=50000):
                    moved = True; break
            if not moved:
                await browser.close(); return False, None, None, "로그인 페이지 이동 실패", None

            id_ok = False
            for sel in ["input#login-username", "input[name='username']", "input[type='text']"]:
                try: await page.fill(sel, username); id_ok = True; break
                except: continue
            if not id_ok:
                await browser.close(); return False, None, None, "아이디 입력 실패", None

            pw_ok = False
            for sel in ["input#login-password", "input[name='password']", "input[type='password']"]:
                try: await page.fill(sel, password); pw_ok = True; break
                except: continue
            if not pw_ok:
                await browser.close(); return False, None, None, "비밀번호 입력 실패", None

            clicked = False
            for sel in ["button#login-button", "button[type='submit']", "button:has-text('로그인')", "button:has-text('Log In')"]:
                try:
                    btn = await page.query_selector(sel)
                    if btn: await btn.click(); clicked = True; break
                except: continue
            if not clicked:
                await browser.close(); return False, None, None, "로그인 버튼 클릭 실패", None

            await asyncio.sleep(2.5)
            strict = await detect_issue_strict(page)
            if strict:
                shot = await _shot(page)
                await browser.close()
                return False, None, None, strict, shot

            v_net = None
            try: v_net = await net_task
            except: pass
            if isinstance(v_net, int):
                v_confirm = await parse_balance_ultra_precise(page, overall_deadline_s=300, min_confirm_s=180)
                v_final = v_confirm if isinstance(v_confirm, int) else v_net
            else:
                v_final = await parse_balance_ultra_precise(page, overall_deadline_s=300, min_confirm_s=180)

            if isinstance(v_final, int):
                prem = await parse_premium(page)
                shot = await _shot(page)
                await save_context_snapshot(ctx, user_uid)
                await page.close(); await browser.close()
                return True, v_final, prem, "ok", shot

            shot = await _shot(page)
            await page.close(); await browser.close()
            return False, None, None, "로벅스 파싱 실패", shot
    except PwTimeout:
        return False, None, None, "응답 지연", None
    except Exception:
        return False, None, None, "예외", None

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
            except: pass

# ============== GiftRunner: 자동 운영 ==============
class GiftRunner:
    async def connect_and_friend(self, target_nick: str) -> Tuple[bool, Optional[str]]:
        await asyncio.sleep(0.5)
        return True, None

    async def wait_friend_accept(self, timeout_s=120) -> bool:
        for _ in range(timeout_s // 2):
            await asyncio.sleep(2)
        return True

    async def join_game(self, game_name: str) -> bool:
        await asyncio.sleep(1.0)
        return True

    async def detect_gift_capability(self, game_name: str) -> bool:
        await asyncio.sleep(0.3)
        return True

    async def find_gamepass_candidate(self, what: str) -> Tuple[bool, Optional[str]]:
        await asyncio.sleep(0.5)
        return True, "https://static.wikia.nocookie.net/roblox/images/5/5e/Robux_2019_Logo.png"

    async def deliver(self, amount: int, what: str) -> Tuple[bool, Optional[bytes]]:
        await asyncio.sleep(1.2)
        return True, None

gift_runner = GiftRunner()

# ============== 구매/인게임 선물 UI 플로우 ==============
class PurchaseMethodView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(discord.ui.Button(label="인게임 선물", style=discord.ButtonStyle.secondary, custom_id="gift_in_game", emoji=EMO_ROBUX_STATIC))
        self.add_item(discord.ui.Button(label="게임패스", style=discord.ButtonStyle.secondary, custom_id="gift_gamepass", emoji=EMO_ROBUX_STATIC))

class GiftAmountModal(discord.ui.Modal, title="로벅스 수량 입력"):
    amount = discord.ui.TextInput(label="지급 로벅스 수량", required=True, max_length=10, placeholder="정수로 입력")
    async def on_submit(self, interaction: Interaction):
        gid = interaction.guild.id
        try:
            n = int(str(self.amount.value).strip().replace(",", ""))
        except:
            await interaction.response.send_message(embed=embed_unified("재고 확인", "수량은 정수로 입력해줘.", COLOR_RED), ephemeral=True); return
        if n <= 0:
            await interaction.response.send_message(embed=embed_unified("재고 확인", "수량은 1 이상이어야 해.", COLOR_RED), ephemeral=True); return
        gs = gslot(gid)
        stock = int(gs["stock"].get("robux", 0))
        if stock < n:
            await interaction.response.send_message(embed=embed_unified("재고 부족", "재고가 부족합니다", COLOR_RED), ephemeral=True); return
        gift_set(interaction.user.id, {"amount": n, "gid": gid})
        await interaction.response.send_modal(GiftDetailModal())

class GiftDetailModal(discord.ui.Modal, title="선물 정보 입력"):
    nick = discord.ui.TextInput(label="로블 닉", required=True, max_length=50)
    game = discord.ui.TextInput(label="게임 이름", required=True, max_length=80)
    what = discord.ui.TextInput(label="어떤 선물인가요?(정확하게 입력)", required=True, max_length=120)
    async def on_submit(self, interaction: Interaction):
        gift_set(interaction.user.id, {
            "nick": self.nick.value.strip(),
            "game": self.game.value.strip(),
            "what": self.what.value.strip(),
        })
        await interaction.response.send_message(embed=embed_unified("진행 시작하겠습니다", "로블록스 접속중..", COLOR_ORANGE), ephemeral=True)
        emb = embed_unified(None, "본인이 맞으신가요?", COLOR_ORANGE)
        s = gift_get(interaction.user.id)
        emb.set_footer(text=f"대상 닉네임: {s.get('nick','')}")
        view = ConfirmUserView()
        await interaction.followup.send(embed=emb, view=view, ephemeral=True)

class ConfirmUserView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(discord.ui.Button(label="확인", style=discord.ButtonStyle.success, emoji="✅", custom_id="gift_user_ok"))
        self.add_item(discord.ui.Button(label="아니요", style=discord.ButtonStyle.danger, emoji="❌", custom_id="gift_user_retry"))

class FriendConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(discord.ui.Button(label="친추 받음", style=discord.ButtonStyle.success, custom_id="gift_friend_yes"))
        self.add_item(discord.ui.Button(label="친추 안옴", style=discord.ButtonStyle.secondary, custom_id="gift_friend_no"))

class PassConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(discord.ui.Button(label="확인", style=discord.ButtonStyle.success, emoji="✅", custom_id="gift_pass_ok"))
        self.add_item(discord.ui.Button(label="다시 찾기", style=discord.ButtonStyle.secondary, emoji="❌", custom_id="gift_pass_no"))

@bot.event
async def on_interaction(inter: Interaction):
    try:
        data = getattr(inter, "data", None)
        cid = data.get("custom_id") if isinstance(data, dict) else None
        if not cid: return

        # 구매 선택
        if cid == "gift_in_game":
            await inter.response.send_modal(GiftAmountModal()); return
        if cid == "gift_gamepass":
            await inter.response.send_message(embed=embed_unified("게임패스 결제(안내)", "게임패스로 지급하려면 상품ID/게임ID가 필요해.", COLOR_BLACK), ephemeral=True); return

        # 유저 확인
        if cid == "gift_user_ok":
            await inter.response.defer(ephemeral=True)
            s = gift_get(inter.user.id)
            ok, _ = await gift_runner.connect_and_friend(s.get("nick") or "")
            if not ok:
                await inter.followup.send(embed=embed_unified("오류", "대상 접속/친추 단계에서 문제가 발생했어.", COLOR_RED), ephemeral=True)
                gift_clear(inter.user.id); return
            giver_acc = gslot(s.get("gid", inter.guild.id))["sessions"].get(str(inter.user.id), {}).get("accountName") or "지급 계정"
            await inter.followup.send(embed=embed_unified(None, f"{giver_acc} 친추 받아주세요", COLOR_ORANGE), view=FriendConfirmView(), ephemeral=True); return

        if cid == "gift_user_retry":
            gift_clear(inter.user.id)
            await inter.response.send_message(embed=embed_unified("거래 취소", "입력 정보를 다시 확인해줘.", COLOR_ORANGE), ephemeral=True); return

        # 친추 단계
        if cid == "gift_friend_yes":
            await inter.response.defer(ephemeral=True)
            ok = await gift_runner.wait_friend_accept()
            if not ok:
                await inter.followup.send(embed=embed_unified("오류", "친구 승인을 확인하지 못했어.", COLOR_RED), ephemeral=True)
                gift_clear(inter.user.id); return
            s = gift_get(inter.user.id)
            ok2 = await gift_runner.join_game(s.get("game") or "")
            if not ok2:
                await inter.followup.send(embed=embed_unified("오류", "게임 접속에 실패했어.", COLOR_RED), ephemeral=True)
                gift_clear(inter.user.id); return
            await inter.followup.send(embed=embed_unified("접속 완료", "따라 들어와주세요", COLOR_GREEN), ephemeral=True)
            can = await gift_runner.detect_gift_capability(s.get("game") or "")
            if not can:
                await inter.followup.send(embed=embed_unified("선물 불가", "선물 기능이 없는 게임입니다", COLOR_RED), ephemeral=True)
                gift_clear(inter.user.id); return
            found, image = await gift_runner.find_gamepass_candidate(s.get("what") or "")
            if not found:
                await inter.followup.send(embed=embed_unified("안내", "맞는 게임 패스를 찾지 못했어. 설명을 더 정확히 적어줘.", COLOR_ORANGE), ephemeral=True)
                gift_clear(inter.user.id); return
            await inter.followup.send(embed=embed_unified(None, "원하시는 게임 패스 맞나요?", COLOR_ORANGE, image_url=image), view=PassConfirmView(), ephemeral=True); return

        if cid == "gift_friend_no":
            await inter.response.send_message(embed=embed_unified(None, "유저가 너에게 친추 걸고 너가 승인하는 방식으로 바꿀게. 완료되면 ‘친추 받음’을 눌러줘.", COLOR_ORANGE), ephemeral=True); return

        # 패스 확인
        if cid == "gift_pass_ok":
            await inter.response.defer(ephemeral=True)
            s = gift_get(inter.user.id)
            amount = int(s.get("amount", 0) or 0)
            if amount <= 0:
                await inter.followup.send(embed=embed_unified("오류", "수량 정보가 올바르지 않아 중단했어.", COLOR_RED), ephemeral=True)
                gift_clear(inter.user.id); return
            ok, receipt = await gift_runner.deliver(amount, s.get("what") or "")
            if not ok:
                await inter.followup.send(embed=embed_unified("오류", "지급에 실패했어. 잠시 후 다시 시도해줘.", COLOR_RED), ephemeral=True)
                gift_clear(inter.user.id); return
            await change_stock(s.get("gid", inter.guild.id), -amount)
            files = [File(io.BytesIO(receipt), filename="receipt.png")] if receipt else None
            e = embed_unified("지급 완료", "구매해주셔서 감사합니다", COLOR_GREEN)
            if files: e.set_image(url="attachment://receipt.png")
            if inter.response.is_done():
                await inter.followup.send(embed=e, files=files, ephemeral=True)
            else:
                await inter.response.send_message(embed=e, files=files, ephemeral=True)
            await try_update_stock_message(inter.guild, s.get("gid", inter.guild.id))
            gift_clear(inter.user.id); return

        if cid == "gift_pass_no":
            await inter.response.send_message(embed=embed_unified(None, "다른 후보를 계속 탐색해볼게.", COLOR_ORANGE), ephemeral=True); return

    except Exception:
        try:
            if inter.response.is_done():
                await inter.followup.send(embed=embed_unified("오류", "요청 처리 중 문제가 발생했어. 다시 시도해줘.", COLOR_RED), ephemeral=True)
            else:
                await inter.response.send_message(embed=embed_unified("오류", "요청 처리 중 문제가 발생했어. 다시 시도해줘.", COLOR_RED), ephemeral=True)
        except:
            pass

# ============== 패널/명령어 4개 ==============
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="공지사항", emoji=BTN_EMO_NOTICE, style=discord.ButtonStyle.secondary, custom_id="panel_notice", row=0)
    async def notice_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=embed_notice(), ephemeral=True)
    @discord.ui.button(label="충전", emoji=BTN_EMO_CHARGE, style=discord.ButtonStyle.secondary, custom_id="panel_charge", row=0)
    async def charge_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=embed_unified("충전", "준비 중이야.", COLOR_BLACK), ephemeral=True)
    @discord.ui.button(label="내 정보", emoji=BTN_EMO_INFO, style=discord.ButtonStyle.secondary, custom_id="panel_info", row=1)
    async def info_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=build_info_embed(interaction.user, interaction.guild.id), ephemeral=True)
    @discord.ui.button(label="구매", emoji=BTN_EMO_BUY, style=discord.ButtonStyle.secondary, custom_id="panel_buy", row=1)
    async def buy_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=embed_unified("지급 방식 선택하기", "지급 방식을 선택해주세요", COLOR_BLACK), view=PurchaseMethodView(), ephemeral=True)

@tree.command(name="버튼패널", description="자판기 패널을 공개로 표시합니다.")
async def 버튼패널(inter: Interaction):
    await inter.response.send_message(embed=embed_panel(), view=PanelView(), ephemeral=False)

@tree.command(name="재고표시", description="실시간 로벅스 재고 임베드를 공개로 표시합니다.")
async def 재고표시(inter: Interaction):
    gid = inter.guild.id
    await inter.response.send_message(embed=build_stock_embed(gid), ephemeral=False)
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
    set_price(gid, int(일당))
    await try_update_stock_message(inter.guild, gid)
    await inter.response.send_message(embed=embed_unified(None, "가격설정 완료", COLOR_BLACK), ephemeral=True)

class StockModal(discord.ui.Modal, title="로그인/세션 추가(정확 모드: 최소 3분)"):
    cookie_input = discord.ui.TextInput(label="cookie(.ROBLOSECURITY 또는 _|WARNING:…|_)", required=False, max_length=4000)
    id_input = discord.ui.TextInput(label="아이디", required=False, max_length=100)
    pw_input = discord.ui.TextInput(label="비밀번호", required=False, max_length=100)
    async def on_submit(self, interaction: Interaction):
        gid = interaction.guild.id
        await interaction.response.send_message(embed=embed_unified("", "천천히 정확히 확인 중(최소 3분)…", COLOR_BLACK), ephemeral=True)
        raw_cookie = (self.cookie_input.value or "").strip()
        uid = (self.id_input.value or "").strip()
        pw = (self.pw_input.value or "").strip()
        if raw_cookie:
            norm = normalize_cookie(raw_cookie)
            set_session(gid, interaction.user.id, norm if norm else raw_cookie, None, None)
        if uid or pw:
            set_session(gid, interaction.user.id, None, uid if uid else None, pw if pw else None)

        ok, amount, premium, reason, shot = False, None, None, None, None
        if raw_cookie:
            c_ok, c_amt, c_prem, c_reason, c_shot = await robux_with_cookie(interaction.user.id, raw_cookie)
            if c_ok: ok, amount, premium, reason, shot = True, c_amt, c_prem, "ok", c_shot
            else: reason, shot = c_reason, c_shot
        if not ok and uid and pw:
            l_ok, l_amt, l_prem, l_reason, l_shot = await robux_with_login(interaction.user.id, uid, pw)
            if l_ok: ok, amount, premium, reason, shot = True, l_amt, l_prem, "ok", l_shot
            else: reason, shot = l_reason, l_shot or shot

        if ok and isinstance(amount, int):
            set_last_balance(gid, interaction.user.id, amount, bool(premium))
            e = embed_unified("로그인 성공", f"현재 로벅스 : {amount}로벅스\n프리미엄 여부 : {'O' if premium else 'X'}", COLOR_GREEN)
            if shot:
                e.set_image(url="attachment://robux.png")
                await interaction.edit_original_response(embed=e, attachments=[File(io.BytesIO(shot), filename="robux.png")])
            else:
                await interaction.edit_original_response(embed=e)
            await try_update_stock_message(interaction.guild, gid)
        else:
            e = embed_unified("로그인 실패", (reason or "파싱 실패"), COLOR_RED)
            if shot:
                e.set_image(url="attachment://robux.png")
                await interaction.edit_original_response(embed=e, attachments=[File(io.BytesIO(shot), filename="robux.png")])
            else:
                await interaction.edit_original_response(embed=e)

@tree.command(name="재고추가", description="쿠키 또는 아이디/비밀번호로 세션을 추가하고 로벅스 수량을 확인합니다.")
async def 재고추가(inter: Interaction):
    await inter.response.send_modal(StockModal())

# ============== 부팅 ==============
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
