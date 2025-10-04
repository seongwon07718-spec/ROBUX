import os
import json
import re
import shutil
import asyncio
import datetime as dt
from typing import Any, Dict, Optional

import discord
from discord import app_commands, Interaction, Embed, Colour
from discord.ext import commands

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# ===================== 설정 =====================
DATA_PATH = "data.json"
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

ROBLOX_LOGIN_URLS = [
    "https://www.roblox.com/ko/Login",
    "https://www.roblox.com/Login",
]
ROBLOX_TX_URLS = [
    "https://www.roblox.com/ko/transactions",
    "https://www.roblox.com/transactions",
]

BALANCE_CACHE_TTL_SEC = 30  # 재고 조회 캐시 TTL
PAGE_TIMEOUT = 15000

# ===================== 유틸(파일/저장) =====================
def _default_data() -> Dict[str, Any]:
    return {
        "users": {},     # { discordUserId: { "roblox": { "username": "...", "masked_cookie": "...", "cookie_raw": "...", "cookie_set_at": "ISO8601" } } }
        "stats": {"total_sold": 0},
        "cache": {"balances": {}},  # { discordUserId: { "value": int, "ts": "ISO8601" } }
        "meta": {"version": 1}
    }

def _atomic_write(path: str, data: Dict[str, Any]):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    shutil.move(tmp, path)

def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_PATH):
        data = _default_data()
        _atomic_write(DATA_PATH, data)
        return data
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        data = _default_data()
        _atomic_write(DATA_PATH, data)
        return data

def save_data(data: Dict[str, Any]):
    _atomic_write(DATA_PATH, data)

def mask_cookie(cookie: str) -> str:
    if not cookie or len(cookie) < 7:
        return "***"
    return cookie[:3] + "***" + cookie[-3:]

def set_user_cookie(user_id: int, cookie: str, username_hint: Optional[str] = None):
    data = load_data()
    u = data["users"].get(str(user_id), {})
    roblox = u.get("roblox", {})
    roblox["cookie_raw"] = cookie  # 주의: 요구사항상 단일 파일에 저장. 실제 서비스라면 암호화 필요
    roblox["masked_cookie"] = mask_cookie(cookie)
    roblox["cookie_set_at"] = dt.datetime.utcnow().isoformat()
    if username_hint:
        roblox["username"] = username_hint
    u["roblox"] = roblox
    data["users"][str(user_id)] = u
    save_data(data)

def set_user_login(user_id: int, username: str, password: str):
    data = load_data()
    u = data["users"].get(str(user_id), {})
    roblox = u.get("roblox", {})
    roblox["username"] = username
    roblox["password"] = password  # 요구사항상 data.json 단일 저장. 실제 서비스라면 비권장(암호화 필요)
    u["roblox"] = roblox
    data["users"][str(user_id)] = u
    save_data(data)

def get_user_info(user_id: int) -> Dict[str, Any]:
    data = load_data()
    return data["users"].get(str(user_id), {}).get("roblox", {})

def set_total_sold(value: int):
    data = load_data()
    data["stats"]["total_sold"] = int(value)
    save_data(data)

def get_total_sold() -> int:
    data = load_data()
    return int(data.get("stats", {}).get("total_sold", 0))

def set_cached_balance(user_id: int, value: int):
    data = load_data()
    data["cache"].setdefault("balances", {})
    data["cache"]["balances"][str(user_id)] = {"value": int(value), "ts": dt.datetime.utcnow().isoformat()}
    save_data(data)

def get_cached_balance(user_id: int) -> Optional[int]:
    data = load_data()
    bal = data.get("cache", {}).get("balances", {}).get(str(user_id))
    if not bal:
        return None
    try:
        ts = dt.datetime.fromisoformat(bal["ts"])
    except Exception:
        return None
    if (dt.datetime.utcnow() - ts).total_seconds() <= BALANCE_CACHE_TTL_SEC:
        return int(bal["value"])
    return None

# ===================== Roblox 조회(Playwright) =====================
NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

async def _extract_numbers_from_page(page: Page) -> Optional[int]:
    content = await page.content()
    nums = []
    for m in NUM_RE.finditer(content):
        raw = m.group(1)
        val = int(re.sub(r"[,\.\s]", "", raw))
        nums.append(val)
    if not nums:
        return None
    return max(nums)  # 가장 그럴듯한 큰 숫자 사용(잔액 배지/표 상단이 대개 최대)

async def _open_with_cookie(context: BrowserContext, cookie_raw: str) -> Optional[int]:
    # Roblox 도메인에 보안 쿠키 주입 → 잔액 페이지에서 숫자 파싱
    try:
        # Set cookie
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
        # 바로 거래/잔액 페이지로
        for url in ROBLOX_TX_URLS:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
                break
            except Exception:
                continue
        # 간단 배지/텍스트에서도 숫자 스캔
        balance = await _extract_numbers_from_page(page)
        await page.close()
        return balance
    except Exception:
        return None

async def _login_with_idpw(context: BrowserContext, username: str, password: str) -> Dict[str, Any]:
    # 반환: {"ok": bool, "balance": Optional[int], "cookie": Optional[str], "username": Optional[str]}
    result = {"ok": False, "balance": None, "cookie": None, "username": None}
    page = await context.new_page()
    # 로그인 페이지 시도
    for url in ROBLOX_LOGIN_URLS:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            break
        except Exception:
            continue

    # 입력 필드 후보
    user_sel = "input[name='username'], input#login-username, input[type='text']"
    pass_sel = "input[name='password'], input#login-password, input[type='password']"

    try:
        await page.wait_for_selector(user_sel, timeout=PAGE_TIMEOUT)
        await page.fill(user_sel, username)
        await page.wait_for_selector(pass_sel, timeout=PAGE_TIMEOUT)
        await page.fill(pass_sel, password)
        login_btn = "button[type='submit'], button[aria-label], button:has-text('로그인'), button:has-text('Log In')"
        await page.click(login_btn)
    except Exception:
        await page.close()
    else:
        # 대기
        try:
            await page.wait_for_load_state("networkidle", timeout=PAGE_TIMEOUT)
        except Exception:
            pass

        # 로그인 성공 가정 후 거래 페이지 진입
        try:
            for url in ROBLOX_TX_URLS:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
                    break
                except Exception:
                    continue
            # 잔액 스캔
            balance = await _extract_numbers_from_page(page)
            result["balance"] = balance
            # 쿠키 획득 시도
            cookies = await context.cookies()
            cookie_val = None
            for c in cookies:
                if c.get("name") == ".ROBLOSECURITY":
                    cookie_val = c.get("value")
                    break
            if cookie_val:
                result["cookie"] = cookie_val
            # 유저명 힌트(상단 프로필 텍스트 등)
            try:
                # 간단히 타이틀이나 상단 텍스트에서 아무 영숫자 핸들 추정
                title = await page.title()
                if title:
                    m = re.search(r"[A-Za-z0-9_]{3,20}", title)
                    if m:
                        result["username"] = m.group(0)
            except Exception:
                pass
            result["ok"] = True if balance is not None else False
        finally:
            await page.close()

    return result

async def fetch_balance_for_user(user_id: int) -> Optional[int]:
    # 캐시 우선
    cached = get_cached_balance(user_id)
    if cached is not None:
        return cached

    info = get_user_info(user_id)
    cookie_raw = info.get("cookie_raw")
    username = info.get("username")
    password = info.get("password")

    try:
        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(headless=True)
            context: BrowserContext = await browser.new_context()

            # 1) 쿠키 우선
            if cookie_raw:
                bal = await _open_with_cookie(context, cookie_raw)
                await browser.close()
                if isinstance(bal, int):
                    set_cached_balance(user_id, bal)
                    return bal
                # 쿠키 실패 시 id/pw 폴백

            # 2) id/pw로 로그인
            if username and password:
                res = await _login_with_idpw(context, username, password)
                await browser.close()
                if res.get("ok"):
                    bal = res.get("balance")
                    if res.get("cookie"):
                        set_user_cookie(user_id, res["cookie"], res.get("username"))
                    if isinstance(bal, int):
                        set_cached_balance(user_id, bal)
                        return bal
                    return None
            else:
                await browser.close()
                return None
    except Exception:
        return None

# ===================== Discord Bot =====================
INTENTS = discord.Intents.default()
BOT = commands.Bot(command_prefix="!", intents=INTENTS)
TREE = BOT.tree

async def sync_tree():
    try:
        if GUILD_ID:
            await TREE.sync(guild=discord.Object(id=GUILD_ID))
        else:
            await TREE.sync()
    except Exception as e:
        print("Command sync err:", e)

@BOT.event
async def on_ready():
    # data.json 보장
    load_data()
    print(f"Logged in as {BOT.user} (data.json ready)")
    await sync_tree()

# /실시간_재고_설정
@TREE.command(name="실시간_재고_설정", description="Roblox 실시간 재고 연동을 설정합니다.")
@app_commands.describe(mode="cookie 또는 login 중 선택", cookie=".ROBLOSECURITY 값", id="Roblox 아이디", pw="Roblox 비밀번호")
async def cmd_setup(inter: Interaction, mode: str, cookie: Optional[str] = None, id: Optional[str] = None, pw: Optional[str] = None):
    mode = (mode or "").lower().strip()
    if mode not in ("cookie", "login"):
        await inter.response.send_message("mode는 cookie 또는 login 중 하나여야 해.", ephemeral=True)
        return

    if mode == "cookie":
        if not cookie:
            await inter.response.send_message("cookie 값을 넣어줘(.ROBLOSECURITY).", ephemeral=True)
            return
        set_user_cookie(inter.user.id, cookie)
        await inter.response.send_message(f"쿠키 저장 완료! 이제 /재고표시로 확인해봐. (저장값: {mask_cookie(cookie)})", ephemeral=True)
        return

    if mode == "login":
        if not id or not pw:
            await inter.response.send_message("login 모드는 id, pw 둘 다 필요해.", ephemeral=True)
            return
        set_user_login(inter.user.id, id, pw)
        await inter.response.send_message("로그인 정보 저장 완료! /재고표시로 재고 불러올게.", ephemeral=True)
        return

# /재고표시
@TREE.command(name="재고표시", description="실시간 로벅스 재고를 보여줍니다.")
async def cmd_show(inter: Interaction):
    await inter.response.defer(thinking=True)

    bal = await fetch_balance_for_user(inter.user.id)
    total = get_total_sold()

    embed = Embed(
        title="실시간 로벅스 재고",
        colour=Colour.dark_grey(),
        timestamp=dt.datetime.utcnow()
    )

    embed.description = "——————————"

    stock_value = "불러오기 실패"
    if isinstance(bal, int):
        stock_value = f"{bal:,}"

    embed.add_field(name="로벅스 수량", value=stock_value, inline=False)
    embed.add_field(name="총 판매량", value=f"{total:,}", inline=False)
    embed.add_field(
        name="로벅스 구매 바로가기",
        value="[구매 링크 열기](https://www.roblox.com/)",
        inline=False
    )

    await inter.followup.send(embed=embed)

# 선택: 총 판매량 누적(운영 시 주문 처리 로직에서 호출)
@TREE.command(name="판매_누적", description="총 판매량을 누적합니다. (운영 훅)")
@app_commands.describe(amount="증가시킬 수량(정수)")
async def cmd_inc(inter: Interaction, amount: int):
    if amount < 0:
        await inter.response.send_message("음수 불가.", ephemeral=True)
        return
    cur = get_total_sold()
    set_total_sold(cur + amount)
    await inter.response.send_message(f"총 판매량 {amount:,} 증가 완료 (현재 {cur+amount:,}).", ephemeral=True)

def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN이 비어있음")
    # data.json 없으면 생성
    load_data()
    BOT.run(TOKEN)

if __name__ == "__main__":
    main()
