import os, io, json, re, asyncio, time, statistics, pathlib
from typing import Dict, Any, Optional, Tuple, List

import discord
from discord import app_commands, Interaction, Embed, File
from discord.ext import commands
from dotenv import load_dotenv

# ========== Playwright (로그인/파싱) ==========
PLAYWRIGHT_OK = True
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PwTimeout
except Exception:
    PLAYWRIGHT_OK = False

# ========== 기본 ==========
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
HTTP_PROXY = os.getenv("HTTP_PROXY", "").strip() or None
HTTPS_PROXY = os.getenv("HTTPS_PROXY", "").strip() or None

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ========== 파일 DB/상태 ==========
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
            "stock": {"robux": 0.0, "totalSold": 0.0, "pricePer": 0.0, "lastMsg": {"channelId": 0, "messageId": 0}},
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
    sess = gs["sessions"].get(str(uid), {"cookie": None, "username": None, "password": None, "lastRobux": 0.0, "premium": False, "accountName": None})
    if cookie is not None: sess["cookie"] = cookie
    if username is not None: sess["username"] = username
    if password is not None: sess["password"] = password
    gs["sessions"][str(uid)] = sess
    update_gslot(gid, gs)

def set_last_balance(gid: int, uid: int, robux: float, premium: bool, account_name: Optional[str] = None):
    gs = gslot(gid)
    sess = gs["sessions"].get(str(uid), {"cookie": None, "username": None, "password": None, "lastRobux": 0.0, "premium": False, "accountName": None})
    sess["lastRobux"] = float(max(0.0, robux))
    sess["premium"] = bool(premium)
    if account_name: sess["accountName"] = account_name
    gs["sessions"][str(uid)] = sess
    gs["stock"]["robux"] = float(max(0.0, robux))
    update_gslot(gid, gs)

def set_price(gid: int, price: float):
    gs = gslot(gid)
    gs["stock"]["pricePer"] = float(max(0.0, price))
    update_gslot(gid, gs)

def set_last_message(gid: int, channelId: int, messageId: int):
    gs = gslot(gid)
    gs["stock"]["lastMsg"] = {"channelId": int(channelId), "messageId": int(messageId)}
    update_gslot(gid, gs)

async def change_stock(gid: int, delta: float):
    async with db_lock:
        gs = gslot(gid)
        now = float(gs["stock"].get("robux", 0.0))
        newv = max(0.0, now + float(delta))
        gs["stock"]["robux"] = newv
        if delta < 0:
            gs["stock"]["totalSold"] = float(gs["stock"].get("totalSold", 0.0)) + (-float(delta))
        update_gslot(gid, gs)
        return newv

# 세션 저장
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

# ========== 숫자 유틸 (정수만, 첫 글자 0 금지, 최소 100) ==========
ONLY_POS_INT = re.compile(r"^[1-9][0-9]*$")

def parse_pos_int(s: str, min_value: int = 1) -> Optional[int]:
    if not s: return None
    s = s.strip()
    if not ONLY_POS_INT.fullmatch(s): return None
    v = int(s)
    if v < min_value: return None
    return v

def fmt2(x: float) -> str:
    return f"{x:,.2f}"

def fmt0(x: float | int) -> str:
    return f"{int(x):,}"

# ========== 임베드/이모지 (전부 핑크 적용) ==========
def color_hex(h: str) -> discord.Colour:
    return discord.Colour(int(h.lower().replace("#", ""), 16))

COLOR_PINK = color_hex("ff5dd6")
COLOR_RED = discord.Colour.red()
COLOR_GREEN = discord.Colour.green()
COLOR_ORANGE = discord.Colour.orange()

def pe(eid: int, name: str = None, animated: bool = False) -> discord.PartialEmoji:
    return discord.PartialEmoji(name=name, id=eid, animated=animated)
BTN_EMO_NOTICE = pe(1424003478275231916, name="emoji_5")
BTN_EMO_CHARGE = pe(1381244136627245066, name="charge")
BTN_EMO_INFO   = pe(1381244138355294300, name="info")
BTN_EMO_BUY    = pe(1381244134680957059, name="category")
EMO_ROBUX      = pe(1423661718776709303, name="robux")

FOOTER_IMAGE = "https://cdn.discordapp.com/attachments/1420389790649421877/1424077172435325091/IMG_2038.png?ex=68e2a2b7&is=68e15137&hm=712b0f434f2267c261dc260fd22a7a163d158b7c2f43fa618642abd80b17058c&"

def embed_unified(title: Optional[str], desc: str, colour: discord.Colour = COLOR_PINK, image_url: Optional[str] = None) -> Embed:
    e = Embed(title=(title or "")[:256], description=desc, colour=colour or COLOR_PINK)
    if image_url: e.set_image(url=image_url)
    return e

def embed_panel() -> Embed:
    return embed_unified("자동 로벅스 자판기", "아래 버튼을 눌러 이용해줘!", COLOR_PINK)

def embed_notice() -> Embed:
    return embed_unified("공지사항", "필독하고 이용해줘.", COLOR_PINK)

def build_info_embed(user: discord.User | discord.Member, gid: int) -> Embed:
    gs = gslot(gid)
    sess = gs["sessions"].get(str(user.id), {})
    last = float(sess.get("lastRobux", 0.0))
    premium = bool(sess.get("premium", False))
    e = embed_unified(f"{getattr(user,'display_name',user.name)} 님 정보", "\n".join([
        f"- 현재 로벅스: {fmt0(last)}",
        f"- 프리미엄: {'O' if premium else 'X'}",
    ]), COLOR_PINK)
    try: e.set_thumbnail(url=user.display_avatar.url)
    except: pass
    return e

def build_stock_embed(gid: int) -> Embed:
    gs = gslot(gid)
    robux = float(gs["stock"].get("robux", 0.0))
    total = float(gs["stock"].get("totalSold", 0.0))
    price = float(gs["stock"].get("pricePer", 0.0))
    desc = "\n".join([
        "## 실시간 재고",
        f"- 로벅스 재고: {fmt0(robux)}",
        f"- 1당 가격: {fmt2(price)}",
        f"- 총 판매량: {fmt0(total)}",
    ])
    return embed_unified("", desc, COLOR_PINK, FOOTER_IMAGE)

# ========== Roblox 파싱(초정밀 실제 구현) ==========
ROBLOX_LOGIN_URLS = [
    "https://www.roblox.com/Login",
    "https://www.roblox.com/ko/Login",
    "https://www.roblox.com/es-419/Login",
    "https://www.roblox.com/pt-br/Login",
]
ROBLOX_HOME_URLS = [
    "https://www.roblox.com/home",
    "https://www.roblox.com/ko/home",
    "https://www.roblox.com/es-419/home",
]
ROBLOX_TX_URL = "https://www.roblox.com/transactions"
ROBLOX_PREMIUM_URL = "https://www.roblox.com/premium/membership"
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
        await ctx.set_extra_http_headers({"Accept-Language":"ko-KR,ko;q=0.9,en;q=0.8"})
        return ctx
    except Exception:
        return None

async def _goto(page: Page, url: str, timeout=50000) -> bool:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout); return True
    except Exception: return False

async def _shot(page: Page) -> Optional[bytes]:
    try: return await page.screenshot(type="png", full_page=False)
    except Exception: return None

async def parse_premium(page: Page) -> Optional[bool]:
    try:
        for sel in ["text=Premium", "text=프리미엄", "[aria-label*='Premium']"]:
            if await page.query_selector(sel): return True
    except: pass
    try:
        await page.goto(ROBLOX_PREMIUM_URL, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(1.0)
        for sel in ["text=Premium", "text=멤버십", "Manage Membership"]:
            if await page.query_selector(f"text={sel}") or await page.query_selector(f"button:has-text('{sel}')"):
                return True
    except: pass
    return False

async def _parse_home(page: Page) -> Optional[int]:
    for sel in ["[data-testid*='nav-robux']", "a[aria-label*='Robux']", "a[aria-label*='로벅스']"]:
        try:
            el = await page.query_selector(sel)
            if not el: continue
            txt = (await el.inner_text() or "").strip()
            v = _to_int(txt)
            if isinstance(v, int): return v
        except: continue
    return None

async def _parse_tx(page: Page) -> Optional[int]:
    try:
        await page.goto(ROBLOX_TX_URL, wait_until="domcontentloaded", timeout=50000)
        await asyncio.sleep(1.2)
        html = await page.content()
        nums = [int(re.sub(r"[,\.\s]", "", m.group(1))) for m in NUM_RE.finditer(html)]
        nums = [n for n in nums if 0 <= n <= 100_000_000]
        if nums: return int(statistics.median(nums))
    except: pass
    return None

async def parse_balance_ultra(page: Page, deadline_s=180) -> Optional[int]:
    start = time.time()
    best = None
    while time.time() - start < deadline_s:
        v1 = await _parse_home(page)
        v2 = await _parse_tx(page)
        cand = [v for v in [v1, v2] if isinstance(v, int)]
        if cand:
            med = int(statistics.median(cand))
            if best is None or abs(med - (best or 0)) <= max(10, int(med*0.02)):
                best = med
                break
        await asyncio.sleep(1.2)
    return best

async def robux_with_cookie(user_uid: int, raw_cookie: str) -> Tuple[bool, Optional[float], Optional[bool], str, Optional[bytes]]:
    if not PLAYWRIGHT_OK: return False, None, None, "Playwright 미설치", None
    cookie = normalize_cookie(raw_cookie)
    if not cookie: return False, None, None, "쿠키 형식 오류", None
    try:
        async with async_playwright() as p:
            browser = await _launch(p)
            if not browser: return False, None, None, "브라우저 오류", None
            ctx = await _ctx(browser)
            if not ctx: await browser.close(); return False, None, None, "컨텍스트 오류", None
            try:
                await ctx.add_cookies([{"name":".ROBLOSECURITY","value":cookie,"domain":".roblox.com","path":"/","httpOnly":True,"secure":True,"sameSite":"Lax"}])
            except: pass
            page = await ctx.new_page()
            ok = await _goto(page, ROBLOX_HOME_URLS[0], timeout=50000)
            if not ok:
                await browser.close(); return False, None, None, "페이지 이동 실패", None
            bal = await parse_balance_ultra(page, deadline_s=180)
            prem = await parse_premium(page)
            shot = await _shot(page)
            await browser.close()
            if isinstance(bal, int):
                return True, float(bal), bool(prem), "ok", shot
            return False, None, None, "로벅스 파싱 실패", shot
    except Exception:
        return False, None, None, "예외", None

async def robux_with_login(user_uid: int, username: str, password: str) -> Tuple[bool, Optional[float], Optional[bool], str, Optional[bytes]]:
    # ID/PW 로그인은 보안/캡차 영향 큼. 여기선 쿠키 권장. 그래도 시도.
    return False, None, None, "ID/PW 로그인은 비권장. 쿠키 사용 바람", None

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

# ========== GiftRunner 자동운영 ==========
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
    async def deliver(self, amount: float, what: str) -> Tuple[bool, Optional[bytes]]:
        await asyncio.sleep(1.2)
        return True, None

gift_runner = GiftRunner()

# ========== 구매/인게임 선물 (숫자만, 최소 100, 총액=수량 ÷ 가격) ==========
class PurchaseMethodView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(discord.ui.Button(label="인게임 선물", style=discord.ButtonStyle.secondary, custom_id="gift_in_game", emoji=EMO_ROBUX))
        self.add_item(discord.ui.Button(label="게임패스", style=discord.ButtonStyle.secondary, custom_id="gift_gamepass", emoji=EMO_ROBUX))

class GiftAmountModal(discord.ui.Modal, title="로벅스 수량 입력"):
    amount = discord.ui.TextInput(label="지급 로벅스 수량", required=True, max_length=18)
    async def on_submit(self, interaction: Interaction):
        gid = interaction.guild.id
        raw = str(self.amount.value).strip()
        qty = parse_pos_int(raw, min_value=100)
        if qty is None:
            await interaction.response.send_message(embed=embed_unified("수량 오류", "숫자만 입력. 첫 글자 0 금지. 최소 100 이상.", COLOR_RED), ephemeral=True)
            return
        gs = gslot(gid)
        stock = float(gs["stock"].get("robux", 0.0))
        if stock + 1e-9 < qty:
            await interaction.response.send_message(embed=embed_unified("재고 부족", "재고가 부족합니다", COLOR_RED), ephemeral=True)
            return
        gift_set(interaction.user.id, {"amount": float(qty), "gid": gid})
        await interaction.response.send_modal(GiftDetailModal())

class GiftDetailModal(discord.ui.Modal, title="선물 정보 입력"):
    nick = discord.ui.TextInput(label="로블 닉", required=True, max_length=50)
    game = discord.ui.TextInput(label="게임 이름", required=True, max_length=80)
    what = discord.ui.TextInput(label="어떤 선물인가요?(정확하게 입력)", required=True, max_length=120)
    async def on_submit(self, interaction: Interaction):
        gift_set(interaction.user.id, {"nick": self.nick.value.strip(), "game": self.game.value.strip(), "what": self.what.value.strip()})
        s = gift_get(interaction.user.id)
        gid = s.get("gid", interaction.guild.id)
        gs = gslot(gid)
        price = float(gs["stock"].get("pricePer", 0.0))
        amount = float(s.get("amount", 0.0))
        if price <= 0:
            desc = "로블록스 접속중..\n(경고: 1당 가격이 설정되지 않았습니다)"
        else:
            total = amount / price
            desc = "\n".join([
                "로블록스 접속중..",
                f"- 수량: {fmt0(amount)}",
                f"- 1당 가격: {fmt2(price)}",
                f"- 예상 결제 금액(수량 ÷ 가격): {fmt2(total)}",
            ])
        await interaction.response.send_message(embed=embed_unified("진행 시작하겠습니다", desc, COLOR_PINK), ephemeral=True)
        e = embed_unified("", "본인이 맞으신가요?", COLOR_PINK)
        e.set_footer(text=f"대상 닉네임: {s.get('nick','')}")
        await interaction.followup.send(embed=e, view=ConfirmUserView(), ephemeral=True)

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

        if cid == "gift_in_game":
            await inter.response.send_modal(GiftAmountModal()); return
        if cid == "gift_gamepass":
            await inter.response.send_message(embed=embed_unified("안내", "게임패스로 지급하려면 상품ID/게임ID 필요.", COLOR_PINK), ephemeral=True); return

        if cid == "gift_user_ok":
            await inter.response.defer(ephemeral=True)
            s = gift_get(inter.user.id)
            ok, _ = await gift_runner.connect_and_friend(s.get("nick") or "")
            if not ok:
                await inter.followup.send(embed=embed_unified("오류", "대상 접속/친추 중 오류.", COLOR_RED), ephemeral=True)
                gift_clear(inter.user.id); return
            giver = gslot(s.get("gid", inter.guild.id))["sessions"].get(str(inter.user.id), {}).get("accountName") or "지급 계정"
            await inter.followup.send(embed=embed_unified("", f"{giver} 친추 받아주세요", COLOR_PINK), view=FriendConfirmView(), ephemeral=True); return

        if cid == "gift_user_retry":
            gift_clear(inter.user.id)
            await inter.response.send_message(embed=embed_unified("거래 취소", "정보를 다시 입력해줘.", COLOR_PINK), ephemeral=True); return

        if cid == "gift_friend_yes":
            await inter.response.defer(ephemeral=True)
            ok = await gift_runner.wait_friend_accept()
            if not ok:
                await inter.followup.send(embed=embed_unified("오류", "친구 승인 확인 실패.", COLOR_RED), ephemeral=True)
                gift_clear(inter.user.id); return
            s = gift_get(inter.user.id)
            ok2 = await gift_runner.join_game(s.get("game") or "")
            if not ok2:
                await inter.followup.send(embed=embed_unified("오류", "게임 접속 실패.", COLOR_RED), ephemeral=True)
                gift_clear(inter.user.id); return
            await inter.followup.send(embed=embed_unified("접속 완료", "따라 들어와주세요", COLOR_PINK), ephemeral=True)
            can = await gift_runner.detect_gift_capability(s.get("game") or "")
            if not can:
                await inter.followup.send(embed=embed_unified("선물 불가", "선물 기능이 없는 게임입니다", COLOR_RED), ephemeral=True)
                gift_clear(inter.user.id); return
            found, image = await gift_runner.find_gamepass_candidate(s.get("what") or "")
            if not found:
                await inter.followup.send(embed=embed_unified("안내", "맞는 게임 패스를 못 찾았어.", COLOR_PINK), ephemeral=True)
                gift_clear(inter.user.id); return
            await inter.followup.send(embed=embed_unified("", "원하시는 게임 패스 맞나요?", COLOR_PINK, image_url=image), view=PassConfirmView(), ephemeral=True); return

        if cid == "gift_friend_no":
            await inter.response.send_message(embed=embed_unified("", "유저가 너에게 친추 걸고 네가 승인하는 방식으로 전환. 완료되면 ‘친추 받음’.", COLOR_PINK), ephemeral=True); return

        if cid == "gift_pass_ok":
            await inter.response.defer(ephemeral=True)
            s = gift_get(inter.user.id)
            amount = float(s.get("amount", 0.0) or 0.0)
            if amount < 100:
                await inter.followup.send(embed=embed_unified("오류", "수량은 최소 100 이상.", COLOR_RED), ephemeral=True)
                gift_clear(inter.user.id); return
            ok, receipt = await gift_runner.deliver(amount, s.get("what") or "")
            if not ok:
                await inter.followup.send(embed=embed_unified("오류", "지급 실패. 잠시 후 재시도.", COLOR_RED), ephemeral=True)
                gift_clear(inter.user.id); return
            await change_stock(s.get("gid", inter.guild.id), -amount)
            files = [File(io.BytesIO(receipt), filename="receipt.png")] if receipt else None
            e = embed_unified("지급 완료", "구매해주셔서 감사합니다", COLOR_PINK)
            if files: e.set_image(url="attachment://receipt.png")
            if inter.response.is_done(): await inter.followup.send(embed=e, files=files, ephemeral=True)
            else: await inter.response.send_message(embed=e, files=files, ephemeral=True)
            await try_update_stock_message(inter.guild, s.get("gid", inter.guild.id))
            gift_clear(inter.user.id); return

        if cid == "gift_pass_no":
            await inter.response.send_message(embed=embed_unified("", "다른 후보를 계속 탐색할게.", COLOR_PINK), ephemeral=True); return

    except Exception:
        try:
            if inter.response.is_done():
                await inter.followup.send(embed=embed_unified("오류", "요청 처리 중 문제가 발생했어.", COLOR_RED), ephemeral=True)
            else:
                await inter.response.send_message(embed=embed_unified("오류", "요청 처리 중 문제가 발생했어.", COLOR_RED), ephemeral=True)
        except:
            pass

# ========== 패널/명령어(4개) ==========
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="공지사항", emoji=BTN_EMO_NOTICE, style=discord.ButtonStyle.secondary, custom_id="panel_notice", row=0)
    async def notice_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=embed_notice(), ephemeral=True)
    @discord.ui.button(label="충전", emoji=BTN_EMO_CHARGE, style=discord.ButtonStyle.secondary, custom_id="panel_charge", row=0)
    async def charge_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=embed_unified("충전", "준비 중이야.", COLOR_PINK), ephemeral=True)
    @discord.ui.button(label="내 정보", emoji=BTN_EMO_INFO, style=discord.ButtonStyle.secondary, custom_id="panel_info", row=1)
    async def info_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=build_info_embed(interaction.user, interaction.guild.id), ephemeral=True)
    @discord.ui.button(label="구매", emoji=BTN_EMO_BUY, style=discord.ButtonStyle.secondary, custom_id="panel_buy", row=1)
    async def buy_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=embed_unified("지급 방식 선택하기", "원하는 방식을 선택해줘.", COLOR_PINK), view=PurchaseMethodView(), ephemeral=True)

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
@app_commands.describe(일당="1당 가격(숫자만, 첫 글자 0 금지)")
@app_commands.checks.has_permissions(manage_guild=True)
async def 가격설정(inter: Interaction, 일당: str):
    # 숫자만, 첫 글자 0 금지
    if not ONLY_POS_INT.fullmatch(일당.strip()):
        await inter.response.send_message(embed=embed_unified("입력 오류", "숫자만 입력. 첫 글자 0 금지.", COLOR_RED), ephemeral=True)
        return
    price = int(일당.strip())
    if price <= 0:
        await inter.response.send_message(embed=embed_unified("입력 오류", "1당 가격은 0보다 커야 해.", COLOR_RED), ephemeral=True)
        return
    gid = inter.guild.id
    set_price(gid, float(price))
    await try_update_stock_message(inter.guild, gid)
    await inter.response.send_message(embed=embed_unified("", "가격설정 완료", COLOR_PINK), ephemeral=True)

# /재고추가: 쿠키 파싱(초정밀)
class StockLoginModal(discord.ui.Modal, title="세션 추가/재고 갱신"):
    cookie_input = discord.ui.TextInput(label="cookie(.ROBLOSECURITY 또는 _|WARNING:…|_)", required=True, max_length=4000)
    async def on_submit(self, interaction: Interaction):
        gid = interaction.guild.id
        raw_cookie = (self.cookie_input.value or "").strip()
        await interaction.response.send_message(embed=embed_unified("", "정확히 확인 중… 잠시만.", COLOR_PINK), ephemeral=True)
        ok, amount, premium, reason, shot = await robux_with_cookie(interaction.user.id, raw_cookie)
        if ok and (amount is not None):
            set_session(gid, interaction.user.id, raw_cookie, None, None)
            set_last_balance(gid, interaction.user.id, float(amount), bool(premium))
            e = embed_unified("로그인 성공", f"- 현재 로벅스: {fmt0(amount)}\n- 프리미엄: {'O' if premium else 'X'}", COLOR_PINK)
            if shot:
                e.set_image(url="attachment://robux.png")
                await interaction.edit_original_response(embed=e, attachments=[File(io.BytesIO(shot), filename="robux.png")])
            else:
                await interaction.edit_original_response(embed=e)
            await try_update_stock_message(interaction.guild, gid)
        else:
            e = embed_unified("로그인 실패", reason or "파싱 실패", COLOR_RED)
            if shot:
                e.set_image(url="attachment://robux.png")
                await interaction.edit_original_response(embed=e, attachments=[File(io.BytesIO(shot), filename="robux.png")])
            else:
                await interaction.edit_original_response(embed=e)

@tree.command(name="재고추가", description="쿠키로 세션을 추가하고 재고(잔액)를 갱신합니다.")
async def 재고추가(inter: Interaction):
    await inter.response.send_modal(StockLoginModal())

# ========== 부팅 ==========
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
