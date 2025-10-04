import os, io, json, re, asyncio, time, statistics, pathlib
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
HTTP_PROXY = os.getenv("HTTP_PROXY", "").strip() or None
HTTPS_PROXY = os.getenv("HTTPS_PROXY", "").strip() or None

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ===== DB =====
DATA_PATH = "data.json"
CTX_SNAPSHOT_DIR = "ctx_snapshots"
pathlib.Path(CTX_SNAPSHOT_DIR).mkdir(parents=True, exist_ok=True)

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
    e = Embed(description=desc, colour=COLOR_PINK)
    e.set_image(url=FOOTER_IMAGE)
    return e

# ===== Roblox 로그인/파싱 =====
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

# 다국어 라벨 및 주변 패턴
LABEL_BALANCE = [
    "내 잔액","My Balance","Balance","Saldo","Số dư","餘額","余额","잔액","ยอดคงเหลือ","Kontostand","Solde"
]
LABEL_MY_TX = [
    "내 거래","My Transactions","Transactions","Transacciones","Giao dịch","我的交易","我的交易記錄","거래","การทำรายการ","Transaktionen","Transactions"
]

NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

def _to_int(txt: str) -> Optional[int]:
    if not txt: return None
    m = NUM_RE.search(txt)
    if not m: return None
    try: return int(re.sub(r"[,\.\s]", "", m.group(1)))
    except Exception: return None

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
        await ctx.set_extra_http_headers({
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache"
        })
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
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        return True
    except Exception:
        return False

async def _shot(page: Page) -> Optional[bytes]:
    try: return await page.screenshot(type="png", full_page=False)
    except Exception: return None

# 엄격 보안 판정(오탐 방지)
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
                el = await page.query_selector(sel)
                if el: return label
            except: pass
    return None

# 네트워크 스니핑
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
        except:
            pass
    context.on("response", on_response)
    try:
        return await asyncio.wait_for(got, timeout=timeout_s)
    except:
        return None
    finally:
        try: context.off("response", on_response)
        except: pass

# 홈 뱃지 파싱
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
            if isinstance(v, int) and 0 <= v <= 100_000_000:
                return v
        except: continue
    return None

# 거래 페이지: “내 잔액” 행에서 Robux 아이콘 옆 숫자만
async def parse_balance_row_precise(page: Page) -> Optional[int]:
    # 1) 다국어 라벨 근접
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
    # 2) Robux 아이콘 근처
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
    # 3) 표 행 스캔
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
        # 다국어 “내 거래” 타이틀 대기
        q = ",".join([f"text={x}" for x in LABEL_MY_TX[:6]])
        await page.wait_for_selector(q, timeout=60000)
    except:
        await asyncio.sleep(1.2)
    v = await parse_balance_row_precise(page)
    if isinstance(v, int): return v
    # 폴백: 라벨 텍스트 주변 문맥 스캔(다국어)
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
        if nums:
            return int(statistics.median(nums))
    except:
        pass
    return None

# 표본 안정화 + 최소 3분 보장
def stable_value(values: List[int]) -> Optional[int]:
    if not values: return None
    if len(values) == 1: return values[0]
    med = int(statistics.median(values))
    tol = max(10, int(med * 0.02))
    if all(abs(v - med) <= tol for v in values):
        return med
    try:
        return statistics.mode(values)
    except:
        return None

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

        # 거래 → 표본
        if await _goto(page, ROBLOX_TX_URL, timeout=50000):
            # 엄격 보안 체크(오탐 방지)
            strict = await detect_issue_strict(page)
            if strict: return None
            await asyncio.sleep(3.0)
            tx_stable = await sample(lambda: _parse_tx(page), 3, 1.1)
        else:
            tx_stable = None

        # 홈 → 표본
        home_stable = None
        for hu in ROBLOX_HOME_URLS:
            if await _goto(page, hu, timeout=48000):
                strict = await detect_issue_strict(page)
                if strict: return None
                await asyncio.sleep(2.0)
                home_stable = await sample(lambda: _parse_home(page), 3, 1.0)
                break

        # 결합 판단
        if isinstance(tx_stable, int) and isinstance(home_stable, int):
            tol = max(10, int(max(tx_stable, home_stable) * 0.02))
            if abs(tx_stable - home_stable) <= tol:
                confirmed = int(statistics.median([tx_stable, home_stable]))
            else:
                # 거래 재표본
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
            # 최소 3분 안정화 루프
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

# 쿠키 로그인
async def robux_with_cookie(user_uid: int, raw_cookie: str) -> Tuple[bool, Optional[int], str, Optional[bytes]]:
    if not PLAYWRIGHT_OK: return False, None, "Playwright 미설치", None
    cookie = normalize_cookie(raw_cookie)
    if not cookie: return False, None, "쿠키 형식 오류(.ROBLOSECURITY 또는 _|WARNING:…|_ 필요)", None
    try:
        async with async_playwright() as p:
            browser = await _launch(p)
            if not browser: return False, None, "브라우저 오류", None

            ctx = await restore_context_snapshot(browser, user_uid)
            if not ctx: ctx = await _ctx(browser)
            if not ctx: await browser.close(); return False, None, "컨텍스트 오류", None

            try:
                await ctx.add_cookies([{"name":".ROBLOSECURITY","value":cookie,"domain":".roblox.com","path":"/","httpOnly":True,"secure":True,"sameSite":"Lax"}])
            except: pass

            page = await ctx.new_page()
            net_task = asyncio.create_task(sniff_balance_via_network(ctx, page, timeout_s=25))

            # 빠른 보안 체크
            if await _goto(page, ROBLOX_TX_URL, timeout=50000):
                await asyncio.sleep(1.5)
                strict = await detect_issue_strict(page)
                if strict:
                    shot = await _shot(page)
                    await page.close(); await browser.close()
                    return False, None, strict, shot

            v_net = None
            try: v_net = await net_task
            except: pass
            if isinstance(v_net, int):
                # 최소 3분 안정화
                v_confirm = await parse_balance_ultra_precise(page, overall_deadline_s=300, min_confirm_s=180)
                v_final = v_confirm if isinstance(v_confirm, int) else v_net
                shot = await _shot(page)  # 확정 직후 스샷
                await save_context_snapshot(ctx, user_uid)
                await page.close(); await browser.close()
                return True, v_final, "ok", shot

            # 폴백: UI 초정밀
            v_final = await parse_balance_ultra_precise(page, overall_deadline_s=300, min_confirm_s=180)
            shot = await _shot(page)
            await save_context_snapshot(ctx, user_uid) if isinstance(v_final, int) else None
            await page.close(); await browser.close()
            if isinstance(v_final, int): return True, v_final, "ok", shot
            return False, None, "로벅스 파싱 실패", shot
    except PwTimeout:
        return False, None, "응답 지연", None
    except Exception:
        return False, None, "예외", None

# ID/PW 로그인
async def robux_with_login(user_uid: int, username: str, password: str) -> Tuple[bool, Optional[int], str, Optional[bytes]]:
    if not PLAYWRIGHT_OK: return False, None, "Playwright 미설치", None
    try:
        async with async_playwright() as p:
            browser = await _launch(p)
            if not browser: return False, None, "브라우저 오류", None

            ctx = await _ctx(browser)
            if not ctx: await browser.close(); return False, None, "컨텍스트 오류", None
            page = await ctx.new_page()
            net_task = asyncio.create_task(sniff_balance_via_network(ctx, page, timeout_s=25))

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
            strict = await detect_issue_strict(page)
            if strict:
                shot = await _shot(page)
                await browser.close()
                return False, None, strict, shot

            v_net = None
            try: v_net = await net_task
            except: pass
            if isinstance(v_net, int):
                v_confirm = await parse_balance_ultra_precise(page, overall_deadline_s=300, min_confirm_s=180)
                v_final = v_confirm if isinstance(v_confirm, int) else v_net
                shot = await _shot(page)
                await save_context_snapshot(ctx, user_uid)
                await page.close(); await browser.close()
                return True, v_final, "ok", shot

            v_final = await parse_balance_ultra_precise(page, overall_deadline_s=300, min_confirm_s=180)
            shot = await _shot(page)
            await save_context_snapshot(ctx, user_uid) if isinstance(v_final, int) else None
            await page.close(); await browser.close()
            if isinstance(v_final, int): return True, v_final, "ok", shot
            return False, None, "로벅스 파싱 실패", shot
    except PwTimeout:
        return False, None, "응답 지연", None
    except Exception:
        return False, None, "예외", None

# ===== 패널/명령어 =====
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

class StockModal(discord.ui.Modal, title="세션/로그인 추가(정확 모드: 최소 3분)"):
    cookie_input = discord.ui.TextInput(label="cookie(.ROBLOSECURITY 또는 _|WARNING:…|_)", required=False, max_length=4000)
    id_input = discord.ui.TextInput(label="아이디", required=False, max_length=100)
    pw_input = discord.ui.TextInput(label="비밀번호", required=False, max_length=100)
    async def on_submit(self, interaction: Interaction):
        gid = interaction.guild.id
        await interaction.response.send_message(embed=Embed(title="", description="천천히 정확히 확인 중(최소 3분)…", colour=COLOR_BLACK), ephemeral=True)

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
            c_ok, c_amt, c_reason, c_shot = await robux_with_cookie(interaction.user.id, raw_cookie)
            if c_ok: ok, amount, reason, shot = True, c_amt, "ok", c_shot
            else: reason, shot = c_reason, c_shot

        if not ok and uid and pw:
            l_ok, l_amt, l_reason, l_shot = await robux_with_login(interaction.user.id, uid, pw)
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
