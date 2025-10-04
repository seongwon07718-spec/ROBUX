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

DATA_PATH = "data.json"
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

ROBLOX_LOGIN_URLS = ["https://www.roblox.com/ko/Login", "https://www.roblox.com/Login"]
ROBLOX_TX_URLS = ["https://www.roblox.com/ko/transactions", "https://www.roblox.com/transactions"]

BALANCE_CACHE_TTL_SEC = 30
PAGE_TIMEOUT = 15000
NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[,\.\s]\d{3})*|\d+)(?!\d)")

def _default_data() -> Dict[str, Any]:
    return {
        "users": {},
        "stats": {"total_sold": 0},
        "cache": {"balances": {}},
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
    roblox["cookie_raw"] = cookie
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
    roblox["password"] = password
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

async def _extract_numbers_from_page(page: Page) -> Optional[int]:
    content = await page.content()
    nums = []
    for m in NUM_RE.finditer(content):
        raw = m.group(1)
        val = int(re.sub(r"[,\.\s]", "", raw))
        nums.append(val)
    if not nums:
        return None
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
        balance = await _extract_numbers_from_page(page)
        await page.close()
        return balance
    except Exception:
        return None

async def _login_with_idpw(context: BrowserContext, username: str, password: str) -> Dict[str, Any]:
    result = {"ok": False, "balance": None, "cookie": None, "username": None}
    page = await context.new_page()
    for url in ROBLOX_LOGIN_URLS:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            break
        except Exception:
            continue
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
        return result
    try:
        await page.wait_for_load_state("networkidle", timeout=PAGE_TIMEOUT)
    except Exception:
        pass
    try:
        for url in ROBLOX_TX_URLS:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
                break
            except Exception:
                continue
        balance = await _extract_numbers_from_page(page)
        result["balance"] = balance
        cookies = await context.cookies()
        for c in cookies:
            if c.get("name") == ".ROBLOSECURITY":
                result["cookie"] = c.get("value")
                break
        try:
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
            if cookie_raw:
                bal = await _open_with_cookie(context, cookie_raw)
                await browser.close()
                if isinstance(bal, int):
                    set_cached_balance(user_id, bal)
                    return bal
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
            await browser.close()
            return None
    except Exception:
        return None

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
    load_data()
    print(f"Logged in as {BOT.user} (data.json ready)")
    await sync_tree()

@TREE.command(name="실시간_재고_설정", description="Roblox 실시간 재고 연동을 설정합니다.")
@app_commands.describe(mode="cookie 또는 login", cookie=".ROBLOSECURITY 값", id="Roblox 아이디", pw="Roblox 비밀번호")
async def cmd_setup(inter: Interaction, mode: str, cookie: Optional[str] = None, id: Optional[str] = None, pw: Optional[str] = None):
    mode = (mode or "").lower().strip()
    if mode not in ("cookie", "login"):
        await inter.response.send_message("mode는 cookie 또는 login 중 하나여야 해.", ephemeral=True)
        return
    if mode == "cookie":
        if not cookie:
            await inter.response.send_message("cookie(.ROBLOSECURITY) 값을 넣어줘.", ephemeral=True)
            return
        set_user_cookie(inter.user.id, cookie)
        await inter.response.send_message(f"쿠키 저장 완료! /재고표시로 확인해봐. (저장값: {mask_cookie(cookie)})", ephemeral=True)
        return
    if mode == "login":
        if not id or not pw:
            await inter.response.send_message("login 모드는 id, pw 둘 다 필요해.", ephemeral=True)
            return
        set_user_login(inter.user.id, id, pw)
        await inter.response.send_message("로그인 정보 저장 완료! /재고표시로 불러올게.", ephemeral=True)

@TREE.command(name="재고표시", description="실시간 로벅스 재고를 보여줍니다.")
async def cmd_show(inter: Interaction):
    await inter.response.defer(thinking=True)
    bal = await fetch_balance_for_user(inter.user.id)
    total = get_total_sold()
    embed = Embed(title="실시간 로벅스 재고", colour=Colour.dark_grey(), timestamp=dt.datetime.utcnow())
    embed.description = "——————————"
    stock_value = "불러오기 실패"
    if isinstance(bal, int):
        stock_value = f"{bal:,}"
    embed.add_field(name="로벅스 수량", value=stock_value, inline=False)
    embed.add_field(name="총 판매량", value=f"{total:,}", inline=False)
    embed.add_field(name="로벅스 구매 바로가기", value="[구매 링크 열기](https://www.roblox.com/)", inline=False)
    await inter.followup.send(embed=embed)

@TREE.command(name="판매_누적", description="총 판매량을 누적합니다. (운영 훅)")
@app_commands.describe(amount="증가시킬 수량")
async def cmd_inc(inter: Interaction, amount: int):
    if amount < 0:
        await inter.response.send_message("음수 불가.", ephemeral=True)
        return
    cur = get_total_sold()
    set_total_sold(cur + amount)
    await inter.response.send_message(f"총 판매량 {amount:,} 증가 완료 (현재 {cur+amount:,}).", ephemeral=True)

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN이 비어있거나 형식이 이상함. 새 토큰 발급 후 환경변수에 넣어줘.")
    try:
        BOT.run(TOKEN)
    except discord.errors.LoginFailure as e:
        print("로그인 실패: 토큰이 잘못됐거나 권한 문제. 새 토큰으로 교체해줘.")
        raise e

if __name__ == "__main__":
    main()
