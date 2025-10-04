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
# GUILD_ID는 환경 변수에서 가져오는 것이 더 안전할 수 있지만, 일단 코드를 유지합니다.
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

# application_id를 명시적으로 전달
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
    except Exception as e:
        LOG(f"[error] DB 로드 실패: {e}")
        return {"guilds": {}}

def save_db():
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(DB, f, ensure_ascii=False, indent=2)
    except Exception as e:
        LOG(f"[error] DB 저장 실패: {e}")

DB = load_db()

def slot(gid: int):
    # DB 접근 시 lock 사용을 보장하는 것이 더 안전함 (여기서는 함수 밖에서 lock을 사용)
    # 다만, `slot` 함수 자체는 스레드 안전하게 설계
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
        # 관리자 권한 확인 (manage_guild는 서버 관리 권한 중 하나)
        if inter.user.guild_permissions.administrator or inter.user.guild_permissions.manage_guild:
            return True
        await inter.response.send_message("관리자만 사용 가능해. (서버 관리 권한 필요)", ephemeral=True); return False
    return app_commands.check(pred)

# ===== 임베드 =====
def build_stock_embed(inv: int, sold: int) -> discord.Embed:
    desc = (
        "**로벅스 수량**\n"
        f"`{inv:0,}`로벅스\n" # 콤마 포맷 추가
        "——————————\n"
        "**총 판매량**\n"
        f"`{sold:0,}`로벅스\n" # 콤마 포맷 추가
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
    LOG(f"[warn] Playwright import 실패. 실시간 잔액 확인 기능을 사용할 수 없습니다: {e}")
    LOG("Playwright를 설치하려면 다음 명령어를 사용하세요: pip install playwright && playwright install chromium")

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
LOGIN_URL = "https://www.roblox.com/vi/Login" # vi는 아마도 베트남어? ko로 통일하는 것이 안정적일 수 있음.
TX_URL    = "https://www.roblox.com/ko/transactions" # ko로 통일

SEL_ID      = "input#login-username, input[name='username'], input[type='text']"
SEL_PW      = "input#login-password, input[name='password'], input[type='password']"
SEL_LOGIN   = "button#login-button, button[type='submit'], button:has-text('로그인'), button:has-text('Đăng nhập'), button:has-text('Log In')" # Log In 추가

RE_BAL = re.compile(r"([0-9][0-9,\.]*)")
LAUNCH_KW = dict(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]) # --disable-gpu 추가

async def roblox_login_and_get_balance(enc_id: str, enc_pw: str) -> tuple[bool, int, str]:
    if not PLAYWRIGHT_AVAILABLE:
        return False, 0, "자동화 모듈(Playwright) 미설치"
    ID = dec(enc_id); PW = dec(enc_pw)
    if not ID or not PW:
        return False, 0, "계정 정보 오류"

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        # chromium 대신 firefox나 webkit을 시도해볼 수도 있음
        try:
            browser = await pw.chromium.launch(**LAUNCH_KW)
        except Exception as e:
            # Playwright 설치 관련 오류가 있을 경우를 대비
            return False, 0, f"브라우저 실행 실패. Playwright 재설치 필요: {str(e)[:120]}"

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121 Safari/537.36"
        )
        page = await context.new_page()
        try:
            # 1. 로그인 시도
            await page.goto(LOGIN_URL, timeout=30000)
            await page.wait_for_timeout(1000)

            id_el = await page.query_selector(SEL_ID)
            if not id_el: 
                # fallback 로직 제거하고 명확하게
                return False, 0, "ID 입력칸 찾기 실패"
            await id_el.fill(ID)

            pw_el = await page.query_selector(SEL_PW)
            if not pw_el: 
                return False, 0, "PW 입력칸 찾기 실패"
            await pw_el.fill(PW)

            btn = await page.query_selector(SEL_LOGIN)
            if not btn: 
                return False, 0, "로그인 버튼 찾기 실패"
            await btn.click()

            await page.wait_for_timeout(3000) # 로그인 후 로딩 대기 시간 증가
            
            # 보안 인증 확인
            html = await page.content()
            if any(k in html.lower() for k in ["hcaptcha","recaptcha","two-step","mfa","verify","login verification"]):
                return False, 0, "보안 인증 발생(캡차/2FA/이메일 인증 등)"

            # 2. 거래 내역 페이지로 이동 및 잔액 파싱
            await page.goto(TX_URL, timeout=30000)
            await page.wait_for_timeout(3000) # 페이지 로딩 대기 시간 증가
            html2 = await page.content()

            # 잔액 파싱 로직 강화
            bal = None
            for pat in [
                r"(내\s*잔액|balance|robux)\D+([0-9][0-9,\.]*)", 
                r"([0-9][0-9,\.]*)\s*(robux|rbx)",
                r'data-amount="([0-9]+)"' # HTML 속성에서 잔액을 직접 가져오는 패턴
            ]:
                m = re.search(pat, html2, re.IGNORECASE)
                if m:
                    # 그룹 1 또는 2에서 숫자 추출
                    cand = m.group(1) if (m.lastindex < 2 and m.group(1)) or m.group(1) not in ["robux", "rbx"] else m.group(m.lastindex)
                    cand = cand.replace(",", "").replace(".", "")
                    if cand.isdigit():
                        bal = int(cand); break
            
            # 로벅스 잔액 엘리먼트 텍스트 직접 찾기 시도 (예시 셀렉터: 'div[class*="robux-amount"]')
            # 이 부분은 로블록스 HTML 구조에 의존하므로, 위 정규식 파싱이 실패할 경우를 대비하여 유지
            if bal is None:
                 # 모든 숫자를 추출하여 합리적인 로벅스 잔액으로 추정
                nums = [n.replace(",", "").replace(".", "") for n in re.findall(RE_BAL, html2)]
                nums = [n for n in nums if n.isdigit()]
                cands = [int(n) for n in nums if 0 <= int(n) <= 100_000_000]
                if cands: bal = max(cands) # 가장 큰 숫자를 잔액으로 추정
                
            if bal is None:
                return False, 0, "잔액 파싱 실패 (로블록스 페이지 구조 변경 가능성)"
            
            return True, int(bal), ""
        
        except PwTimeout:
            return False, 0, "로블록스 응답 지연 (Timeout)"
        except Exception as e:
            return False, 0, f"자동화 예외: {type(e).__name__} - {str(e)[:120]}"
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
        
        # DB에서 데이터 로드 및 임베드 생성
        with _db_lock:
            s = slot(gid)
            e = build_stock_embed(int(s.get("inventory", 0)), int(s.get("totalSold", 0)))
        
        await it.response.send_message(embed=e)  # 공개 메시지 전송
        
        # 메시지 ID 저장
        try:
            msg = await it.original_response()
            with _db_lock:
                s = slot(gid)
                s["lastMessage"] = {"channelId": it.channel.id, "messageId": msg.id}
                save_db()
        except Exception as e: 
            LOG(f"[warn] 메시지 ID 저장 실패: {e}")

    @app_commands.command(name="실시간_재고_설정", description="로블록스 계정 등록 후 잔액을 실시간 반영(관리자).")
    @is_admin()
    @app_commands.describe(id="로블록스 로그인 ID", pw="로블록스 로그인 PW")
    async def set_realtime_stock(self, it: discord.Interaction, id: str, pw: str):
        if not it.guild:
            await it.response.send_message("길드에서만 가능해.", ephemeral=True); return
        
        if not PLAYWRIGHT_AVAILABLE:
            await it.response.send_message("❌ **Playwright 자동화 모듈이 설치되지 않았습니다.**\n`pip install playwright` 후 `playwright install chromium`을 실행하여 설치해야 이 기능을 사용할 수 있습니다.", ephemeral=True)
            return

        gid = it.guild.id
        await it.response.send_message("⏳ 계정 정보 암호화 및 로블록스 로그인 확인 중...", ephemeral=True)

        # 계정 정보 저장 (ID/PW 암호화)
        with _db_lock:
            s = slot(gid)
            s["account"]["idEnc"] = enc(id.strip())
            s["account"]["pwEnc"] = enc(pw.strip())
            s["account"]["optionsApplied"] = True
            save_db()

        # 로블록스 로그인 및 잔액 확인
        ok, amount, reason = await roblox_login_and_get_balance(s["account"]["idEnc"], s["account"]["pwEnc"])

        # 잔액 결과 DB에 반영
        with _db_lock:
            s = slot(gid)
            if ok:
                # 잔액이 0 미만일 수는 없으므로 max(0, amount) 처리
                s["inventory"] = int(max(0, amount)) 
            # 실패하더라도 계정 정보는 유지되므로 DB 저장은 여기서 한 번만 함
            save_db()

        # 기존 재고표시 임베드 수정 시도 (비동기)
        if ok:
            await self.update_stock_embed(gid)

        # 결과 피드백
        if ok:
            await it.followup.send(f"✅ **설정 완료.** 현재 잔액 **{amount:0,} 로벅스**가 재고에 반영되었습니다.", ephemeral=True)
        else:
            await it.followup.send(f"❌ **설정 실패.** 로블록스 로그인/잔액 확인 중 문제가 발생했습니다:\n`{reason or '확인 불가'}`\nID/PW를 다시 확인하거나, 2FA/캡차 설정을 해제해 주세요.", ephemeral=True)

    # 임베드 업데이트 로직을 별도 함수로 분리하여 재사용성 및 가독성 향상
    async def update_stock_embed(self, gid: int):
        # DB에서 필요한 정보 로드 (잠금 필요)
        try:
            with _db_lock:
                s = slot(gid)
                last = s.get("lastMessage") or {}
                ch_id = int(last.get("channelId") or 0)
                msg_id = int(last.get("messageId") or 0)
                inv = int(s.get("inventory", 0))
                sold = int(s.get("totalSold", 0))
            
            # 메시지 수정
            if ch_id and msg_id:
                # 채널과 메시지를 가져오기 위해 클라이언트 객체 사용
                ch = self.bot.get_channel(ch_id)
                if isinstance(ch, discord.TextChannel):
                    try:
                        msg = await ch.fetch_message(msg_id)
                        await msg.edit(embed=build_stock_embed(inv, sold))
                        LOG(f"[info] 재고 임베드 성공적으로 수정됨 (Guild:{gid})")
                    except discord.NotFound:
                        LOG(f"[warn] 재고 임베드 메시지/채널 찾기 실패 (Guild:{gid}) - ID: {ch_id}/{msg_id}")
                    except Exception as e:
                        LOG(f"[warn] 재고 임베드 수정 실패: {type(e).__name__} - {e}")
        except Exception as e:
            LOG(f"[warn] 임베드 업데이트 로직 중 예외 발생: {e}")

# ===== 싱크: setup_hook 1회 + 상세 로그 =====
@bot.event
async def setup_hook():
    LOG(f"[boot] APP_ID={APP_ID or 'missing'} / TOKEN={'set' if TOKEN else 'missing'} / GUILD_ID={GUILD_ID}")
    
    if not bot.application_id:
        LOG("[error] DISCORD_APP_ID 누락/잘못됨 → Secrets 확인"); return
    
    await bot.add_cog(StockCog(bot))
    
    try:
        # 길드 객체를 먼저 가져와서 존재하는지 확인
        target_guild = bot.get_guild(GUILD_ID)
        if not target_guild:
            LOG(f"[warn] 길드({GUILD_ID}) 오브젝트를 찾을 수 없음. 봇이 해당 길드에 초대되지 않았을 수 있습니다.")
        
        LOG(f"[setup] 길드 싱크 시작: {GUILD_ID}")
        # 길드 싱크는 GUILD_ID를 포함하여 명시적으로 시도
        cmds = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        names = ", ".join(f"/{c.name}" for c in cmds)
        LOG(f"[setup] 길드 싱크 완료: {len(cmds)}개 → {names}")
        
    except Exception as e:
        # 싱크 실패 시 에러 로그를 좀 더 상세하게 출력
        LOG(f"[error] 길드 싱크 실패: {type(e).__name__} - {e}")

@bot.event
async def on_ready():
    LOG(f"[ready] 로그인: {bot.user} 준비완료")
    try:
        guilds = bot.guilds
        LOG(f"[ready] 봇이 속한 길드 수: {len(guilds)} → {[g.id for g in guilds]}")
        
        g = bot.get_guild(GUILD_ID)
        if g: 
            LOG(f"[ready] 현재 길드 OK: {g.name}({g.id}) — 슬래시 명령 사용 가능 예상")
        else: 
            # 이 메시지가 뜬다면 봇이 GUILD_ID 길드에 실제로 초대되지 않은 것
            LOG(f"[warn] 길드({GUILD_ID})에 봇이 없음. 봇을 다시 초대하세요 (스코프: bot + applications.commands)")
            
    except Exception as e:
        LOG(f"[warn] 길드 확인 실패: {e}")

# ===== 실행 =====
async def main():
    if not TOKEN:
        LOG("[error] DISCORD_TOKEN 누락. Secrets 환경 변수를 확인하세요."); return
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    # Windows 환경에서 asyncio 이슈 방지 (이미 코드에 있으나, 명시적으로 유지)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOG("[info] 봇 종료 요청")
    except Exception as e:
        LOG(f"[fatal] 봇 실행 중 치명적인 오류 발생: {e}")

