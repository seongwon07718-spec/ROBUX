import os
import io
import json
import re
import shutil
import asyncio
from typing import Any, Dict, Optional, Tuple

import discord
from discord import app_commands, Interaction, Embed, File
from discord.ext import commands, tasks
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

# ====== 전역 설정 ======
DATA_PATH = "data.json"
TOKEN = os.getenv("DISCORD_TOKEN")
# GUILD_ID가 환경변수에 없을 경우 0으로 설정하여 전체 서버에 명령어 등록 시도
GUILD_ID = int(os.getenv("GUILD_ID", "0")) 

# 이미지 표시 방식: "url" 또는 "attach"
IMAGE_MODE = "url"  # 기본: URL로 IMAGE 슬롯에 직접. 실패 시 자동 첨부 폴백.

# 💡 1. 요청하신 새로운 이미지 URL로 수정
STOCK_IMAGE_URL = "https://cdn.discordapp.com/attachments/1420389790649421877/1423911284260474910/IMG_2038.png?ex=68e20839&is=68e0b6b9&hm=d8a2a5a75fb270a7153e93fd28651a456f62102beffef0c134b7e90238f3f13c&"
LOCAL_IMAGE_PATH = "stock.png"  # 원하면 프로젝트에 이미지 파일 업로드해서 이 경로로 첨부 가능

# Roblox 경로
ROBLOX_LOGIN_URLS = ["https://www.roblox.com/ko/Login", "https://www.roblox.com/Login"]
ROBLOX_TX_URLS = ["https://www.roblox.com/ko/transactions", "https://www.roblox.com/transactions"]

# 타임아웃/주기
BALANCE_CACHE_TTL_SEC = 30
PAGE_TIMEOUT = 20000
UPDATE_INTERVAL_SEC = 60
LOGIN_RETRY = 2

# 숫자 파싱
NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

# ====== 저장소 유틸 ======
def _default_data() -> Dict[str, Any]:
    return {
        "users": {},  # { userId: { "roblox": {...}, "last_embed": {"channel_id","message_id"} } }
        "stats": {"total_sold": 0},
        "cache": {"balances": {}},  # {userId: {"value": int, "ts": float}}
        "meta": {"version": 1}
    }

def _atomic_write(path: str, data: Dict[str, Any]):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    shutil.move(tmp, path)

def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_PATH):
        d = _default_data()
        _atomic_write(DATA_PATH, d)
        return d
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # 파일 손상 시 초기화
        d = _default_data()
        _atomic_write(DATA_PATH, d)
        return d

def save_data(d: Dict[str, Any]):
    _atomic_write(DATA_PATH, d)

def mask_cookie(cookie: str) -> str:
    if not cookie or len(cookie) < 7:
        return "***"
    return cookie[:3] + "***" + cookie[-3:]

def get_user_block(uid: int) -> Dict[str, Any]:
    d = load_data()
    return d["users"].get(str(uid), {})

def set_user_block(uid: int, block: Dict[str, Any]):
    d = load_data()
    d["users"][str(uid)] = block
    save_data(d)

def set_user_cookie(uid: int, cookie: str, username_hint: Optional[str] = None):
    u = get_user_block(uid)
    r = u.get("roblox", {})
    r["cookie_raw"] = cookie
    r["masked_cookie"] = mask_cookie(cookie)
    r["cookie_set_at"] = asyncio.get_running_loop().time()
    if username_hint:
        r["username"] = username_hint
    u["roblox"] = r
    set_user_block(uid, u)

def set_user_login(uid: int, username: str, password: str):
    u = get_user_block(uid)
    r = u.get("roblox", {})
    r["username"] = username
    r["password"] = password
    u["roblox"] = r
    set_user_block(uid, u)

def set_last_embed(uid: int, channel_id: int, message_id: int):
    u = get_user_block(uid)
    u["last_embed"] = {"channel_id": channel_id, "message_id": message_id}
    set_user_block(uid, u)

def get_last_embed(uid: int) -> Optional[Dict[str, int]]:
    u = get_user_block(uid)
    return u.get("last_embed")

def get_total_sold() -> int:
    d = load_data()
    return int(d.get("stats", {}).get("total_sold", 0))

def cache_balance(uid: int, value: int):
    d = load_data()
    d["cache"].setdefault("balances", {})
    d["cache"]["balances"][str(uid)] = {"value": int(value), "ts": asyncio.get_running_loop().time()}
    save_data(d)

def get_cached_balance(uid: int) -> Optional[int]:
    d = load_data()
    item = d.get("cache", {}).get("balances", {}).get(str(uid))
    if not item:
        return None
    ts = float(item["ts"])
    if (asyncio.get_running_loop().time() - ts) <= BALANCE_CACHE_TTL_SEC:
        return int(item["value"])
    return None

# ====== Playwright 런처(실패 방지) ======
async def launch_browser(p: Playwright) -> Optional[Browser]:
    """브라우저 실행을 시도하고 실패 시 다른 옵션을 시도하여 브라우저를 반환합니다."""
    # 💡 2. 브라우저 접속 오류 해결을 위한 개선된 옵션 및 폴백 로직
    # '--no-sandbox'는 특히 Replit과 같은 리눅스 환경에서 필수적입니다.
    # '--disable-dev-shm-usage'는 메모리 부족 오류 방지에 도움을 줍니다.
    # '--single-process'는 일부 환경에서 안정성을 높입니다.
    
    args = [
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-setuid-sandbox",
        "--no-zygote",
        "--single-process",
    ]
    
    # 1차 시도: 일반적인 headless 모드
    try:
        return await p.chromium.launch(headless=True, args=args)
    except Exception as e:
        print(f"1차 브라우저 실행 실패 (headless): {e}")

    # 2차 시도: headless=False 모드
    try:
        return await p.chromium.launch(headless=False, args=args)
    except Exception as e:
        print(f"2차 브라우저 실행 실패 (not headless): {e}")

    # 3차 시도: 특정 환경 (예: 셸 환경)을 위한 대체 경로 지정
    try:
        # `playwright install-deps` 후에도 실패하는 경우를 대비
        return await p.chromium.launch(
            headless=True, 
            args=args, 
            executable_path=shutil.which("chromium-browser-for-selenium") or shutil.which("chromium-browser") or None
        )
    except Exception as e:
        print(f"3차 브라우저 실행 실패 (fallback path): {e}")
        
    return None

async def new_context(browser: Browser) -> Optional[BrowserContext]:
    try:
        return await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            java_script_enabled=True,
            locale="ko-KR",
        )
    except Exception:
        return None

# ====== Roblox 파싱 ======
async def _extract_numbers_from_page(page: Page) -> Optional[int]:
    """페이지에서 가장 큰 숫자를 잔액으로 추출합니다."""
    # 텍스트 기반 추출 시도
    content = await page.inner_text("body", timeout=5000)
    nums = []
    for m in NUM_RE.finditer(content):
        raw = m.group(1)
        # 콤마, 마침표, 공백을 제거하고 정수로 변환
        val = int(re.sub(r"[,\.\s]", "", raw)) 
        nums.append(val)
    
    # 추가: 특정 잔액 표시 요소 직접 확인 (선택자 변경 가능성에 대비해)
    try:
        bal_text = await page.locator("div.robux-balance").first.inner_text()
        if bal_text:
            m = NUM_RE.search(bal_text)
            if m:
                val = int(re.sub(r"[,\.\s]", "", m.group(1)))
                nums.append(val)
    except Exception:
        pass
        
    if not nums:
        return None
    # 페이지에 표시된 여러 숫자 중 가장 큰 값을 잔액으로 추정
    return max(nums)

async def _open_with_cookie(context: BrowserContext, cookie_raw: str) -> Optional[int]:
    try:
        await context.add_cookies([{
            "name": ".ROBLOSECURITY",
            "value": cookie_raw,
            "domain": ".roblox.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        }])
        page = await context.new_page()
        for url in ROBLOX_TX_URLS:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
                break
            except Exception:
                continue
        bal = await _extract_numbers_from_page(page)
        await page.close()
        return bal
    except Exception:
        return None

async def _login_with_idpw(context: BrowserContext, username: str, password: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str], Optional[str]]:
    ok, bal, cookie_val, username_hint, fail_reason = False, None, None, None, None
    page = await context.new_page()
    try:
        loaded = False
        for url in ROBLOX_LOGIN_URLS:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
                loaded = True
                break
            except Exception:
                continue
        if not loaded:
            return ok, bal, cookie_val, username_hint, "로그인 페이지 로딩 실패"

        user_sel = "input[name='username'], input#login-username"
        pass_sel = "input[name='password'], input#login-password"
        
        # 입력 필드와 버튼 선택자 안정화
        try:
            await page.wait_for_selector(user_sel, timeout=PAGE_TIMEOUT)
            await page.fill(user_sel, username)
            await page.fill(pass_sel, password)
        except Exception:
             # 선택자가 다를 경우를 대비하여 한 번 더 시도 (새로운 로그인 페이지 변화 대비)
             user_sel = "input[type='text']"
             pass_sel = "input[type='password']"
             await page.wait_for_selector(user_sel, timeout=PAGE_TIMEOUT)
             await page.fill(user_sel, username)
             await page.fill(pass_sel, password)

        login_btn = "button[type='submit'], button:has-text('로그인'), button:has-text('Log In')"
        await page.click(login_btn)

        try:
            # 네트워크가 안정화되거나 20초 대기
            await page.wait_for_load_state("networkidle", timeout=PAGE_TIMEOUT) 
        except Exception:
            pass

        # 오류 메시지 확인
        err = await page.query_selector("div:has-text('잘못') , div:has-text('Invalid') , div:has-text('incorrect')")
        if err:
            # 오류 메시지 텍스트를 실패 이유로 반환
            error_text = await err.inner_text()
            return ok, bal, cookie_val, username_hint, f"아이디/비밀번호 오류: {error_text[:30]}..."

        moved = False
        for url in ROBLOX_TX_URLS:
            try:
                # 로그인 후 거래 페이지로 이동 (잔액 확인)
                await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
                moved = True
                break
            except Exception:
                continue
        
        if not moved:
            # 페이지 이동 실패는 2FA, 캡차, 장치 인증 등 중간 단계가 남아있을 가능성 높음
            return ok, bal, cookie_val, username_hint, "거래 페이지 이동 실패 (2단계 인증 또는 캡차 가능성)"

        bal = await _extract_numbers_from_page(page)
        
        # 쿠키 추출
        cookies = await context.cookies()
        for c in cookies:
            if c.get("name") == ".ROBLOSECURITY":
                cookie_val = c.get("value")
                break

        # 유저 이름 힌트 추출 (제목에서 시도)
        try:
            title = await page.title()
            if title:
                m = re.search(r"[A-Za-z0-9_]{3,20}", title)
                if m:
                    username_hint = m.group(0)
        except Exception:
            pass

        ok = (bal is not None)
        if not ok and not fail_reason:
            fail_reason = "잔액 파싱 실패 (로그인은 성공했을 수 있으나 잔액을 찾지 못함)"
            
        return ok, bal, cookie_val, username_hint, fail_reason
    
    except Exception as e:
        return ok, bal, cookie_val, username_hint, f"브라우저 실행 예외 발생: {e.__class__.__name__}"
    
    finally:
        await page.close()


async def fetch_balance(uid: int) -> int:
    cached = get_cached_balance(uid)
    if cached is not None:
        return int(cached)

    info = get_user_block(uid).get("roblox", {})
    cookie_raw = info.get("cookie_raw")
    username = info.get("username")
    password = info.get("password")
    
    # 2회 재시도 루프
    for _ in range(LOGIN_RETRY):
        browser = None
        context = None
        try:
            async with async_playwright() as p:
                browser = await launch_browser(p)
                if not browser:
                    continue
                context = await new_context(browser)
                if not context:
                    await browser.close()
                    continue

                # 1. 쿠키로 시도
                if cookie_raw:
                    bal = await _open_with_cookie(context, cookie_raw)
                    if isinstance(bal, int):
                        cache_balance(uid, bal)
                        return int(bal)

                # 2. 아이디/비밀번호로 시도
                if username and password:
                    ok, bal, new_cookie, uname_hint, _ = await _login_with_idpw(context, username, password)
                    if ok and isinstance(bal, int):
                        if new_cookie:
                            # 성공 시 새로운 쿠키로 업데이트하여 다음 요청은 쿠키로 진행
                            set_user_cookie(uid, new_cookie, uname_hint)
                        cache_balance(uid, bal)
                        return int(bal)
        except Exception as e:
            print(f"잔액 fetch 중 예외 발생: {e}")
            continue
        finally:
            if browser:
                await browser.close()
                
    return 0  # 모든 시도 실패 시 0

# ====== 이미지 유틸 ======
async def fetch_image_bytes_from_url(url: str, timeout: int = 10) -> Optional[bytes]:
    """URL에서 이미지 바이트를 가져옵니다 (첨부 모드 폴백용)."""
    # urllib 대신 더 안정적인 aiohttp를 사용하는 것이 좋지만, 현재 의존성 유지를 위해 urllib 사용
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None

def make_embed(guild: Optional[discord.Guild], robux_balance: int, total_sold: int, image_as_attachment: bool) -> Embed:
    colour = discord.Colour(int("ff5dd6", 16))
    emb = Embed(title="", colour=colour)  # timestamp 미사용

    if guild:
        icon = guild.icon.url if guild.icon else None
        emb.set_author(name=guild.name, icon_url=icon)

    stock = f"{robux_balance:,}"
    total = f"{total_sold:,}"
    
    # 템플릿 코드 유지 (이모티콘 ID는 서버에 따라 다름)
    lines = [
        "### <a:upuoipipi:1423892277373304862>실시간 로벅스 재고",
        "### <a:thumbsuppp:1423892279612936294>로벅스 재고",
        f"<a:sakfnmasfagfamg:1423892278677602435>**`{stock}`로벅스**",
        "### <a:thumbsuppp:1423892279612936294>총 판매량",
        f"<a:sakfnmasfagfamg:1423892278677602435>**`{total}`로벅스**",
    ]
    emb.description = "\n".join(lines)

    # IMAGE 필드(본문 아래 크게)
    if image_as_attachment:
        # File 객체로 첨부 시 'attachment://파일명'
        emb.set_image(url="attachment://stock.png")
    else:
        # URL 모드 시 직접 URL 사용
        emb.set_image(url=STOCK_IMAGE_URL.strip())
    return emb

# ====== 디스코드 봇 ======
INTENTS = discord.Intents.default()
# 메시지 내용, 멤버 등 추가 권한이 필요할 경우 Intents.all() 사용 및 포털 설정
BOT = commands.Bot(command_prefix="!", intents=INTENTS)
TREE = BOT.tree

# { userId: {"channel_id": int, "message_id": int, "use_attachment": bool} }
active_updates: Dict[str, Dict[str, Any]] = {}

async def send_or_edit_public(inter: Interaction, uid: int, force_new: bool = False):
    bal = await fetch_balance(uid)
    total = get_total_sold()

    # 1) url 모드 시도 → 실패하면 attach 폴백
    # 💡 원본 로직 유지: IMAGE_MODE가 url이면 url 시도 후 실패 시 attach로 전환
    use_attachment = (IMAGE_MODE == "attach")
    file: Optional[File] = None

    if not use_attachment:
        embed = make_embed(inter.guild, bal, total, image_as_attachment=False)
        try:
            if force_new or not get_last_embed(uid):
                msg = await inter.channel.send(embed=embed)
                set_last_embed(uid, inter.channel.id, msg.id)
                active_updates[str(uid)] = {"channel_id": inter.channel.id, "message_id": msg.id, "use_attachment": False}
                return
            last = get_last_embed(uid)
            ch = await BOT.fetch_channel(last["channel_id"])
            msg = await ch.fetch_message(last["message_id"])
            await msg.edit(embed=embed)
            active_updates[str(uid)] = {"channel_id": ch.id, "message_id": msg.id, "use_attachment": False}
            return
        except Exception:
            use_attachment = True  # URL 실패 → 첨부 폴백

    # 2) 첨부 모드 (URL 실패 또는 초기 설정이 attach일 경우)
    embed = make_embed(inter.guild, bal, total, image_as_attachment=True)
    if os.path.exists(LOCAL_IMAGE_PATH):
        # 로컬 파일이 있으면 로컬 파일 사용
        file = File(fp=LOCAL_IMAGE_PATH, filename="stock.png")
    else:
        # 로컬 파일이 없으면 원본 URL에서 다운로드 후 사용
        img_bytes = await fetch_image_bytes_from_url(STOCK_IMAGE_URL)
        file = File(io.BytesIO(img_bytes), filename="stock.png") if img_bytes else None

    if force_new or not get_last_embed(uid):
        msg = await inter.channel.send(embed=embed, file=file) if file else await inter.channel.send(embed=embed)
        set_last_embed(uid, inter.channel.id, msg.id)
        active_updates[str(uid)] = {"channel_id": inter.channel.id, "message_id": msg.id, "use_attachment": bool(file)}
        return
    else:
        try:
            last = get_last_embed(uid)
            ch = await BOT.fetch_channel(last["channel_id"])
            msg = await ch.fetch_message(last["message_id"])
            
            # 메시지 수정 시 첨부 파일도 함께 전달
            if file:
                # attachments=[file] 대신 File 객체 직접 전달
                await msg.edit(embed=embed, attachments=[file]) 
                active_updates[str(uid)] = {"channel_id": ch.id, "message_id": msg.id, "use_attachment": True}
            else:
                # 파일이 없으면 임베드만 수정
                await msg.edit(embed=embed)
                active_updates[str(uid)] = {"channel_id": ch.id, "message_id": msg.id, "use_attachment": False}
        except Exception:
            # 기존 메시지 수정 실패 시 새로 전송
            msg = await inter.channel.send(embed=embed, file=file) if file else await inter.channel.send(embed=embed)
            set_last_embed(uid, inter.channel.id, msg.id)
            active_updates[str(uid)] = {"channel_id": inter.channel.id, "message_id": msg.id, "use_attachment": bool(file)}

@tasks.loop(seconds=UPDATE_INTERVAL_SEC)
async def updater_loop():
    for uid, loc in list(active_updates.items()):
        try:
            user_id = int(uid)
            ch = await BOT.fetch_channel(loc["channel_id"])
            msg = await ch.fetch_message(loc["message_id"])
            bal = await fetch_balance(user_id)
            total = get_total_sold()

            # 업데이트도 기존 방식 유지
            use_attachment = loc.get("use_attachment", IMAGE_MODE == "attach")
            embed = make_embed(getattr(msg, "guild", None), bal, total, image_as_attachment=use_attachment)

            if use_attachment:
                file: Optional[File] = None
                if os.path.exists(LOCAL_IMAGE_PATH):
                    file = File(fp=LOCAL_IMAGE_PATH, filename="stock.png")
                else:
                    img_bytes = await fetch_image_bytes_from_url(STOCK_IMAGE_URL)
                    file = File(io.BytesIO(img_bytes), filename="stock.png") if img_bytes else None
                
                if file:
                    await msg.edit(embed=embed, attachments=[file])
                    loc["use_attachment"] = True
                else:
                    await msg.edit(embed=embed)
                    loc["use_attachment"] = False
            else:
                await msg.edit(embed=embed)
                
        except Exception as e:
            # 메시지 삭제 등으로 인한 에러 발생 시 업데이트 목록에서 제거
            print(f"Update loop error for user {uid} in channel {loc.get('channel_id')}: {e}")
            del active_updates[uid]
            continue

async def sync_tree():
    try:
        if GUILD_ID:
            # 특정 길드에만 등록
            await TREE.sync(guild=discord.Object(id=GUILD_ID))
        else:
            # GUILD_ID가 없으면 전역 등록
            await TREE.sync()
    except Exception as e:
        print("Command sync err:", e)

@BOT.event
async def on_ready():
    load_data()
    print(f"Logged in as {BOT.user} (data.json ready)")
    await sync_tree()
    if not updater_loop.is_running():
        updater_loop.start()
    
    # 💡 Playwright 의존성 및 추가 의존성 안내
    print("\n--- 설치 가이드 ---")
    print("1. 필수: pip install -U discord.py playwright")
    print("2. 브라우저 엔진 설치: python -m playwright install chromium")
    print("3. 리눅스 환경에서 브라우저 실행 오류 시:")
    print("   a. 의존성 설치: python -m playwright install-deps")
    print("   b. (추가) 폰트 오류(Pang/HarfBuzz) 시: sudo apt-get install -y fontconfig")
    print("--------------------\n")

# ====== 명령어 ======
@TREE.command(name="실시간_재고_설정", description="쿠키/로그인 저장 후 즉시 검증하고 임베드에 반영합니다.")
@app_commands.describe(mode="cookie 또는 login", cookie=".ROBLOSECURITY 값", id="Roblox 아이디", pw="Roblox 비밀번호")
async def cmd_setup(inter: Interaction, mode: str, cookie: Optional[str] = None, id: Optional[str] = None, pw: Optional[str] = None):
    await inter.response.defer(ephemeral=True, thinking=True)
    mode = (mode or "").lower().strip()
    if mode not in ("cookie", "login"):
        await inter.followup.send(embed=Embed(title="실패", description="mode는 `cookie` 또는 `login`", colour=discord.Colour.red()), ephemeral=True)
        return

    if mode == "cookie":
        if not cookie:
            await inter.followup.send(embed=Embed(title="실패", description="`cookie`(.ROBLOSECURITY) 값 필요", colour=discord.Colour.red()), ephemeral=True)
            return
        set_user_cookie(inter.user.id, cookie)
        bal = await fetch_balance(inter.user.id)  # 실패 시 0
        await inter.followup.send(embed=Embed(title="연동 완료 🎉", description=f"현재 잔액: **{bal:,}** 로벅스\n*(쿠키로 로그인되어 60초마다 자동 갱신됩니다.)*", colour=discord.Colour.green()), ephemeral=True)
        await send_or_edit_public(inter, inter.user.id, force_new=False)
        return

    if mode == "login":
        if not id or not pw:
            await inter.followup.send(embed=Embed(title="실패", description="`login` 모드는 id, pw 필요", colour=discord.Colour.red()), ephemeral=True)
            return
        set_user_login(inter.user.id, id, pw)

        tried_ok = False
        last_reason = None
        bal_value = 0
        browser = None
        try:
            async with async_playwright() as p:
                browser = await launch_browser(p)
                if not browser:
                    last_reason = "브라우저 실행 오류 (Playwright 설치 및 의존성 확인 필요)"
                else:
                    ctx = await new_context(browser)
                    if not ctx:
                        last_reason = "브라우저 컨텍스트 실패 (샌드박스/권한 문제 가능성)"
                    else:
                        for _ in range(LOGIN_RETRY):
                            _ok, _bal, new_cookie, uname_hint, fail_reason = await _login_with_idpw(ctx, id, pw)
                            if _ok and isinstance(_bal, int):
                                tried_ok = True
                                bal_value = _bal
                                if new_cookie:
                                    set_user_cookie(inter.user.id, new_cookie, uname_hint)
                                break
                            last_reason = fail_reason or "알 수 없는 오류"
        except Exception as e:
            last_reason = f"Playwright 실행 예외: {e.__class__.__name__}"
        finally:
            if browser:
                await browser.close()
            
        if tried_ok:
            await inter.followup.send(embed=Embed(title="로그인 완료 🎉", description=f"현재 잔액: **{bal_value:,}** 로벅스\n*(쿠키가 저장되어 60초마다 자동 갱신됩니다.)*", colour=discord.Colour.green()), ephemeral=True)
            await send_or_edit_public(inter, inter.user.id, force_new=False)
        else:
            await inter.followup.send(embed=Embed(title="로그인 실패 😢", description=f"실패 이유: **{str(last_reason)}**", colour=discord.Colour.red()), ephemeral=True)

@TREE.command(name="재고표시", description="실시간 로벅스 재고를 공개 임베드로 표시합니다.")
async def cmd_show(inter: Interaction):
    # force_new=True로 기존 메시지 무시하고 새로운 메시지 전송
    await inter.response.defer(thinking=True, ephemeral=False) 
    await send_or_edit_public(inter, inter.user.id, force_new=True)
    await inter.followup.send("재고 임베드 공개 완료. 60초마다 자동 갱신됩니다.", ephemeral=True)

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN 환경 변수가 비어있거나 형식에 문제가 있습니다.")
    BOT.run(TOKEN)

if __name__ == "__main__":
    main()
