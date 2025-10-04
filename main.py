import os, json, threading, time, base64, sys, asyncio, re, contextlib
import discord
from discord import app_commands
from discord.ext import commands

# ===== 강제 디버그 로그(경고/정보 보이게) =====
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("robux-stock")

def LOG(msg): print(msg, flush=True)

# ===== 고정 환경 =====
GUILD_ID = 1419200424636055592
INTENTS = discord.Intents.default()
INTENTS.guilds = True  # 길드 목록 보이게
GRAY = discord.Color.from_str("#808080")

APP_ID = os.getenv("DISCORD_APP_ID", "").strip()
TOKEN  = os.getenv("DISCORD_TOKEN", "").strip()

# ===== Bot: application_id 필수 =====
def _as_int(x: str) -> int:
    try: return int(x)
    except: return 0

bot = commands.Bot(
    command_prefix="!",
    intents=INTENTS,
    application_id=_as_int(APP_ID)
)

# ===== DB =====
DB_PATH = "stock_data.json"
_db_lock = threading.Lock()

def load_db():
    if not os.path.exists(DB_PATH):
        return {"guilds": {}}
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"guilds": {}}

def save_db():
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(DB, f, ensure_ascii=False, indent=2)

DB = load_db()

def slot(gid: int):
    DB["guilds"].setdefault(str(gid), {
        "inventory": 0,
        "totalSold": 0,
        "lastMessage": {"channelId": 0, "messageId": 0},
        "account": {"idEnc":"", "pwEnc":"", "cookies":[], "cookiesAt":0, "optionsApplied": True}
    })
    return DB["guilds"][str(gid)]

def now(): return int(time.time())

# ===== 테스트용 인코딩 =====
def enc(s: str) -> str: return base64.b64encode((s or "").encode()).decode()
def dec(s: str) -> str:
    try: return base64.b64decode((s or "").encode()).decode()
    except: return ""

# ===== 권한 =====
def is_admin():
    async def pred(inter: discord.Interaction):
        if not inter.guild:
            await inter.response.send_message("길드에서만 사용 가능해.", ephemeral=True); return False
        if inter.user.guild_permissions.manage_guild: return True
        await inter.response.send_message("관리자만 사용 가능해.", ephemeral=True); return False
    return app_commands.check(pred)

# ===== 임베드 =====
def build_stock_embed(inv: int, sold: int) -> discord.Embed:
    desc = (
        "**로벅스 수량**\n"
        f"`{inv}`로벅스\n"
        "——————————\n"
        "**총 판매량**\n"
        f"`{sold}`로벅스\n"
        "——————————\n"
        "[로벅스 구매 바로가기](https://discord.com/channels/1419200424636055592/1419235238512427083)"
    )
    return discord.Embed(title="실시간 로벅스 재고", description=desc, color=GRAY)

# ===== Playwright 준비 =====
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, TimeoutError as PwTimeout
    PLAYWRIGHT_AVAILABLE = True
except Exception as e:
    LOG(f"[warn] Playwright import 실패: {e}")

# 일부 환경 child watcher 방어
try:
    if sys.platform != "win32" and hasattr(asyncio, "get_child_watcher"):
        try: asyncio.get_child_watcher()
        except NotImplementedError:
            from asyncio import SafeChildWatcher, set_child_watcher
            set_child_watcher(SafeChildWatcher())
except Exception as e:
    LOG(f"[warn] child_watcher 설정 스킵: {e}")

# ===== 로블록스 URL/셀렉터 =====
LOGIN_URL = "https://www.roblox.com/vi/Login"
TX_URL    = "https://www.roblox.com/ko/transactions"

SEL_ID      = "input#login-username, input[name='username'], input[type='text']"
SEL_PW      = "input#login-password, input[name='password'], input[type='password']"
SEL_LOGIN   = "button#login-button, button[type='submit'], button:has-text('로그인'), button:has-text('Đăng nhập')"

RE_BAL = re.compile(r"([0-9][0-9,\.]*)")
LAUNCH_KW = dict(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])

async def roblox_login_and_get_balance(enc_id: str, enc_pw: str) -> tuple[bool, int, str]:
    if not PLAYWRIGHT_AVAILABLE:
        return False, 0, "자동화 모듈 미설치"
    ID = dec(enc_id); PW = dec(enc_pw)
    if not ID or not PW:
        return False, 0, "계정 정보 오류"

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(**LAUNCH_KW)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121 Safari/537.36"
        )
        page = await context.new_page()
        try:
            await page.goto(LOGIN_URL, timeout=25000)
            await page.wait_for_timeout(700)

            id_el = await page.query_selector(SEL_ID) or (await page.query_selector_all("input"))[0]
            if not id_el: return False, 0, "ID 입력칸 없음"
            await id_el.fill(ID)

            pw_el = await page.query_selector(SEL_PW) or (await page.query_selector_all("input[type='password']"))[0]
            if not pw_el: return False, 0, "PW 입력칸 없음"
            await pw_el.fill(PW)

            btn = await page.query_selector(SEL_LOGIN) or await page.query_selector("button")
            if not btn: return False, 0, "로그인 버튼 없음"
            await btn.click()

            await page.wait_for_timeout(1800)
            html = await page.content()
            if any(k in html.lower() for k in ["hcaptcha","recaptcha","two-step","mfa","verify"]):
                return False, 0, "보안 인증 발생(캡차/2FA)"

            await page.goto(TX_URL, timeout=25000)
            await page.wait_for_timeout(1200)
            html2 = await page.content()

            bal = None
            for pat in [r"(내\s*잔액|balance|robux)\D+([0-9][0-9,\.]*)", r"([0-9][0-9,\.]*)\s*(robux|rbx)"]:
                m = re.search(pat, html2, re.IGNORECASE)
                if m:
                    cand = m.group(2) if (m.lastindex and m.lastindex >= 2) else m.group(1)
                    cand = cand.replace(",", "").replace(".", "")
                    if cand.isdigit():
                        bal = int(cand); break
            if bal is None:
                nums = [n.replace(",", "").replace(".", "") for n in re.findall(RE_BAL, html2)]
                nums = [n for n in nums if n.isdigit()]
                cands = [int(n) for n in nums if 0 <= int(n) <= 100_000_000]
                if cands: bal = min(cands)
            if bal is None:
                return False, 0, "잔액 파싱 실패"
            return True, int(bal), ""
        except PwTimeout:
            return False, 0, "응답 지연"
        except Exception as e:
            return False, 0, f"자동화 예외: {str(e)[:120]}"
        finally:
            with contextlib.suppress(Exception): await context.close()
            with contextlib.suppress(Exception): await browser.close()

# ===== Cog: /재고표시, /실시간_재고_설정 =====
class StockCog(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    @app_commands.command(name="재고표시", description="실시간 로벅스 재고 임베드를 공개로 표시합니다.")
    async def show_stock(self, it: discord.Interaction):
        if not it.guild:
            await it.response.send_message("길드에서만 사용 가능해.", ephemeral=True); return
        gid = it.guild.id
        with _db_lock:
            s = slot(gid); e = build_stock_embed(int(s["inventory"]), int(s["totalSold"]))
        await it.response.send_message(embed=e)  # 공개
        try:
            msg = await it.original_response()
            with _db_lock:
                s = slot(gid)
                s["lastMessage"] = {"channelId": it.channel.id, "messageId": msg.id}
                save_db()
        except: pass

    @app_commands.command(name="실시간_재고_설정", description="로블록스 계정 등록 후 잔액을 실시간 반영(관리자).")
    @is_admin()
    @app_commands.describe(id="로블록스 로그인 ID", pw="로블록스 로그인 PW")
    async def set_realtime_stock(self, it: discord.Interaction, id: str, pw: str):
        if not it.guild:
            await it.response.send_message("길드에서만 가능해.", ephemeral=True); return
        gid = it.guild.id
        await it.response.send_message("계정 확인 중…", ephemeral=True)

        with _db_lock:
            s = slot(gid)
            s["account"]["idEnc"] = enc(id.strip())
            s["account"]["pwEnc"] = enc(pw.strip())
            s["account"]["optionsApplied"] = True
            save_db()

        ok, amount, reason = await roblox_login_and_get_balance(s["account"]["idEnc"], s["account"]["pwEnc"])

        with _db_lock:
            s = slot(gid)
            if ok:
                s["inventory"] = int(max(0, amount))
                save_db()
            else:
                save_db()

        # 기존 임베드 수정
        try:
            with _db_lock:
                s = slot(gid)
                last = s.get("lastMessage") or {}
                ch_id = int(last.get("channelId") or 0)
                msg_id = int(last.get("messageId") or 0)
                inv = int(s.get("inventory", 0))
                sold = int(s.get("totalSold", 0))
            if ch_id and msg_id:
                ch = it.client.get_channel(ch_id)
                if isinstance(ch, discord.TextChannel):
                    msg = await ch.fetch_message(msg_id)
                    await msg.edit(embed=build_stock_embed(inv, sold))
        except Exception as e:
            LOG(f"[warn] 임베드 수정 실패: {e}")

        if ok:
            await it.followup.send(f"설정 완료. 현재 잔액 {amount} 로벅스 반영됨.", ephemeral=True)
        else:
            await it.followup.send(f"설정 실패: {reason or '확인 불가'}", ephemeral=True)

# ===== 싱크: setup_hook 1회 + 상세 로그 =====
@bot.event
async def setup_hook():
    LOG(f"[boot] APP_ID={APP_ID or 'missing'} / TOKEN={'set' if TOKEN else 'missing'} / GUILD_ID={GUILD_ID}")
    if not bot.application_id:
        LOG("[error] DISCORD_APP_ID 누락/잘못됨 → Secrets 확인"); return
    await bot.add_cog(StockCog(bot))
    try:
        LOG(f"[setup] 길드 싱크 시작: {GUILD_ID}")
        cmds = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        names = ", ".join(f"/{c.name}" for c in cmds)
        LOG(f"[setup] 길드 싱크 완료: {len(cmds)}개 → {names}")
    except Exception as e:
        LOG(f"[error] 길드 싱크 실패: {e}")

@bot.event
async def on_ready():
    LOG(f"[ready] 로그인: {bot.user} 준비완료")
    try:
        guilds = bot.guilds
        LOG(f"[ready] 봇이 속한 길드 수: {len(guilds)} → {[g.id for g in guilds]}")
        g = bot.get_guild(GUILD_ID)
        if g: LOG(f"[ready] 현재 길드 OK: {g.name}({g.id}) — 슬래시 명령 사용 가능")
        else: LOG(f"[warn] 길드({GUILD_ID})에 봇이 없음. 초대 스코프 bot + applications.commands로 다시 초대 필요")
    except Exception as e:
        LOG(f"[warn] 길드 확인 실패: {e}")

# ===== 실행 =====
async def main():
    if not TOKEN:
        LOG("[error] DISCORD_TOKEN 누락"); return
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
