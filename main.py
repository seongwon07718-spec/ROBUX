import os
import io
import json
import re
import shutil
import asyncio
from typing import Any, Dict, Optional, Tuple, List

import discord
from discord import app_commands, Interaction, Embed, File
from discord.ext import commands, tasks
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# ===== .env 강제 로드 =====
def _force_load_env() -> Dict[str, Any]:
    try:
        from dotenv import load_dotenv, dotenv_values, find_dotenv
    except Exception:
        print("[ENV] python-dotenv 미설치. pip install python-dotenv")
        return {"loaded": False, "path": None}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [os.path.join(script_dir, ".env"), os.path.join(os.getcwd(), ".env")]
    used = None
    for p in candidates:
        if os.path.exists(p):
            load_dotenv(dotenv_path=p, override=True)
            used = p
            break
    if not used:
        found = find_dotenv(usecwd=True)
        if found:
            load_dotenv(found, override=True)
            used = found
    tok = os.getenv("DISCORD_TOKEN"); gid = os.getenv("GUILD_ID")
    print(f"[ENV] path={used} token_len={0 if tok is None else len(tok)} guild_id={gid}")
    return {"loaded": bool(tok), "path": used}
_env = _force_load_env()

# ===== 기본 데이터 =====
DATA_PATH = "data.json"
def _atomic_write(path: str, data: Dict[str, Any]):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    shutil.move(tmp, path)

def _default_data():
    return {
        "users": {},  # userId: {wallet,total,count,recent[], roblox{cookie,username,password}}
        "stats": {"total_sold": 0},
        "cache": {"balances": {}},
        "meta": {"version": 3}
    }

def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_PATH):
        d = _default_data(); _atomic_write(DATA_PATH, d); return d
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        d = _default_data(); _atomic_write(DATA_PATH, d); return d

def save_data(d: Dict[str, Any]): _atomic_write(DATA_PATH, d)

def _ensure_user(uid: int) -> Dict[str, Any]:
    d = load_data()
    u = d["users"].get(str(uid))
    if not u:
        u = {"wallet": 0, "total": 0, "count": 0, "recent": [], "roblox": {}}
        d["users"][str(uid)] = u
        save_data(d)
    return u

def update_user_stats(uid: int, amount: int, desc: str):
    d = load_data()
    u = d["users"].setdefault(str(uid), {"wallet": 0, "total": 0, "count": 0, "recent": [], "roblox": {}})
    u["wallet"] = max(0, int(u.get("wallet", 0) + amount))
    if amount > 0:
        u["total"] = int(u.get("total", 0) + amount)
    u["count"] = int(u.get("count", 0) + 1)
    recent = u.get("recent", [])
    recent.insert(0, {"desc": desc, "amount": int(amount), "ts": int(asyncio.get_event_loop().time())})
    u["recent"] = recent[:5]
    d["users"][str(uid)] = u
    save_data(d)

def get_user_stats(uid: int) -> Dict[str, Any]:
    return _ensure_user(uid)

def set_user_cookie(uid: int, cookie: str, username_hint: Optional[str] = None):
    d = load_data(); u = d["users"].setdefault(str(uid), {"wallet":0,"total":0,"count":0,"recent":[], "roblox":{}})
    r = u.get("roblox", {})
    r["cookie_raw"] = cookie
    if username_hint: r["username"] = username_hint
    u["roblox"] = r; d["users"][str(uid)] = u; save_data(d)

def set_user_login(uid: int, username: str, password: str):
    d = load_data(); u = d["users"].setdefault(str(uid), {"wallet":0,"total":0,"count":0,"recent":[], "roblox":{}})
    r = u.get("roblox", {})
    r["username"] = username; r["password"] = password
    u["roblox"] = r; d["users"][str(uid)] = u; save_data(d)

def get_total_sold() -> int:
    d = load_data(); return int(d.get("stats", {}).get("total_sold", 0))

def cache_balance(uid: int, value: int):
    d = load_data()
    d["cache"].setdefault("balances", {})
    d["cache"]["balances"][str(uid)] = {"value": int(value), "ts": float(asyncio.get_event_loop().time())}
    save_data(d)

def get_cached_balance(uid: int, ttl: int) -> Optional[int]:
    d = load_data()
    item = d.get("cache", {}).get("balances", {}).get(str(uid))
    if not item: return None
    if (float(asyncio.get_event_loop().time()) - float(item["ts"])) <= ttl:
        return int(item["value"])
    return None

TOKEN = os.getenv("DISCORD_TOKEN") or ""
try:
    GUILD_ID = int(os.getenv("GUILD_ID") or "0")
except Exception:
    GUILD_ID = 0
    print("[ENV][WARN] GUILD_ID 파싱 실패 → 전역 등록")

# ===== 이미지(임베드 IMAGE) =====
IMAGE_MODE = "url"  # 필요시 "attach_local" + stock.png
STOCK_IMAGE_URL = "https://cdn.discordapp.com/attachments/1420389790649421877/1423898721036271718/IMG_2038.png"
LOCAL_IMAGE_PATH = "stock.png"

# ===== Roblox =====
ROBLOX_HOME_URLS = ["https://www.roblox.com/ko/home", "https://www.roblox.com/home"]
ROBLOX_LOGIN_URLS = ["https://www.roblox.com/ko/Login", "https://www.roblox.com/Login"]
BALANCE_CACHE_TTL_SEC = 15
PAGE_TIMEOUT = 25000
UPDATE_INTERVAL_SEC = 60
LOGIN_RETRY = 3
NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

# ===== Playwright =====
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

# ===== Roblox 파싱(홈 우상단 뱃지, 정확) =====
ROBLOX_BADGE_SELECTORS: List[str] = [
    "[data-testid*='nav-robux']",
    "a[aria-label*='Robux']",
    "a[aria-label*='로벅스']",
    "span[title*='Robux']",
    "span[title*='로벅스']",
]

async def _goto_any(page: Page, urls: List[str]) -> bool:
    for u in urls:
        try:
            await page.goto(u, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            return True
        except Exception:
            continue
    return False

async def _wait_nav_ready(page: Page):
    for sel in ROBLOX_BADGE_SELECTORS:
        try:
            await page.wait_for_selector(sel, timeout=PAGE_TIMEOUT)
            return
        except Exception:
            continue
    await asyncio.sleep(1.5)

async def _extract_robux_badge(page: Page) -> Optional[int]:
    for sel in ROBLOX_BADGE_SELECTORS:
        try:
            el = await page.query_selector(sel)
            if not el: continue
            txt = (await el.inner_text() or "").strip()
            m = NUM_RE.search(txt)
            if not m: continue
            v = int(re.sub(r"[,\.\s]", "", m.group(1)))
            if 0 <= v <= 100_000_000:
                return v
        except Exception:
            continue
    try:
        html = await page.content()
        around = []
        for kw in ["Robux","로벅스"]:
            for m in re.finditer(kw, html, flags=re.IGNORECASE):
                s = max(0, m.start()-100); e = min(len(html), m.end()+100)
                around.append(html[s:e])
        nums = []
        for chunk in around:
            for m in re.finditer(NUM_RE, chunk):
                v = int(re.sub(r"[,\.\s]", "", m.group(1)))
                if 0 <= v <= 100_000_000: nums.append(v)
        if nums: return min(nums)
    except Exception:
        pass
    return None

async def _open_with_cookie_home(context: BrowserContext, cookie_raw: str) -> Optional[int]:
    try:
        await context.add_cookies([{"name":".ROBLOSECURITY","value":cookie_raw,"domain":".roblox.com","path":"/","httpOnly":True,"secure":True,"sameSite":"Lax"}])
        page = await context.new_page()
        ok = await _goto_any(page, ROBLOX_HOME_URLS)
        if not ok:
            await page.close(); return None
        await _wait_nav_ready(page)
        bal = await _extract_robux_badge(page)
        await page.close()
        return bal
    except Exception:
        return None

async def _login_with_idpw_home(context: BrowserContext, username: str, password: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    ok, bal, cookie_val, username_hint = False, None, None, None
    page = await context.new_page()
    try:
        got = await _goto_any(page, ROBLOX_LOGIN_URLS)
        if not got:
            await page.close(); return False, None, None, None
        user_sel = "input[name='username'], input#login-username, input[type='text']"
        pass_sel = "input[name='password'], input#login-password, input[type='password']"
        await page.wait_for_selector(user_sel, timeout=PAGE_TIMEOUT); await page.fill(user_sel, username)
        await page.wait_for_selector(pass_sel, timeout=PAGE_TIMEOUT); await page.fill(pass_sel, password)
        login_btn = "button[type='submit'], button[aria-label], button:has-text('로그인'), button:has-text('Log In')"
        await page.click(login_btn)
        try: await page.wait_for_load_state("domcontentloaded", timeout=PAGE_TIMEOUT)
        except Exception: pass
        ok_home = await _goto_any(page, ROBLOX_HOME_URLS)
        if not ok_home:
            await page.close(); return False, None, None, None
        await _wait_nav_ready(page)
        bal = await _extract_robux_badge(page)
        for c in await context.cookies():
            if c.get("name") == ".ROBLOSECURITY":
                cookie_val = c.get("value"); break
        try:
            t = await page.title()
            if t:
                m = re.search(r"[A-Za-z0-9_]{3,20}", t)
                if m: username_hint = m.group(0)
        except Exception: pass
        ok = bal is not None
        return ok, bal, cookie_val, username_hint
    finally:
        await page.close()

async def fetch_balance(uid: int) -> int:
    cached = get_cached_balance(uid, BALANCE_CACHE_TTL_SEC)
    if cached is not None:
        return int(cached)
    info = get_user_stats(uid).get("roblox", {})
    cookie_raw, username, password = info.get("cookie_raw"), info.get("username"), info.get("password")
    for _ in range(LOGIN_RETRY):
        try:
            async with async_playwright() as p:
                browser = await launch_browser(p)
                if not browser: continue
                context = await new_context(browser)
                if not context: await browser.close(); continue
                if cookie_raw:
                    bal = await _open_with_cookie_home(context, cookie_raw); await browser.close()
                    if isinstance(bal, int): cache_balance(uid, bal); return int(bal)
                if username and password:
                    ok, bal, new_cookie, uname_hint = await _login_with_idpw_home(context, username, password)
                    await browser.close()
                    if ok and isinstance(bal, int):
                        if new_cookie: set_user_cookie(uid, new_cookie, uname_hint)
                        cache_balance(uid, bal); return int(bal)
                else:
                    await browser.close()
        except Exception:
            continue
    return 0

# ===== 이미지 유틸 =====
async def fetch_image_bytes(url: str, timeout: int = 10) -> Optional[bytes]:
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None

# ===== 임베드 =====
def _author(emb: Embed, guild: Optional[discord.Guild]):
    if guild:
        icon = guild.icon.url if guild.icon else None
        emb.set_author(name=guild.name, icon_url=icon)

def make_stock_embed(guild: Optional[discord.Guild], robux_balance: int, total_sold: int, image_as_attachment: bool) -> Embed:
    emb = Embed(title="", colour=discord.Colour(int("ff5dd6", 16)))
    _author(emb, guild)
    stock = f"{robux_balance:,}"; total = f"{total_sold:,}"
    emb.description = "\n".join([
        "### <a:upuoipipi:1423892277373304862>실시간 로벅스 재고",
        "### <a:thumbsuppp:1423892279612936294>로벅스 재고",
        f"<a:sakfnmasfagfamg:1423892278677602435>**`{stock}`로벅스**",
        "### <a:thumbsuppp:1423892279612936294>총 판매량",
        f"<a:sakfnmasfagfamg:1423892278677602435>**`{total}`로벅스**",
    ])
    if image_as_attachment: emb.set_image(url="attachment://stock.png")
    else: emb.set_image(url=STOCK_IMAGE_URL.strip())
    return emb

def make_panel_embed(guild: Optional[discord.Guild]) -> Embed:
    emb = Embed(title="", colour=discord.Colour(int("ff5dd6", 16)))
    _author(emb, guild)
    emb.description = "## 24시간 자동 자판기\n**아래 원하시는 버튼을 눌려 이용해주세요**"
    return emb

def make_notice_embed(guild: Optional[discord.Guild]) -> Embed:
    emb = Embed(title="", colour=discord.Colour.dark_grey(), description="<#1419230737244229653> 필독 부탁드립니다")
    _author(emb, guild)
    return emb

def make_myinfo_embed(user: discord.User | discord.Member, stats: Dict[str, Any]) -> Embed:
    emb = Embed(title=f"{user.display_name}님 정보", colour=discord.Colour(int("ff5dd6", 16)))
    emb.description = "\n".join([
        f"### 보유 금액 : {int(stats.get('wallet',0)):,}",
        f"### 누적 금액 : {int(stats.get('total',0)):,}",
        f"### 거래 횟수 : {int(stats.get('count',0)):,}",
        "",
        "최근 거래내역 5개"
    ])
    if user.display_avatar:
        emb.set_thumbnail(url=user.display_avatar.url)
    return emb

# ===== 디스코드 봇/명령 =====
INTENTS = discord.Intents.default()
INTENTS.message_content = False
BOT = commands.Bot(command_prefix="!", intents=INTENTS)
TREE = BOT.tree

# PartialEmoji
def pe(id_str: str, name: str = None, animated: bool = False) -> discord.PartialEmoji:
    return discord.PartialEmoji(name=name, id=int(id_str), animated=animated)
EMOJI_ACC     = pe("1423544323735027763", name="Acc",     animated=False)
EMOJI_CARD    = pe("1423544325597560842", name="Card",    animated=True)
EMOJI_DISCORD = pe("1423517142556610560", name="discord", animated=False)
EMOJI_GREEN   = pe("1423939286817837090", name="Green_dot", animated=True)

class TransactionsSelect(discord.ui.Select):
    def __init__(self, entries: List[Dict[str, Any]]):
        options = []
        if entries:
            for i, e in enumerate(entries):
                label = f"{e.get('desc','거래')} / {int(e.get('amount',0)):,}"
                options.append(discord.SelectOption(label=label[:100], value=str(i)))
        else:
            options = [discord.SelectOption(label="거래 내역 없음", value="none", default=True)]
        super().__init__(placeholder="거래내역 보기", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: Interaction):
        try:
            await interaction.response.defer_update()
        except Exception:
            pass

class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="공지사항", emoji=EMOJI_ACC,     custom_id="p_notice", row=0))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="충전",   emoji=EMOJI_CARD,    custom_id="p_charge", row=0))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="내 정보", emoji=EMOJI_DISCORD, custom_id="p_me",     row=1))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="구매",   emoji=EMOJI_GREEN,   custom_id="p_buy",    row=1))
    async def interaction_check(self, interaction: Interaction) -> bool:
        try:
            await interaction.response.defer_update()
        except Exception:
            pass
        cid = interaction.data.get("custom_id") if interaction.data else None
        try:
            if cid == "p_notice":
                await interaction.followup.send(embed=make_notice_embed(interaction.guild), ephemeral=True)
            elif cid == "p_me":
                stats = get_user_stats(interaction.user.id)
                view = discord.ui.View(timeout=None)
                view.add_item(TransactionsSelect(stats.get("recent", [])))
                await interaction.followup.send(embed=make_myinfo_embed(interaction.user, stats), view=view, ephemeral=True)
            elif cid == "p_charge":
                update_user_stats(interaction.user.id, amount=1000, desc="충전")
                stats = get_user_stats(interaction.user.id)
                view = discord.ui.View(timeout=None)
                view.add_item(TransactionsSelect(stats.get("recent", [])))
                await interaction.followup.send(content="충전 완료!", embed=make_myinfo_embed(interaction.user, stats), view=view, ephemeral=True)
            elif cid == "p_buy":
                update_user_stats(interaction.user.id, amount=-500, desc="구매")
                stats = get_user_stats(interaction.user.id)
                view = discord.ui.View(timeout=None)
                view.add_item(TransactionsSelect(stats.get("recent", [])))
                await interaction.followup.send(content="구매 처리 완료!", embed=make_myinfo_embed(interaction.user, stats), view=view, ephemeral=True)
        except Exception as e:
            print("[BTN] error:", e)
        return False

@TREE.command(name="실시간_재고_설정", description="쿠키/로그인 저장 후 결과를 '나만 보이게' 즉시 표시합니다.")
@app_commands.describe(mode="cookie 또는 login", cookie=".ROBLOSECURITY 값", id="Roblox 아이디", pw="Roblox 비밀번호")
async def cmd_setup(inter: Interaction, mode: str, cookie: Optional[str] = None, id: Optional[str] = None, pw: Optional[str] = None):
    mode = (mode or "").lower().strip()
    if mode not in ("cookie","login"):
        await inter.response.send_message("mode는 cookie 또는 login이야.", ephemeral=True); return
    if mode == "cookie":
        if not cookie:
            await inter.response.send_message("cookie(.ROBLOSECURITY) 값이 필요해.", ephemeral=True); return
        set_user_cookie(inter.user.id, cookie)
        bal = await fetch_balance(inter.user.id)  # 바로 파싱
        emb = Embed(title="연동 완료", description=f"현재 잔액: {bal:,} 로벅스", colour=discord.Colour.green())
        await inter.response.send_message(embed=emb, ephemeral=True)  # 즉시
        return
    # login 모드: 즉시 한 번 보내고 → 그 메시지를 편집
    await inter.response.send_message(embed=Embed(title="로그인 처리중...", description="잠시만 기다려줘.", colour=discord.Colour.blurple()), ephemeral=True)
    async def task():
        set_user_login(inter.user.id, id or "", pw or "")
        tried_ok, bal_value = False, 0
        try:
            async with async_playwright() as p:
                browser = await launch_browser(p)
                if browser:
                    ctx = await new_context(browser)
                    if ctx:
                        for _ in range(LOGIN_RETRY):
                            ok, bal, new_cookie, uname_hint = await _login_with_idpw_home(ctx, id or "", pw or "")
                            if ok and isinstance(bal, int):
                                tried_ok = True; bal_value = bal
                                if new_cookie: set_user_cookie(inter.user.id, new_cookie, uname_hint)
                                break
                    await browser.close()
        except Exception as e:
            print("[SETUP] err:", e)
        if tried_ok:
            emb = Embed(title="로그인 완료", description=f"현재 잔액: {bal_value:,} 로벅스", colour=discord.Colour.green())
        else:
            emb = Embed(title="로그인 실패", description="2FA/장치인증 가능성. 쿠키 방식 추천.", colour=discord.Colour.red())
        try:
            await inter.edit_original_response(embed=emb)
        except Exception:
            await inter.followup.send(embed=emb, ephemeral=True)
    asyncio.create_task(task())

@TREE.command(name="재고표시", description="실시간 로벅스 재고 임베드를 공개로 바로 표시합니다.")
async def cmd_show(inter: Interaction):
    bal = await fetch_balance(inter.user.id)
    total = get_total_sold()
    image_as_attachment = (IMAGE_MODE == "attach_local")
    file: Optional[File] = None
    if image_as_attachment:
        if os.path.exists(LOCAL_IMAGE_PATH):
            file = File(fp=LOCAL_IMAGE_PATH, filename="stock.png")
        else:
            img = await fetch_image_bytes(STOCK_IMAGE_URL)
            if img: file = File(io.BytesIO(img), filename="stock.png")
    emb = make_stock_embed(inter.guild, bal, total, image_as_attachment)
    await inter.response.send_message(embed=emb, file=file if file else discord.utils.MISSING, ephemeral=False)

@TREE.command(name="버튼패널", description="24시간 자동 자판기 패널을 공개로 바로 표시합니다.")
async def cmd_panel(inter: Interaction):
    emb = make_panel_embed(inter.guild)
    view = PanelView()
    await inter.response.send_message(embed=emb, view=view, ephemeral=False)

# ===== 자동 갱신(옵션) =====
active_updates: Dict[str, Dict[str, Any]] = {}
@tasks.loop(seconds=UPDATE_INTERVAL_SEC)
async def updater_loop():
    for uid, loc in list(active_updates.items()):
        try:
            user_id = int(uid)
            ch = await BOT.fetch_channel(loc["channel_id"])
            msg = await ch.fetch_message(loc["message_id"])
            bal = await fetch_balance(user_id); total = get_total_sold()
            use_attach = loc.get("use_attachment", IMAGE_MODE == "attach_local")
            emb = make_stock_embed(getattr(msg, "guild", None), bal, total, image_as_attachment=use_attach)
            if use_attach and os.path.exists(LOCAL_IMAGE_PATH):
                await msg.edit(embed=emb, attachments=[File(fp=LOCAL_IMAGE_PATH, filename="stock.png")])
            else:
                await msg.edit(embed=emb)
        except Exception:
            continue

# ===== 동기화/부팅 =====
async def sync_tree(force_guild: Optional[int] = None):
    try:
        if force_guild:
            await TREE.sync(guild=discord.Object(id=force_guild))
            print(f"[SYNC] guild {force_guild} sync ok")
        else:
            await TREE.sync()
            print("[SYNC] global sync ok")
    except Exception as e:
        print(f"[SYNC] sync error: {e}")

@BOT.event
async def on_ready():
    load_data()
    print(f"Logged in as {BOT.user}")
    print(f"[ENV] guild_id={GUILD_ID}")
    if GUILD_ID: await sync_tree(GUILD_ID)
    else: await sync_tree(None)
    async def delayed():
        await asyncio.sleep(30)
        if GUILD_ID: await sync_tree(GUILD_ID)
        else: await sync_tree(None)
        await asyncio.sleep(60)
        if GUILD_ID: await sync_tree(GUILD_ID)
    BOT.loop.create_task(delayed())

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN 비어있거나 형식 이상. .env 확인.")
    BOT.run(TOKEN)

if __name__ == "__main__":
    main()
