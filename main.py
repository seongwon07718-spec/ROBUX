import os, json, threading, time, base64, sys, asyncio, re, contextlib
import discord
from discord import app_commands
from discord.ext import commands

# ===== 고정 환경 =====
GUILD_ID = 1419200424636055592
GUILD = discord.Object(id=GUILD_ID)
INTENTS = discord.Intents.default()
GRAY = discord.Color.from_str("#808080")

# ===== Bot: application_id 필수 =====
bot = commands.Bot(
    command_prefix="!",
    intents=INTENTS,
    application_id=int(os.getenv("DISCORD_APP_ID", "0"))
)

# ===== DB (아주 단순 JSON) =====
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
        "inventory": 0,         # 현재 로벅스 잔액(=재고)
        "totalSold": 0,         # 총 판매량
        "lastMessage": {"channelId": 0, "messageId": 0},
        "account": {"idEnc":"", "pwEnc":"", "cookies":[], "cookiesAt":0, "optionsApplied": True}
    })
    return DB["guilds"][str(gid)]

def now(): return int(time.time())

# ===== 테스트용 인코딩(운영 땐 교체) =====
def enc(s: str) -> str: return base64.b64encode((s or "").encode()).decode()
def dec(s: str) -> str:
    try: return base64.b64decode((s or "").encode()).decode()
    except: return ""

# ===== 권한 =====
def is_admin():
    async def pred(inter: discord.Interaction):
        if inter.user.guild_permissions.manage_guild:
            return True
        await inter.response.send_message("관리자만 사용 가능해.", ephemeral=True)
        return False
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
except:
    PLAYWRIGHT_AVAILABLE = False

# 일부 환경 child watcher 방어(미지원이면 조용히 패스)
try:
    if sys.platform != "win32" and hasattr(asyncio, "get_child_watcher"):
        try: asyncio.get_child_watcher()
        except NotImplementedError:
            from asyncio import SafeChildWatcher, set_child_watcher
            set_child_watcher(SafeChildWatcher())
except:
    pass

# ===== 로블록스 URL/셀렉터 =====
LOGIN_URL = "https://www.roblox.com/vi/Login"
TX_URL    = "https://www.roblox.com/ko/transactions"

SEL_ID      = "input#login-username, input[name='username'], input[type='text']"
SEL_PW      = "input#login-password, input[name='password'], input[type='password']"
SEL_LOGIN   = "button#login-button, button[type='submit'], button:has-text('로그인'), button:has-text('Đăng nhập')"

RE_BAL = re.compile(r"([0-9][0-9,\.]*)")
LAUNCH_KW = dict(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])

async def roblox_login_and_get_balance(enc_id: str, enc_pw: str) -> tuple[bool, int, str, list[dict]]:
    if not PLAYWRIGHT_AVAILABLE:
        return False, 0, "자동화 모듈 미설치", []
    ID = dec(enc_id); PW = dec(enc_pw)
    if not ID or not PW:
        return False, 0, "계정 정보 오류", []

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(**LAUNCH_KW)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            # 로그인
            await page.goto(LOGIN_URL, timeout=25000)
            await page.wait_for_timeout(700)

            id_el = await page.query_selector(SEL_ID) or (await page.query_selector_all("input"))[0]
            if not id_el: return False, 0, "ID 입력칸 없음", await context.cookies()
            await id_el.fill(ID)

            pw_el = await page.query_selector(SEL_PW) or (await page.query_selector_all("input[type='password']"))[0]
            if not pw_el: return False, 0, "PW 입력칸 없음", await context.cookies()
            await pw_el.fill(PW)

            btn = await page.query_selector(SEL_LOGIN) or await page.query_selector("button")
            if not btn: return False, 0, "로그인 버튼 없음", await context.cookies()
            await btn.click()

            await page.wait_for_timeout(1800)
            html = await page.content()

            # 보안 차단 감지
            if any(k in html.lower() for k in ["hcaptcha", "recaptcha", "two-step", "mfa", "verify"]):
                return False, 0, "보안 인증(캡차/2FA) 발생", await context.cookies()

            # 잔액 페이지
            await page.goto(TX_URL, timeout=25000)
            await page.wait_for_timeout(1200)
            html2 = await page.content()

            # 우선 패턴
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
                return False, 0, "잔액 파싱 실패", await context.cookies()

            return True, int(bal), "", await context.cookies()

        except PwTimeout:
            return False, 0, "응답 지연", await context.cookies()
        except Exception as e:
            return False, 0, f"자동화 예외: {str(e)[:120]}", await context.cookies()
        finally:
            with contextlib.suppress(Exception): await context.close()
            with contextlib.suppress(Exception): await browser.close()

# ===== Cog: 명령어 2개 =====
class StockCog(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    @app_commands.command(name="재고표시", description="실시간 로벅스 재고 임베드를 공개로 표시합니다.")
    async def show_stock(self, it: discord.Interaction):
        if not it.guild:
            await it.response.send_message("길드에서만 사용 가능해.", ephemeral=True); return
        gid = it.guild.id
        with _db_lock:
            s = slot(gid)
            e = build_stock_embed(int(s["inventory"]), int(s["totalSold"]))
        await it.response.send_message(embed=e)  # 공개 메시지
        try:
            msg = await it.original_response()
            with _db_lock:
                s = slot(gid)
                s["lastMessage"] = {"channelId": it.channel.id, "messageId": msg.id}
                save_db()
        except:
            pass

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
        ok, amount, reason, cookies = await roblox_login_and_get_balance(s["account"]["idEnc"], s["account"]["pwEnc"])
        with _db_lock:
            s = slot(gid)
            if ok:
                s["inventory"] = int(max(0, amount))
                s["account"]["cookies"] = cookies or []
                s["account"]["cookiesAt"] = now()
                save_db()
            else:
                s["account"]["cookies"] = []
                s["account"]["cookiesAt"] = 0
                save_db()
        # 기존 메시지 수정
        try:
            with _db_lock:
                s = slot(gid)
                last = s.get("lastMessage") or {}
                ch_id = int(last.get("channelId") or 0)
                msg_id = int(last.get("messageId") or 0)
                inv = int(s.get("inventory", 0))
                sold = int(s.get("totalSold", 0))
            if ch_id and msg_id:
                ch = it.guild.get_channel(ch_id)
                if isinstance(ch, discord.TextChannel):
                    msg = await ch.fetch_message(msg_id)
                    await msg.edit(embed=build_stock_embed(inv, sold))
        except:
            pass
        if ok:
            await it.followup.send(f"설정 완료. 현재 잔액 {amount} 로벅스 반영됨.", ephemeral=True)
        else:
            await it.followup.send(f"설정 실패: {reason or '확인 불가'}. 잠시 후 다시 시도해줘.", ephemeral=True)

# ===== 싱크: setup_hook에서 길드 한정 1회만 =====
@bot.event
async def setup_hook():
    if not bot.application_id:
        print("DISCORD_APP_ID 누락 또는 잘못됨"); return
    await bot.add_cog(StockCog(bot))
    try:
        await bot.tree.sync(guild=GUILD)
        print("길드 싱크 완료")
    except Exception as e:
        print("명령어 싱크 실패 :", e)

@bot.event
async def on_ready():
    print(f"로그인: {bot.user} 준비완료")

# ===== 실행 =====
async def main():
    token = os.getenv("DISCORD_TOKEN", "")
    if not token:
        print("DISCORD_TOKEN 누락"); return
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
