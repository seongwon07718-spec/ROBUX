import os
import random
import string
import aiohttp
import discord
from discord import app_commands, ui
from discord.ext import tasks, commands
import sqlite3
import asyncio
import os
import random
import string
import discord
from discord import app_commands, ui
from discord.ext import tasks, commands
import sqlite3
import asyncio
import re
import uvicorn
import requests
import json
import uuid
import subprocess
from fastapi import FastAPI
from fastapi import FastAPI, Request, HTTPException
from fastapi.security import HTTPBearer
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from threading import Thread
from buy_gamepass import process_manual_buy_selenium

# ─────────────────────────────────────────
# 설정
# ─────────────────────────────────────────

purchase_cooldown = {}
COOLDOWN_SECONDS = 60

DATABASE = "robux_shop.db"
TOKEN = ""
BANK_K = "7777-03-6763823 (카카오뱅크)"

COIN_FEE = {
    "btc": 8,
    "ltc": 5,
    "trx": 5,
    "sol": 5,
}

COIN_LIST = {
    "ltc": ("라이트코인", "LTC"),
    "trx": ("트론", "TRX"),
    "btc": ("비트코인", "BTC"),
    "sol": ("솔라나", "SOL"),
}

GIFT_GAMES = [
    ("라이벌", "17625359962"),
    ("배드워즈", "6872265039"),
]

# ─────────────────────────────────────────
# DB 초기화
# ─────────────────────────────────────────

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id TEXT,
                amount INTEGER,
                robux INTEGER,
                status TEXT,
                roblox_name TEXT DEFAULT '',
                roblox_id TEXT DEFAULT '',
                gamepass_name TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE TABLE IF NOT EXISTS vending_messages (channel_id TEXT PRIMARY KEY, msg_id TEXT)")

        for col in ["roblox_name", "roblox_id", "gamepass_name"]:
            try:
                cur.execute(f"ALTER TABLE orders ADD COLUMN {col} TEXT DEFAULT ''")
            except Exception:
                pass

        conn.commit()

init_db()

# ─────────────────────────────────────────
# FastAPI (입금 감지)
# ─────────────────────────────────────────

app = FastAPI()
pending_deposits = {}

class ChargeData(BaseModel):
    message: str
    server_id: str = ""
    pw: str = ""

@app.post("/charge")
async def receive_charge(request: Request, data: ChargeData):

    server_id = request.headers.get("server-id") or data.server_id if hasattr(data, 'server_id') else None
    pw = request.headers.get("pw") or data.pw if hasattr(data, 'pw') else None

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'charge_server_id'")
        saved_id = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'charge_pw'")
        saved_pw = cur.fetchone()

    if not saved_id or not saved_pw:
        raise HTTPException(status_code=500, detail="Server not configured")

    if server_id != saved_id[0] or pw != saved_pw[0]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    msg = data.message.strip()
    amount_match = re.search(r'입금\s*([\d,]+)원', msg)
    name_match = re.search(r'원\n([가-힣]+)\n잔액', msg)

    name = None
    amount = None

    if amount_match and name_match:
        amount = amount_match.group(1).replace(",", "")
        name = name_match.group(1)
        pending_deposits[f"{name}_{amount}"] = True
    else:
        fallback = re.search(r'([가-힣]+)\s*(\d+)', msg)
        if fallback:
            name = fallback.group(1)
            amount = fallback.group(2)
            pending_deposits[f"{name}_{amount}"] = True

    return {
        "ok": True,
        "message": f"{name} / {int(amount):,}원 충전 신청 완료" if name and amount else "처리 완료"
    }

web_app = FastAPI()

@web_app.get("/")
async def root():
    return {"status": "ok"}

@web_app.get("/purchase-log")
async def purchase_log_page():
    try:
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "purchase_log.html")
        print(f"[웹] HTML 경로: {html_path}")
        print(f"[웹] 파일 존재: {os.path.exists(html_path)}")
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except Exception as e:
        return HTMLResponse(f"<h1>오류: {e}</h1>")

@web_app.get("/api/purchase-logs")
async def get_purchase_logs(limit: int = 20, offset: int = 0):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT order_id, user_id, amount, robux, created_at, roblox_name, roblox_id, gamepass_name
            FROM orders WHERE status = 'completed'
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed' AND DATE(created_at) = DATE('now')")
        today = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'completed'")
        total_amount = cur.fetchone()[0]

    logs = []
    for row in rows:
        order_id, user_id, amount, robux, created_at, roblox_name, roblox_id, gamepass_name = row
        logs.append({
            "order_id": order_id,
            "roblox_name": roblox_name or "유저",
            "roblox_id": roblox_id or "",
            "amount": amount,
            "robux": robux,
            "gamepass_name": gamepass_name or "게임패스",
            "created_at": created_at,
            "avatar_url": f"https://www.roblox.com/headshot-thumbnail/image?userId={roblox_id}&width=150&height=150&format=png" if roblox_id else ""
        })

    return {"logs": logs, "stats": {"total": total, "today": today, "total_amount": total_amount}}

# ─────────────────────────────────────────
# 유틸 함수
# ─────────────────────────────────────────

async def get_container_view(title: str, description: str, color: int):
    view = ui.LayoutView()
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"### {title}\n{description}"))
    view.add_item(con)
    return view

def create_container_msg(title, description, color):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"### {title}"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(description))
    return con

def get_roblox_data(cookie):
    if not cookie:
        return False, "입력된 쿠키가 없습니다."

    auth_cookie = cookie.strip().strip('"').strip("'")
    if not auth_cookie.startswith(".ROBLOSECURITY="):
        full_cookie = f".ROBLOSECURITY={auth_cookie}"
    else:
        full_cookie = auth_cookie

    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": full_cookie,
    }

    try:
        res = session.get("https://users.roblox.com/v1/users/authenticated", headers=headers, timeout=7)
        if res.status_code == 200:
            user_id = res.json().get("id")
            eco = session.get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers=headers, timeout=5)
            robux = eco.json().get("robux", 0) if eco.status_code == 200 else 0
            return True, robux
        return False, "만료되었거나 잘못된 쿠키입니다"
    except Exception:
        return False, "로블록스 서버와 연결할 수 없습니다"

# ─────────────────────────────────────────
# Roblox API
# ─────────────────────────────────────────

class RobloxAPI:
    BASE_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )
    }

    def __init__(self, cookie: str | None = None):
        self.session = requests.Session()
        self.session.headers.update(self.BASE_HEADERS)
        if cookie:
            clean = cookie.strip()
            if "=" in clean:
                clean = clean.split("=", 1)[-1]
            self.session.cookies.set(".ROBLOSECURITY", clean, domain=".roblox.com")

    def get_user_id(self, nickname: str) -> int | None:
        resp = self.session.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [nickname], "excludeBannedUsers": False},
        )
        print(f"[유저검색] status={resp.status_code} body={resp.text}")
        if resp.status_code != 200:
            return None
        data = resp.json().get("data", [])
        return data[0].get("id") if data else None

    def get_user_places(self, user_id: int) -> list[dict]:
        games = []
        cursor = ""
        while True:
            url = f"https://games.roblox.com/v2/users/{user_id}/games?limit=50&sortOrder=Asc"
            if cursor:
                url += f"&cursor={cursor}"
            resp = self.session.get(url)
            if resp.status_code != 200:
                break
            body = resp.json()
            for g in body.get("data", []):
                root_place = g.get("rootPlace") or {}
                games.append({
                    "id": g.get("id"),
                    "name": g.get("name") or "이름 없는 게임",
                    "rootPlaceId": root_place.get("id"),
                })
            cursor = body.get("nextPageCursor") or ""
            if not cursor:
                break
        return games

    def get_place_gamepasses(self, universe_id: int) -> list[dict]:
        passes = []
        page_token = ""
        while True:
            url = (
                f"https://apis.roproxy.com/game-passes/v1/universes/{universe_id}/game-passes"
                f"?passView=Full&pageSize=100"
            )
            if page_token:
                url += f"&pageToken={page_token}"
            resp = self.session.get(url)
            if resp.status_code != 200:
                break
            body = resp.json()
            for p in body.get("gamePasses", []):
                price = p.get("price")
                pass_id = p.get("id")
                name = p.get("displayName") or p.get("name") or "이름 없음"
                if pass_id and price and price > 0:
                    passes.append({"id": pass_id, "name": name, "price": price})
            page_token = body.get("nextPageToken") or ""
            if not page_token:
                break
        return passes

# ─────────────────────────────────────────
# 게임패스 구매 뷰
# ─────────────────────────────────────────

class FinalBuyView(ui.LayoutView):

    def __init__(self, pass_info: dict, money: int, user_id: int | str, discount: int = 0):
        super().__init__(timeout=60)
        self.pass_info = pass_info
        self.money = money
        self.user_id = str(user_id)
        self.discount = discount
        self._build_ui()

    def _build_ui(self):
        con = ui.Container()
        con.accent_color = 0x5865F2

        discount_text = f"\n-# - **할인율**: {self.discount}%" if self.discount > 0 else ""

        con.add_item(ui.TextDisplay(
            f"### <:acy2:1489883409001091142>  최종 단계\n"
            f"-# - **게임패스**: {self.pass_info.get('name', '알 수 없음')}\n"
            f"-# - **로벅스**: {self.pass_info.get('price', 0):,}로벅스"
            f"{discount_text}\n"
            f"-# - **차감금액**: {self.money:,}원"
        ))

        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        btn = ui.Button(label="진행하기", style=discord.ButtonStyle.gray, emoji="<:success:1489875582874554429>")
        btn.callback = self.do_buy
        con.add_item(ui.ActionRow(btn))
        self.add_item(con)

    async def do_buy(self, it: discord.Interaction):

        now = asyncio.get_event_loop().time()
        last = purchase_cooldown.get(self.user_id, 0)
        if now - last < COOLDOWN_SECONDS:
            remain = int(COOLDOWN_SECONDS - (now - last))
            await it.response.edit_message(
                view=await get_container_view(
                    "<:downvote:1489930277450158080>  중복 시도",
                    f"-# - {remain}초 후에 다시 시도할 수 있습니다",
                    0xED4245
                )
            )
            return
        purchase_cooldown[self.user_id] = now

        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'maintenance'")
            m = cur.fetchone()

        if m and m[0] == "1":
            await it.response.edit_message(
                view=await get_container_view(
                    "<:downvote:1489930277450158080>  점검 중",
                    "-# - 현재 점검 중입니다\n-# - 잠시 후 다시 시도해주세요",
                    0xED4245
                )
            )
            return

        start_time = asyncio.get_event_loop().time()

        await it.response.edit_message(
            view=await get_container_view(
                "<a:1792loading:1487444148716965949>  대기 중",
                "-# - 대기열에 등록되었습니다\n-# - 잠시만 기다려주세요",
                0x5865F2
            )
        )

        loop = asyncio.get_running_loop()
        from buy_gamepass import queue_status

        order_ref = {"id": None}

        async def update_position():
            while True:
                await asyncio.sleep(3)
                try:
                    for oid, info in list(queue_status.items()):
                        if order_ref["id"] and oid != order_ref["id"]:
                            continue
                        if info["status"] == "waiting":
                            pos = info["position"]
                            try:
                                await it.edit_original_response(
                                    view=await get_container_view(
                                        "<a:1792loading:1487444148716965949>  대기 중",
                                        f"-# - 대기열: **{pos}번째**\n-# - 앞에 {pos - 1}명이 있습니다",
                                        0x5865F2
                                    )
                                )
                            except Exception:
                                pass
                        elif info["status"] == "processing":
                            try:
                                await it.edit_original_response(
                                    view=await get_container_view(
                                        "<a:1792loading:1487444148716965949>  구매 진행 중",
                                        "-# - 로블록스 서버 API 연결 중입니다\n-# - 구매를 진행하는데 약간의 시간이 소요될 수 있습니다",
                                        0x5865F2
                                    )
                                )
                            except Exception:
                                pass
                except Exception:
                    pass

        update_task = asyncio.create_task(update_position())

        res = await loop.run_in_executor(
            None, process_manual_buy_selenium,
            self.pass_info["id"], self.user_id, self.money,
            self.pass_info.get("roblox_name", ""), 
            self.pass_info.get("name", "")  
        )
        update_task.cancel()

        elapsed = round(asyncio.get_event_loop().time() - start_time, 1)

        if res["success"]:
            view = ui.LayoutView()
            con = ui.Container()
            con.accent_color = 0x5865F2
            con.add_item(ui.TextDisplay(
                f"### <:acy2:1489883409001091142>  구매 성공\n"
                f"-# - **게임패스**: {self.pass_info.get('name', '알 수 없음')}\n"
                f"-# - **가격**: {self.pass_info.get('price', 0):,}로벅스\n"
                f"-# - **결제금액**: {self.money:,}원\n"
                f"-# - **처리시간**: {elapsed}초\n"
                f"-# - **거래ID**: `{res['order_id']}`"
            ))
            view.add_item(con)
            await it.edit_original_response(view=view)

            screenshot = res.get("screenshot")

            try:
                if screenshot and os.path.exists(screenshot):
                    await it.user.send(
                        content=f"<:acy2:1489883409001091142> **@{it.user.name} 구매 완료 - 거래ID: `{res['order_id']}`**",
                        file=discord.File(screenshot, filename="success.png")
                    )
                else:
                    await it.user.send(
                        content=f"<:acy2:1489883409001091142> **@{it.user.name} 구매 완료 - 거래ID: `{res['order_id']}`**\n- 게임패스: {self.pass_info.get('name', '알 수 없음')}\n- 가격: {self.pass_info.get('price', 0):,}로벅스\n- 결제금액: {self.money:,}원\n- 처리시간: {elapsed}초"
                    )
            except Exception as e:
                print(f"[DM 실패] {e}")

            try:
                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT value FROM config WHERE key = 'purchase_log'")
                    log_row = cur.fetchone()

                if log_row:
                    log_channel = bot.get_channel(int(log_row[0]))
                    if log_channel:
                        if screenshot and os.path.exists(screenshot):
                            await log_channel.send(
                                content=f"<:acy2:1489883409001091142> **{it.user.mention} / {self.pass_info.get('price', 0):,}로벅스 구매 감사합니다**\n- 게임패스: {self.pass_info.get('name', '알 수 없음')}\n- 결제금액: {self.money:,}원\n- 거래ID: `{res['order_id']}`",
                                file=discord.File(screenshot, filename="success.png")
                            )
                        else:
                            await log_channel.send(
                                content=f"<:acy2:1489883409001091142> **{it.user.mention} / {self.pass_info.get('price', 0):,}로벅스 구매 감사합니다**\n- 게임패스: {self.pass_info.get('name', '알 수 없음')}\n- 결제금액: {self.money:,}원\n- 거래ID: `{res['order_id']}`"
                            )
            except Exception as e:
                print(f"[로그 실패] {e}")

        elif res.get("message") and "이미 소유" in res["message"]:
            view = ui.LayoutView()
            con = ui.Container()
            con.accent_color = 0xED4245
            con.add_item(ui.TextDisplay(
                f"### <:downvote:1489930277450158080>  구매 불가\n"
                f"-# - **게임패스**: {self.pass_info.get('name', '알 수 없음')}\n"
                f"-# - 이미 보유 중인 게임패스입니다\n"
                f"-# - 다른 게임패스를 선택해주세요"
            ))
            view.add_item(con)
            await it.edit_original_response(view=view)

        else:
            await it.edit_original_response(
                view=await get_container_view(
                    "<:downvote:1489930277450158080>  결제 실패",
                    f"-# {res.get('message', '알 수 없는 오류')}",
                    0xED4245
                )
            )

class PassSelectView(ui.LayoutView):

    def __init__(self, passes: list[dict], user_id: int | str):
        super().__init__(timeout=60)
        self.passes = passes
        self.user_id = user_id
        self._build_ui()

    def _build_ui(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            "### <:acy2:1489883409001091142>  게임패스 선택\n"
            "-# - 구매할 게임패스를 선택하세요"
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        select = ui.Select(placeholder="게임패스를 선택해주세요")
        for p in self.passes[:25]:
            p_id = p.get("id")
            p_name = p.get("name") or "이름 없음"
            p_price = p.get("price", 0)
            if p_id is not None:
                select.add_option(
                    label=f"{p_name[:80]} ({p_price:,} R$)",
                    value=str(p_id),
                )

        select.callback = self.on_select
        con.add_item(ui.ActionRow().add_item(select))
        self.add_item(con)

    async def on_select(self, it: discord.Interaction):
        selected_id = int(it.data["values"][0])
        pass_data = next((p for p in self.passes if p.get("id") == selected_id), None)

        if not pass_data:
            await it.response.send_message(
                view=await get_container_view("<:downvote:1489930277450158080>  오류", "-# - 오류가 발생했습니다", 0xED4245),
                ephemeral=True
            )
            return

        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
            r = cur.fetchone()
            rate = int(r[0]) if r else 1000

            cur.execute("SELECT value FROM config WHERE key = ?", (f"discount_{it.user.id}",))
            d = cur.fetchone()
            discount = int(d[0]) if d else 0

        base_money = int((pass_data.get("price", 0) / rate) * 10000)
        discounted = int(base_money * (1 - discount / 100)) if discount > 0 else base_money

        view = FinalBuyView(pass_data, discounted, it.user.id, discount)
        await it.response.edit_message(view=view)


class PlaceSelectView(ui.LayoutView):

    def __init__(self, places: list[dict], user_id: int | str):
        super().__init__(timeout=60)
        self.places = places
        self.user_id = user_id
        self._build_ui()

    def _build_ui(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            "### <:acy2:1489883409001091142>  게임 선택\n"
            "-# - 게임패스를 구매할 게임을 선택해주세요"
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        seen: set[int] = set()
        options = []
        for p in self.places:
            u_id = p.get("id")
            if u_id and u_id not in seen and len(seen) < 25:
                options.append(p)
                seen.add(u_id)

        if not options:
            con.add_item(ui.TextDisplay("<:downvote:1489930277450158080>\n-# - 선택 가능한 공개 게임이 없습니다"))
        else:
            select = ui.Select(placeholder="게임을 선택해주세요")
            for p in options:
                select.add_option(label=p["name"][:100], value=str(p["id"]))
            select.callback = self.on_select
            con.add_item(ui.ActionRow().add_item(select))

        self.add_item(con)

    async def on_select(self, it: discord.Interaction):
        universe_id = int(it.data["values"][0])

        await it.response.edit_message(
            view=await get_container_view(
                "<a:1792loading:1487444148716965949>  조회 중",
                "-# - 게임패스 목록을 불러오는 중입니다",
                0x5865F2
            )
        )

        loop = asyncio.get_running_loop()
        api = RobloxAPI()
        passes = await loop.run_in_executor(None, api.get_place_gamepasses, universe_id)

        if not passes:
            await it.edit_original_response(
                view=await get_container_view(
                    "<:downvote:1489930277450158080>  결과 없음",
                    "-# - 판매 중인 게임패스가 없습니다",
                    0xED4245
                )
            )
            return

        view = PassSelectView(passes, self.user_id)
        await it.edit_original_response(view=view)

# ─────────────────────────────────────────
# 모달
# ─────────────────────────────────────────

class NicknameSearchModal(ui.Modal, title="유저 검색"):

    nick_input = ui.TextInput(
        label="로블록스 닉네임",
        placeholder="로블록스 닉네임을 정확하게 입력해주세요",
        required=True,
        max_length=20,
    )

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)
        loop = asyncio.get_running_loop()
        api = RobloxAPI()

        user_id = await loop.run_in_executor(None, api.get_user_id, self.nick_input.value.strip())
        if not user_id:
            await it.followup.send(
                view=await get_container_view("<:downvote:1489930277450158080>  실패", "-# - 유저를 찾을 수 없습니다", 0xED4245),
                ephemeral=True
            )
            return

        places = await loop.run_in_executor(None, api.get_user_places, user_id)
        if not places:
            await it.followup.send(
                view=await get_container_view("<:downvote:1489930277450158080>  결과 없음", "-# - 공개된 게임이 없습니다", 0xED4245),
                ephemeral=True
            )
            return

        view = PlaceSelectView(places, it.user.id)
        await it.followup.send(view=view, ephemeral=True)


class GiftModal(ui.Modal, title="글로벌 선물 방식"):

    roblox_name = ui.TextInput(
        label="로블록스 닉네임",
        placeholder="선물받을 유저의 닉네임을 입력하세요",
        required=True,
        max_length=20,
    )

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)

        target_name = self.roblox_name.value.strip()
        loop = asyncio.get_running_loop()
        api = RobloxAPI()
        target_id = await loop.run_in_executor(None, api.get_user_id, target_name)

        if not target_id:
            await it.followup.send(
                view=await get_container_view("<:downvote:1489930277450158080>  실패", "-# - 유저를 찾을 수 없습니다", 0xED4245),
                ephemeral=True
            )
            return

        view = ui.LayoutView(timeout=60)
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            f"### <:acy2:1489883409001091142>  글로벌 선물 방식\n"
            f"-# - **선물 대상**: {target_name}\n"
            f"-# - 선물할 게임을 선택해주세요"
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        select = ui.Select(
            placeholder="게임을 선택해주세요",
            custom_id=str(uuid.uuid4()).replace("-", "")[:40]
        )
        for name, place_id in GIFT_GAMES:
            select.add_option(label=name, value=place_id)

        async def on_game_select(interaction: discord.Interaction):
            selected_place_id = interaction.data["values"][0]
            game_name = next((n for n, u in GIFT_GAMES if u == selected_place_id), "알 수 없음")

            loading_view = ui.LayoutView(timeout=60)
            loading_con = ui.Container()
            loading_con.accent_color = 0x5865F2
            loading_con.add_item(ui.TextDisplay(
                f"### <a:1792loading:1487444148716965949>  불러오는 중\n"
                f"-# - **선물 대상**: {target_name}\n"
                f"-# - **게임**: {game_name}\n"
                f"-# - 게임패스 목록을 불러오는 중입니다"
            ))
            loading_view.add_item(loading_con)
            await interaction.response.edit_message(view=loading_view)

            def get_universe_and_passes(place_id):
                import requests as req
                resp = req.get(
                    f"https://apis.roproxy.com/universes/v1/places/{place_id}/universe",
                    timeout=10
                )
                if resp.status_code != 200:
                    return None
                universe_id = resp.json().get("universeId")
                if not universe_id:
                    return None
                return api.get_place_gamepasses(universe_id)

            passes = await loop.run_in_executor(None, get_universe_and_passes, selected_place_id)

            if not passes:
                fail_view = ui.LayoutView(timeout=60)
                fail_con = ui.Container()
                fail_con.accent_color = 0xED4245
                fail_con.add_item(ui.TextDisplay(
                    f"### <:downvote:1489930277450158080>  게임패스 없음\n"
                    f"-# - **게임**: {game_name}\n"
                    f"-# - 판매 중인 게임패스가 없습니다"
                ))
                fail_view.add_item(fail_con)
                await interaction.edit_original_response(view=fail_view)
                return

            pass_view = ui.LayoutView(timeout=60)
            pass_con = ui.Container()
            pass_con.accent_color = 0x5865F2
            pass_con.add_item(ui.TextDisplay(
                f"### <:acy2:1489883409001091142>  게임패스 선택\n"
                f"-# - **선물 대상**: {target_name}\n"
                f"-# - **게임**: {game_name}\n"
                f"-# - 선물할 게임패스를 선택해주세요"
            ))
            pass_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            pass_select = ui.Select(
                placeholder="게임패스를 선택해주세요",
                custom_id=str(uuid.uuid4()).replace("-", "")[:40]
            )
            for p in passes[:25]:
                pass_select.add_option(
                    label=f"{p.get('name', '이름없음')[:80]} ({p.get('price', 0):,} R$)",
                    value=str(p.get("id")),
                )

            async def on_pass_select(inter: discord.Interaction):
                selected_id = int(inter.data["values"][0])
                pass_data = next((p for p in passes if p.get("id") == selected_id), None)

                if not pass_data:
                    await inter.response.send_message(
                        view=await get_container_view("<:downvote:1489930277450158080>  오류", "-# - 오류가 발생했습니다", 0xED4245),
                        ephemeral=True
                    )
                    return

                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
                    r = cur.fetchone()
                    rate = int(r[0]) if r else 1000

                    cur.execute("SELECT value FROM config WHERE key = ?", (f"discount_{inter.user.id}",))
                    d = cur.fetchone()
                    discount = int(d[0]) if d else 0

                base_money = int((pass_data.get("price", 0) / rate) * 10000)
                final_money = int(base_money * (1 - discount / 100)) if discount > 0 else base_money

                discount_text = (
                    f"-# - **할인율**: {discount}%\n"
                    f"-# - **원래 가격**: ~~{base_money:,}원~~\n"
                    f"-# - **최종 가격**: {final_money:,}원"
                ) if discount > 0 else f"-# - **결제 금액**: {final_money:,}원"

                result_view = ui.LayoutView(timeout=60)
                result_con = ui.Container()
                result_con.accent_color = 0x5865F2
                result_con.add_item(ui.TextDisplay(
                    f"### <:acy2:1489883409001091142>  선물 정보 확인\n"
                    f"-# - **선물 대상**: {target_name}\n"
                    f"-# - **게임**: {game_name}\n"
                    f"-# - **게임패스**: {pass_data.get('name', '이름없음')}\n"
                    f"-# - **가격**: {pass_data.get('price', 0):,}로벅스\n"
                    f"{discount_text}"
                ))
                result_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

                proceed_btn = ui.Button(
                    label="진행하기",
                    style=discord.ButtonStyle.gray,
                    emoji="<:success:1489875582874554429>",
                    custom_id=str(uuid.uuid4()).replace("-", "")[:40]
                )

                async def on_proceed(proceed_inter: discord.Interaction):
                    await proceed_inter.response.edit_message(
                        view=await get_container_view(
                            "<a:1792loading:1487444148716965949>  게임 실행 중",
                            "-# - 봇이 게임에 접속중이니 기다려주세요",
                            0x5865F2
                        )
                    )

                    settings_path = os.path.expandvars(r"%LOCALAPPDATA%\Roblox\Versions")
                    try:
                        for ver in os.listdir(settings_path):
                            cfg_path = os.path.join(settings_path, ver, "ClientSettings", "ClientAppSettings.json")
                            os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
                            with open(cfg_path, "w") as f:
                                json.dump({
                                    "FFlagHandleAltEnterFullscreenManually": "False",
                                    "FFlagDebugFullscreenTitlebarRevamp": "False"
                                }, f)
                    except Exception:
                        pass

                    subprocess.Popen(["cmd", "/c", f"start roblox://experiences/start?placeId={selected_place_id}"])

                    await asyncio.sleep(8)

                    await proceed_inter.edit_original_response(
                        view=await get_container_view(
                            "게임 실행됨",
                            f"-# - **게임**: {game_name}\n"
                            f"-# - **선물 대상**: {target_name}",
                            0x57F287
                        )
                    )

                proceed_btn.callback = on_proceed
                result_con.add_item(ui.ActionRow(proceed_btn))
                result_view.add_item(result_con)
                await inter.response.edit_message(view=result_view)

            pass_select.callback = on_pass_select
            pass_con.add_item(ui.ActionRow(pass_select))
            pass_view.add_item(pass_con)
            await interaction.edit_original_response(view=pass_view)

        select.callback = on_game_select
        con.add_item(ui.ActionRow(select))
        view.add_item(con)
        await it.followup.send(view=view, ephemeral=True)


class CookieModal(ui.Modal, title="로블록스 쿠키 등록"):

    cookie_input = ui.TextInput(
        label="Cookie",
        placeholder="쿠키를 입력해주세요.",
        style=discord.TextStyle.long,
        required=True
    )

    async def on_submit(self, it: discord.Interaction):
        cookie = self.cookie_input.value
        is_success, result = get_roblox_data(cookie)

        if is_success:
            with sqlite3.connect(DATABASE) as conn:
                conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('roblox_cookie', ?)", (cookie,))
                conn.commit()
            con = create_container_msg(
                "<:upvote:1489930275868770305>  쿠키 등록 성공",
                f"-# - 계정에 접속을 성공했습니다\n - 현재 재고: **{result:,}로벅스**",
                0x57F287
            )
        else:
            con = create_container_msg(
                "<:downvote:1489930277450158080>  쿠키 등록 실패",
                f" - 인증에 실패하였습니다\n-# - 사유: `{result}`",
                0xED4245
            )

        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)


class RobuxCalculatorModal(ui.Modal, title="로벅스 가격 계산기"):

    robux_amount = ui.TextInput(
        label="구매할 로벅스 수량",
        placeholder="구매할 로벅스 수량을 적어주세요",
        min_length=1
    )

    async def on_submit(self, it: discord.Interaction):
        try:
            target_robux = int(self.robux_amount.value)

            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
                row = cur.fetchone()

            rate = int(row[0]) if row else 1300
            required_money = int((target_robux / rate) * 10000)

            con = ui.Container()
            con.accent_color = 0x5865F2
            con.add_item(ui.TextDisplay("### <:acy2:1489883409001091142>  계산 결과"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay(
                f"-# - **구매할 로벅스**: {target_robux:,}로벅스\n"
                f"-# - **현재 로벅스 가격**: 1.0 = {rate}로벅스\n"
                f"-# - **필요한 충전 금액**: {required_money:,}원"
            ))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("-# 계산된 금액만큼 충전 후 구매를 진행해주세요"))

            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

        except ValueError:
            await it.response.send_message(
                view=await get_container_view("<:downvote:1489930277450158080>  오류", "-# - 숫자만 정확히 입력해주세요", 0xED4245),
                ephemeral=True
            )
        except Exception as e:
            await it.response.send_message(
                view=await get_container_view("<:downvote:1489930277450158080>  오류", f"-# - 계산 중 오류가 발생했습니다: {e}", 0xED4245),
                ephemeral=True
            )

class CoinChargeModal(ui.Modal, title="코인 결제"):

    amount = ui.TextInput(
        label="충전 금액 (원)",
        placeholder="충전할 금액을 입력해주세요 (원)",
        min_length=3
    )

    def __init__(self, coin: str, coin_name: str, coin_symbol: str):
        super().__init__(title=f"코인 결제 - {coin_name}")
        self.coin = coin
        self.coin_name = coin_name
        self.coin_symbol = coin_symbol

    async def on_submit(self, it: discord.Interaction):

        try:
            krw_amount = int(self.amount.value.replace(",", ""))
        except ValueError:
            await it.response.send_message(
                view=await get_container_view("<:downvote:1489930277450158080>  오류", "-# - 숫자만 입력해주세요", 0xED4245),
                ephemeral=True
            )
            return

        await it.response.send_message(
            view=await get_container_view(
                "<a:1792loading:1487444148716965949>  결제 API 설정 중",
                "-# - 결제 주소를 생성하는 중입니다...",
                0x5865F2
            ),
            ephemeral=True
        )

        # NOWPayments API로 결제 주소 생성
        try:
            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT value FROM config WHERE key = 'nowpayments_key'")
                key_row = cur.fetchone()

            if not key_row:
                await it.edit_original_response(
                    view=await get_container_view("<:downvote:1489930277450158080>  오류", "-# - 코인 결제가 설정되지 않았습니다", 0xED4245)
                )
                return

            api_key = key_row[0]

            # 원화 → USD 환율 계산
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.exchangerate-api.com/v4/latest/KRW") as resp:
                    rate_data = await resp.json()
                    usd_rate = rate_data["rates"]["USD"]

            usd_amount = round(krw_amount * usd_rate, 2)

            # NOWPayments 결제 생성
            order_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.nowpayments.io/v1/payment",
                    headers={
                        "x-api-key": api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "price_amount": usd_amount,
                        "price_currency": "usd",
                        "pay_currency": self.coin,
                        "order_id": order_id,
                        "order_description": f"Robux {krw_amount}원 충전"
                    }
                ) as resp:
                    data = await resp.json()

            if "pay_address" not in data:
                await it.edit_original_response(
                    view=await get_container_view("<:downvote:1489930277450158080>  오류", f"-# - 결제 주소 생성 실패", 0xED4245)
                )
                return

            pay_address = data["pay_address"]
            pay_amount = data["pay_amount"]
            payment_id = data["payment_id"]

            # DB에 결제 정보 저장
            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'pending')",
                    (order_id, str(it.user.id), krw_amount, 0)
                )
                cur.execute(
                    "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                    (f"coin_payment_{payment_id}", f"{it.user.id}_{krw_amount}_{order_id}")
                )
                conn.commit()

            view = ui.LayoutView(timeout=None)
            con = ui.Container()
            con.accent_color = 0x5865F2
            fee_percent = COIN_FEE.get(self.coin, 0)
            final_amount = int(krw_amount * (1 - fee_percent / 100))

            con.add_item(ui.TextDisplay(
                f"### <:acy2:1489883409001091142>  코인 결제 정보\n"
                f"-# - **코인**: {self.coin_name} ({self.coin_symbol})\n"
                f"-# - **결제 금액**: {krw_amount:,}원\n"
                f"-# - **수수료**: {fee_percent}% (-{krw_amount - final_amount:,}원)\n"
                f"-# - **실제 충전**: {final_amount:,}원\n"
                f"-# - **결제 금액**: {pay_amount} {self.coin_symbol}\n"
                f"-# - **결제 주소**: `{pay_address}`\n"
                f"-# - **주문 ID**: `{order_id}`\n"
                f"-# 위 주소로 정확한 금액을 전송해주세요\n"
                f"-# 입금 확인까지 최대 10분 소요될 수 있습니다"
            ))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            copy_btn = ui.Button(
                label="주소 복사",
                style=discord.ButtonStyle.gray,
                emoji="<:success:1489875582874554429>"
            )

            async def copy_cb(inter: discord.Interaction):
                await inter.response.send_message(content=f"`{pay_address}`", ephemeral=True)

            copy_btn.callback = copy_cb
            con.add_item(ui.ActionRow(copy_btn))
            view.add_item(con)
            await it.edit_original_response(view=view)

            # 백그라운드에서 입금 확인
            asyncio.create_task(check_coin_payment(it, payment_id, krw_amount, order_id, self.coin_name, self.coin))

        except Exception as e:
            await it.edit_original_response(
                view=await get_container_view("<:downvote:1489930277450158080>  오류", f"-# - 오류가 발생했습니다: {e}", 0xED4245)
            )


async def check_coin_payment(it, payment_id, krw_amount, order_id, coin_name, coin_id):
    """백그라운드에서 코인 입금 확인"""

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'nowpayments_key'")
        key_row = cur.fetchone()

    if not key_row:
        return

    api_key = key_row[0]

    # 30분 동안 확인 (2분마다)
    for _ in range(15):
        await asyncio.sleep(120)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.nowpayments.io/v1/payment/{payment_id}",
                    headers={"x-api-key": api_key}
                ) as resp:
                    data = await resp.json()

            status = data.get("payment_status")

            if status in ("finished", "confirmed", "sending"):

                fee_percent = COIN_FEE.get(coin_id, 0)
                final_amount = int(krw_amount * (1 - fee_percent / 100))

                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?",
                        (str(it.user.id), final_amount, final_amount)
                    )
                    cur.execute("UPDATE orders SET status = 'charge' WHERE order_id = ?", (order_id,))
                    conn.commit()

                try:
                    log_view = ui.LayoutView(timeout=None)
                    log_con = ui.Container()
                    log_con.accent_color = 0x57F287
                    log_con.add_item(ui.TextDisplay(
                        f"### <:acy2:1489883409001091142>  코인 충전 로그\n"
                        f"-# - **유저**: {it.user.mention}\n"
                        f"-# - **코인**: {coin_name}\n"
                        f"-# - **결제 금액**: {krw_amount:,}원\n"
                        f"-# - **수수료**: {fee_percent}% (-{krw_amount - final_amount:,}원)\n"
                        f"-# - **실제 충전**: {final_amount:,}원\n"
                        f"-# - **주문 ID**: `{order_id}`\n"
                        f"-# - **상태**: 자동 승인"
                    ))
                    approve_btn = ui.Button(label="승인됨", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>", disabled=True)
                    log_con.add_item(ui.ActionRow(approve_btn))
                    log_view.add_item(log_con)
                    await send_log("charge_log", log_view)
                except Exception as e:
                    print(f"[코인충전로그 실패] {e}")

                try:
                    await it.edit_original_response(
                        view=await get_container_view(
                            "<:upvote:1489930275868770305>  충전 완료",
                            f"-# - **코인**: {coin_name}\n"
                            f"-# - **결제 금액**: {krw_amount:,}원\n"
                            f"-# - **수수료**: {fee_percent}% (-{krw_amount - final_amount:,}원)\n"
                            f"-# - **실제 충전**: {final_amount:,}원\n"
                            f"-# - **주문 ID**: `{order_id}`",
                            0x57F287
                        )
                    )
                except Exception:
                    pass

                try:
                    await it.user.send(
                        f"<:acy2:1489883409001091142> **코인 충전 완료**\n"
                        f"- 코인: {coin_name}\n"
                        f"- 충전 금액: {krw_amount:,}원\n"
                        f"- 주문 ID: `{order_id}`"
                    )
                except Exception:
                    pass

                return

            elif status == "failed" or status == "expired":
                try:
                    await it.edit_original_response(
                        view=await get_container_view(
                            "<:downvote:1489930277450158080>  결제 실패",
                            f"-# - 결제가 실패하거나 만료되었습니다\n-# - 다시 시도해주세요",
                            0xED4245
                        )
                    )
                except Exception:
                    pass
                return

        except Exception as e:
            print(f"[코인결제 확인 실패] {e}")

    try:
        await it.edit_original_response(
            view=await get_container_view(
                "<:downvote:1489930277450158080>  시간 초과",
                "-# - 30분 내에 입금이 확인되지 않았습니다\n-# - 입금하셨다면 관리자에게 문의해주세요",
                0xED4245
            )
        )
    except Exception:
        pass

class ChargeModal(ui.Modal, title="계좌이체 충전 신청"):

    depositor = ui.TextInput(label="입금자명", placeholder="입금자명을 입력해주세요", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전 금액", placeholder="숫자만 입력해주세요", min_length=3)

    async def copy_callback(self, it: discord.Interaction):
        await it.response.send_message(content=f"`{BANK_K}`", ephemeral=True)

    async def on_submit(self, it: discord.Interaction):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### <a:1792loading:1487444148716965949>  충전 준비 중\n-# - **충전 서버 API** 연결 시도중 (1/3)"))
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        msg = await it.original_response()

        steps = [
            "-# - **입금자명/충전금액** 설정 중 (2/3)",
            "-# - **안전한 충전**을 위한 설정 중 (3/3)",
            "-# - **모든 설정이 완료되었습니다**"
        ]
        for step in steps:
            await asyncio.sleep(1.5)
            con.clear_items()
            con.add_item(ui.TextDisplay(f"### <a:1792loading:1487444148716965949>  충전 준비 중\n{step}"))
            await msg.edit(view=ui.LayoutView().add_item(con))

        await asyncio.sleep(1)
        con.clear_items()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### <a:1792loading:1487444148716965949>  입금 대기 중"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay(
            f"-# - **입금자명**은 반드시 본인 실명으로 입력해주세요\n"
            f"-# - 입금 대기 시간은 **5분**입니다\n"
            f"-# - 충전 처리는 입금 후 **최대 2~3분**까지 걸립니다\n"
            f"-# - **5분 지나고 입금할 시 충전 안됩니다**"
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay(
            f"-# - **입금 계좌**: {BANK_K}\n"
            f"-# - **입금 금액**: {int(self.amount.value):,}원\n"
            f"-# - **입금자명**: {self.depositor.value}"
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        copy_btn = ui.Button(label="계좌복사", style=discord.ButtonStyle.gray, emoji="<:success:1489875582874554429>")
        copy_btn.callback = self.copy_callback
        con.add_item(ui.ActionRow(copy_btn))
        await msg.edit(view=ui.LayoutView().add_item(con))

        log_msg = None
        try:
            log_view = ui.LayoutView(timeout=None)
            log_con = ui.Container()
            log_con.accent_color = 0x5865F2
            log_con.add_item(ui.TextDisplay(
                f"### <:acy2:1489883409001091142>  충전 신청\n"
                f"-# - **유저**: {it.user.mention}\n"
                f"-# - **입금자명**: `{self.depositor.value}`\n"
                f"-# - **충전 금액**: {int(self.amount.value):,}원\n"
                f"-# - **상태**: 입금 대기 중"
            ))
            log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            approve_btn = ui.Button(
                label="승인",
                style=discord.ButtonStyle.gray,
                emoji="<:upvote:1489930275868770305>",
                custom_id=f"approve_{it.user.id}_{self.amount.value}"
            )
            reject_btn = ui.Button(
                label="거부",
                style=discord.ButtonStyle.gray,
                emoji="<:downvote:1489930277450158080>",
                custom_id=f"reject_{it.user.id}_{self.amount.value}"
            )

            async def on_approve(inter: discord.Interaction):
                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?",
                        (str(it.user.id), int(self.amount.value), int(self.amount.value))
                    )
                    cur.execute(
                        "INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'charge')",
                        ("".join(random.choices(string.ascii_uppercase + string.digits, k=10)), str(it.user.id), int(self.amount.value), 0)
                    )
                    conn.commit()

                done_view = ui.LayoutView(timeout=None)
                done_con = ui.Container()
                done_con.accent_color = 0x57F287
                done_con.add_item(ui.TextDisplay(
                    f"### <:acy2:1489883409001091142>  충전 승인\n"
                    f"-# - **유저**: {it.user.mention}\n"
                    f"-# - **입금자명**: `{self.depositor.value}`\n"
                    f"-# - **충전 금액**: {int(self.amount.value):,}원\n"
                    f"-# - **상태**: 승인됨\n"
                    f"-# - **처리자**: {inter.user.mention}"
                ))
                done_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                done_btn1 = ui.Button(label="승인됨", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>", disabled=True)
                done_con.add_item(ui.ActionRow(done_btn1))
                done_view.add_item(done_con)
                await inter.response.edit_message(view=done_view)

                try:
                    await it.user.send(f"<:acy2:1489883409001091142> **충전이 승인되었습니다**\n- 충전 금액: {int(self.amount.value):,}원")
                except Exception:
                    pass

            async def on_reject(inter: discord.Interaction):
                done_view = ui.LayoutView(timeout=None)
                done_con = ui.Container()
                done_con.accent_color = 0xED4245
                done_con.add_item(ui.TextDisplay(
                    f"### <:downvote:1489930277450158080>  충전 거부\n"
                    f"-# - **유저**: {it.user.mention}\n"
                    f"-# - **입금자명**: `{self.depositor.value}`\n"
                    f"-# - **충전 금액**: {int(self.amount.value):,}원\n"
                    f"-# - **상태**: 거부됨\n"
                    f"-# - **처리자**: {inter.user.mention}"
                ))
                done_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                done_btn2 = ui.Button(label="거부됨", style=discord.ButtonStyle.gray, emoji="<:downvote:1489930277450158080>", disabled=True)
                done_con.add_item(ui.ActionRow(done_btn2))
                done_view.add_item(done_con)
                await inter.response.edit_message(view=done_view)

                try:
                    await it.user.send(f"<:downvote:1489930277450158080> **충전이 거부되었습니다**\n- 충전 금액: {int(self.amount.value):,}원")
                except Exception:
                    pass

            approve_btn.callback = on_approve
            reject_btn.callback = on_reject
            log_con.add_item(ui.ActionRow(approve_btn, reject_btn))
            log_view.add_item(log_con)

            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT value FROM config WHERE key = 'charge_log'")
                row = cur.fetchone()

            if row:
                channel = bot.get_channel(int(row[0]))
                if channel:
                    log_msg = await channel.send(view=log_view)

        except Exception as e:
            print(f"[충전로그 실패] {e}")

        # 기존 입금 대기
        key = f"{self.depositor.value}_{self.amount.value}"
        success = False
        for _ in range(60):
            if pending_deposits.get(key):
                success = True
                del pending_deposits[key]
                break
            await asyncio.sleep(5)

        con.clear_items()
        if success:
            con.accent_color = 0x5865F2
            con.add_item(ui.TextDisplay("### <a:1792loading:1487444148716965949>  충전 처리 중\n-# - 유저 **DB에 충전 기록** 저장 중 (1/2)"))
            await msg.edit(view=ui.LayoutView().add_item(con))
            await asyncio.sleep(1.5)

            con.clear_items()
            con.add_item(ui.TextDisplay("### <a:1792loading:1487444148716965949>  충전 처리 중\n-# - 입금 **금액 반영** 중 (2/2)"))
            await msg.edit(view=ui.LayoutView().add_item(con))

            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?",
                    (str(it.user.id), int(self.amount.value), int(self.amount.value))
                )
                cur.execute(
                    "INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'charge')",
                    ("".join(random.choices(string.ascii_uppercase + string.digits, k=10)), str(it.user.id), int(self.amount.value), 0)
                )
                conn.commit()

            await asyncio.sleep(1.5)
            con.clear_items()
            con.accent_color = 0x57F287
            con.add_item(ui.TextDisplay("### <:upvote:1489930275868770305>  충전 완료"))
            con.add_item(ui.TextDisplay(f"-# - 잔액이 성공적으로 충전되었습니다\n-# - **충전 금액:** `{int(self.amount.value):,}원`"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("-# 정보 버튼을 눌러 잔액을 확인하세요!"))

            # ✅ 자동충전 성공 시 로그 버튼 비활성화
            if log_msg:
                try:
                    done_view = ui.LayoutView(timeout=None)
                    done_con = ui.Container()
                    done_con.accent_color = 0x57F287
                    done_con.add_item(ui.TextDisplay(
                        f"### <:acy2:1489883409001091142>  충전 로그\n"
                        f"-# - **유저**: {it.user.mention}\n"
                        f"-# - **입금자명**: `{self.depositor.value}`\n"
                        f"-# - **충전 금액**: {int(self.amount.value):,}원\n"
                        f"-# - **상태**: 자동 승인됨"
                    ))
                    done_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    done_btn1 = ui.Button(label="승인됨", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>", disabled=True)
                    done_btn2 = ui.Button(label="거부", style=discord.ButtonStyle.gray, emoji="<:downvote:1489930277450158080>", disabled=True)
                    done_con.add_item(ui.ActionRow(done_btn1, done_btn2))
                    done_view.add_item(done_con)
                    await log_msg.edit(view=done_view)
                except Exception as e:
                    print(f"[로그 업데이트 실패] {e}")

        else:
            con.accent_color = 0xED4245
            con.add_item(ui.TextDisplay("### <:downvote:1489930277450158080>  충전 실패"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("-# - 시간 내에 입금이 확인되지 않았습니다\n-# - 다시 충전 신청을 해주세요"))

        await msg.edit(view=ui.LayoutView().add_item(con))

# ─────────────────────────────────────────
# 자판기 뷰
# ─────────────────────────────────────────

class RobuxVending(ui.LayoutView):

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def build_main_menu(self):
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
            c_row = cur.fetchone()
            cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
            r_row = cur.fetchone()

        cookie = c_row[0] if c_row else None
        rate = r_row[0] if r_row else "1300"

        success, result = get_roblox_data(cookie)
        stock_display = f"{result:,}" if success else "점검 중"

        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### <:acy2:1489883409001091142>  실시간 재고 - 가격"))

        stock_button = ui.Button(
            label=f"{stock_display}로벅스",
            style=discord.ButtonStyle.gray,
            disabled=True,
            emoji="<:emoji_19:1487441741484392498>"
        )
        price_button = ui.Button(
            label=f"1.0 = {rate}로벅스",
            style=discord.ButtonStyle.gray,
            disabled=True,
            emoji="<:emoji_19:1487441741484392498>"
        )
        con.add_item(ui.ActionRow(stock_button))
        con.add_item(ui.ActionRow(price_button))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay("### <:acy2:1489883409001091142>  지급방식"))
        con.add_item(ui.TextDisplay(
            "-# - **게임패스 방식** / 무조건 본인 게임만 가능\n"
            "-# - **글로벌 선물 방식** / 예시: 라이벌 - 번들\n"
            "-# - **그룹 지급 방식** / 그룹 2주 동안 참가시 가능"
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        charge = ui.Button(label="충전", custom_id="charge", style=discord.ButtonStyle.blurple)
        charge.callback = self.main_callback

        info = ui.Button(label="정보", custom_id="info", style=discord.ButtonStyle.blurple)
        info.callback = self.info_callback

        shop = ui.Button(label="구매", custom_id="buying", style=discord.ButtonStyle.blurple)
        shop.callback = self.shop_callback

        calc = ui.Button(label="계산", custom_id="calc", style=discord.ButtonStyle.blurple)
        calc.callback = self.calc_callback

        con.add_item(ui.ActionRow(charge, info, shop, calc))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay("-# © 2026 Robux Vending All rights reserved"))
        self.clear_items()
        self.add_item(con)
        return con

    async def calc_callback(self, it: discord.Interaction):
        await it.response.send_modal(RobuxCalculatorModal())

    async def shop_callback(self, it: discord.Interaction):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            "### <:acy2:1489883409001091142>  구매 방식 선택\n"
            "-# - 원하시는 구매 방식을 선택해주세요\n"
            "-# - 현재는 **게임패스, 글로벌**만 지원됩니다"
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        btn_gp = ui.Button(label="게임패스", style=discord.ButtonStyle.gray, emoji="<:opt_online:1489872305138962452>")
        btn_ingame = ui.Button(label="글로벌", style=discord.ButtonStyle.gray, emoji="<:opt_online:1489872305138962452>")
        btn_group = ui.Button(label="그룹", style=discord.ButtonStyle.gray, emoji="<:opt_offline:1489886702368723087>", disabled=True)

        btn_gp.callback = lambda i: i.response.send_modal(NicknameSearchModal())
        btn_ingame.callback = lambda i: i.response.send_modal(GiftModal())

        async def group_cb(interaction: discord.Interaction):
            await interaction.response.send_message(
                view=await get_container_view("<:downvote:1489930277450158080>  준비 중", "-# - 그룹 지급 방식은 준비 중입니다", 0xED4245),
                ephemeral=True
            )

        btn_group.callback = group_cb
        con.add_item(ui.ActionRow(btn_gp, btn_ingame, btn_group))

        new_view = ui.LayoutView(timeout=None)
        new_view.add_item(con)
        await it.response.send_message(view=new_view, ephemeral=True)

    async def info_callback(self, it: discord.Interaction):
        u_id = str(it.user.id)
        money = 0
        used_money = 0
        discount = 0

        try:
            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
                row = cur.fetchone()
                if row:
                    money = row[0]

                cur.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM orders WHERE user_id = ? AND status = 'completed'",
                    (u_id,)
                )
                used_row = cur.fetchone()
                if used_row:
                    used_money = used_row[0]

                cur.execute("SELECT value FROM config WHERE key = ?", (f"discount_{u_id}",))
                disc_row = cur.fetchone()
                if disc_row:
                    discount = int(disc_row[0])
        except Exception:
            pass

        roles = [role.name for role in it.user.roles if role.name != "@everyone"]
        role_grade = roles[-1] if roles else "Guest"

        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(f"### <:acy2:1489883409001091142>  {it.user.display_name} 님의 정보"))
        con.add_item(ui.TextDisplay(
            f"-# - **보유 잔액:** `{money:,}원`\n"
            f"-# - **사용 금액:** `{used_money:,}원`\n"
            f"-# - **역할 등급:** `{role_grade}`\n"
            f"-# - **할인 혜택:** `{discount}%`"
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        select = ui.Select(
            placeholder="조회할 내역 선택해주세요",
            options=[
                discord.SelectOption(label="최근 충전 내역", value="charge"),
                discord.SelectOption(label="최근 구매 내역", value="purchase")
            ]
        )

        async def res_cb(i: discord.Interaction):
            selected = select.values[0]
            try:
                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    if selected == "charge":
                        cur.execute(
                            "SELECT amount, created_at FROM orders WHERE user_id = ? AND status = 'charge' ORDER BY created_at DESC LIMIT 5",
                            (u_id,)
                        )
                        rows = cur.fetchall()
                        if not rows:
                            await i.response.send_message(
                                view=await get_container_view("최근 충전 내역", "-# - 충전 내역이 없습니다", 0x5865F2),
                                ephemeral=True
                            )
                            return
                        text = "### <:acy2:1489883409001091142>  최근 충전 내역\n"
                        for row in rows:
                            text += f"-# - `{row[1][:10]}` | **+{row[0]:,}원**\n"
                    else:
                        cur.execute(
                            "SELECT order_id, amount, created_at FROM orders WHERE user_id = ? AND status = 'completed' ORDER BY created_at DESC LIMIT 5",
                            (u_id,)
                        )
                        rows = cur.fetchall()
                        if not rows:
                            await i.response.send_message(
                                view=await get_container_view("최근 구매 내역", "-# - 구매 내역이 없습니다", 0x5865F2),
                                ephemeral=True
                            )
                            return
                        text = "### <:acy2:1489883409001091142>  최근 구매 내역\n"
                        for row in rows:
                            text += f"-# - `{row[2][:10]}` | **{row[1]:,}원** | `{row[0]}`\n"
            except Exception:
                await i.response.send_message(
                    view=await get_container_view("<:downvote:1489930277450158080>  오류", "-# - 내역을 불러올 수 없습니다", 0xED4245),
                    ephemeral=True
                )
                return

            result_view = ui.LayoutView(timeout=60)
            result_con = ui.Container()
            result_con.accent_color = 0x5865F2
            result_con.add_item(ui.TextDisplay(text))
            result_view.add_item(result_con)
            await i.response.send_message(view=result_view, ephemeral=True)

        select.callback = res_cb
        con.add_item(ui.ActionRow(select))
        await it.response.send_message(view=ui.LayoutView(timeout=60).add_item(con), ephemeral=True)

    async def main_callback(self, it: discord.Interaction):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            "### <:acy2:1489883409001091142>  충전 수단\n"
            "-# - 원하시는 **충전 방식**을 선택해주세요\n"
            "-# - 현재 가능한 결제 수단은 **계좌이체, 코인결제**"
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        btn_bank = ui.Button(label="계좌이체", style=discord.ButtonStyle.gray, emoji="<:opt_online:1489872305138962452>")
        btn_coin = ui.Button(label="코인결제", style=discord.ButtonStyle.gray, emoji="<:opt_online:1489872305138962452>")

        async def bank_cb(i: discord.Interaction):
            await i.response.send_modal(ChargeModal())

        async def coin_cb(i: discord.Interaction):
            view = ui.LayoutView(timeout=60)
            con = ui.Container()
            con.accent_color = 0x5865F2
            con.add_item(ui.TextDisplay(
                "### <:acy2:1489883409001091142>  코인 결제\n"
                "-# - 결제할 코인을 선택해주세요"
            ))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            select = ui.Select(
                placeholder="코인을 선택해주세요",
                custom_id=str(uuid.uuid4()).replace("-", "")[:40]
            )
            select.add_option(label="라이트코인 (LTC)", value="ltc", emoji="<:ltc:1490718663534444667>")
            select.add_option(label="트론 (TRX)", value="trx", emoji="<:trx:1490718665216233605>")
            select.add_option(label="비트코인 (BTC)", value="btc", emoji="<:btc:1490718661982421105>")
            select.add_option(label="솔라나 (SOL)", value="sol", emoji="<:sol:1490718660275212491>")

            async def on_coin_select(inter: discord.Interaction):
                coin = inter.data["values"][0]
                coin_name = COIN_LIST[coin][0]
                coin_symbol = COIN_LIST[coin][1]

                await inter.response.send_modal(CoinChargeModal(coin, coin_name, coin_symbol))

            select.callback = on_coin_select
            con.add_item(ui.ActionRow(select))
            view.add_item(con)
            await i.response.send_message(view=view, ephemeral=True)

        btn_bank.callback = bank_cb
        btn_coin.callback = coin_cb
        con.add_item(ui.ActionRow(btn_bank, btn_coin))
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

# ─────────────────────────────────────────
# 봇
# ─────────────────────────────────────────

class MyBot(commands.Bot):

    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.vending_msg_info = {}

    async def setup_hook(self):
        self.stock_updater.start()
        await self.tree.sync()

        try:
            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT channel_id, msg_id FROM vending_messages")
                rows = cur.fetchall()

            for channel_id, msg_id in rows:
                self.vending_msg_info[int(channel_id)] = int(msg_id)

                view = RobuxVending(self)
                await view.build_main_menu()
                self.add_view(view)

            print(f"[자판기] {len(rows)}개 복구됨")
        except Exception as e:
            print(f"[자판기 복구 실패] {e}")

    @tasks.loop(minutes=2.0)
    async def stock_updater(self):

        try:
            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
                cookie_row = cur.fetchone()
                cur.execute("SELECT value FROM config WHERE key = 'last_robux'")
                last_row = cur.fetchone()
                cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
                admin_row = cur.fetchone()
                cur.execute("SELECT value FROM config WHERE key = 'cookie_alert_sent'")
                alert_row = cur.fetchone()

            cookie = cookie_row[0] if cookie_row else None
            is_valid, current_robux = get_roblox_data(cookie)
            last_robux = int(last_row[0]) if last_row else 0

            if is_valid:
                if alert_row and alert_row[0] == "1":
                    with sqlite3.connect(DATABASE) as conn:
                        cur = conn.cursor()
                        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('cookie_alert_sent', '0')")
                        conn.commit()

                if current_robux > last_robux and last_robux > 0:
                    try:
                        with sqlite3.connect(DATABASE) as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT value FROM config WHERE key = 'stock_log'")
                            stock_row = cur.fetchone()

                        if stock_row:
                            stock_channel = self.get_channel(int(stock_row[0]))
                            if stock_channel:
                                added = current_robux - last_robux
                                embed = discord.Embed(
                                    title=f"<:acy2:1489883409001091142>  {added:,}로벅스 입고",
                                    description=f"원래 재고: {last_robux:,}로벅스 → 현재 재고: {current_robux:,}로벅스",
                                    color=0x5865F2
                                )
                                await stock_channel.send(content="@everyone", embed=embed)
                    except Exception as e:
                        print(f"[재고로그 실패] {e}")

                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT OR REPLACE INTO config (key, value) VALUES ('last_robux', ?)",
                        (str(current_robux),)
                    )
                    conn.commit()

            else:
                if not alert_row or alert_row[0] == "0":
                    if admin_row:
                        try:
                            admin = await self.fetch_user(int(admin_row[0]))
                            if admin:
                                await admin.send(
                                    f"<:downvote:1489930277450158080> **쿠키 만료 감지**\n"
                                    f"- 사유: {current_robux}\n"
                                    f"- `/쿠키등록` 으로 쿠키를 갱신해주세요"
                                )
                        except Exception:
                            pass
                    with sqlite3.connect(DATABASE) as conn:
                        cur = conn.cursor()
                        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('cookie_alert_sent', '1')")
                        conn.commit()

        except Exception as e:
            print(f"[재고감지 실패] {e}")

        if not self.vending_msg_info:
            return
        for channel_id, msg_id in list(self.vending_msg_info.items()):
            try:
                channel = self.get_channel(channel_id)
                if not channel:
                    continue
                msg = await channel.fetch_message(msg_id)
                view = RobuxVending(self)
                con = await view.build_main_menu()
                await msg.edit(view=ui.LayoutView(timeout=None).add_item(con))
            except Exception as e:
                print(f"Update Error: {e}")

bot = MyBot()

# ─────────────────────────────────────────
# 슬래시 커맨드
# ─────────────────────────────────────────

@bot.tree.command(name="자판기", description="로벅스 자판기를 전송합니다")
async def spawn_vending(it: discord.Interaction):
    await it.response.send_message(
        view=await get_container_view("<:acy2:1489883409001091142>  자판기", "-# - 자판기가 전송되었습니다", 0x5865F2),
        ephemeral=True
    )
    view = RobuxVending(bot)
    con = await view.build_main_menu()
    msg = await it.channel.send(view=ui.LayoutView().add_item(con))
    bot.vending_msg_info[it.channel_id] = msg.id

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO vending_messages (channel_id, msg_id) VALUES (?, ?)",
            (str(it.channel_id), str(msg.id))
        )
        conn.commit()

@bot.tree.command(name="쿠키등록", description="로블록스 쿠키를 등록합니다")
@app_commands.checks.has_permissions(administrator=True)
async def set_cookie(it: discord.Interaction):
    await it.response.send_modal(CookieModal())


@bot.tree.command(name="가격설정", description="로벅스 가격을 설정합니다")
@app_commands.describe(수량="1.0당 지급할 로벅스 양 (예: 1300)")
@app_commands.checks.has_permissions(administrator=True)
async def set_rate(it: discord.Interaction, 수량: int):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('robux_rate', ?)", (str(수량),))
        conn.commit()
    await it.response.send_message(
        view=await get_container_view("<:acy2:1489883409001091142>  가격 설정 완료", f"-# - 1.0당 {수량:,}로벅스로 설정되었습니다", 0x5865F2),
        ephemeral=True
    )


@bot.tree.command(name="관리자설정", description="관리자 ID를 설정합니다")
async def 관리자설정(it: discord.Interaction):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('admin_id', ?)", (str(it.user.id),))
        conn.commit()
    await it.response.send_message(
        view=await get_container_view("<:acy2:1489883409001091142>  설정 완료", "-# - 관리자로 설정되었습니다", 0x5865F2),
        ephemeral=True
    )


@bot.tree.command(name="수동충전", description="유저 잔액을 수동으로 조정합니다")
@app_commands.describe(유저="대상 디스코드 유저", 금액="충전/차감할 금액", 여부="추가 또는 차감")
@app_commands.choices(여부=[
    app_commands.Choice(name="추가", value="추가"),
    app_commands.Choice(name="차감", value="차감"),
])
async def 수동충전(it: discord.Interaction, 유저: discord.Member, 금액: int, 여부: app_commands.Choice[str]):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    if 금액 <= 0:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  오류", "-# - 금액은 1원 이상이어야 합니다", 0xED4245),
            ephemeral=True
        )
        return

    user_id = str(유저.id)

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        current = cur.fetchone()[0]

        if 여부.value == "추가":
            new_balance = current + 금액
            cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (금액, user_id))
            action_text = f"+{금액:,}원 추가"
            color = 0x5865F2
        else:
            if current < 금액:
                await it.response.send_message(
                    view=await get_container_view(
                        "<:downvote:1489930277450158080>  잔액 부족",
                        f"-# - 현재 잔액: {current:,}원\n-# - 차감 금액: {금액:,}원",
                        0xED4245
                    ),
                    ephemeral=True
                )
                return
            new_balance = current - 금액
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (금액, user_id))
            action_text = f"-{금액:,}원 차감"
            color = 0xED4245

        cur.execute(
            "INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'charge')",
            ("".join(random.choices(string.ascii_uppercase + string.digits, k=10)), user_id, 금액, 0)
        )
        conn.commit()

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(
        f"### <:acy2:1489883409001091142>  수동 충전 완료\n"
        f"-# - **대상 유저**: {유저.mention}\n"
        f"-# - **처리 내용**: {action_text}\n"
        f"-# - **이전 잔액**: {current:,}원\n"
        f"-# - **변경 후 잔액**: {new_balance:,}원\n"
        f"-# - **처리자**: {it.user.mention}"
    ))
    view.add_item(con)
    await it.response.send_message(view=view, ephemeral=True)

    try:
        log_view = ui.LayoutView(timeout=None)
        log_con = ui.Container()
        log_con.accent_color = 0x5865F2
        log_con.add_item(ui.TextDisplay(
            f"### <:acy2:1489883409001091142>  수동충전 로그\n"
            f"-# - **대상**: {유저.mention}\n"
            f"-# - **처리**: {action_text}\n"
            f"-# - **이전 잔액**: {current:,}원\n"
            f"-# - **변경 후 잔액**: {new_balance:,}원\n"
            f"-# - **처리자**: {it.user.mention}"
        ))
        log_view.add_item(log_con)
        await send_log("manual_charge_log", log_view)
    except Exception as e:
        print(f"[수동충전로그 실패] {e}")

@bot.tree.command(name="할인", description="유저 할인율을 설정합니다")
@app_commands.describe(유저="대상 디스코드 유저", 할인율="할인율 (0~100)")
async def 할인(it: discord.Interaction, 유저: discord.Member, 할인율: int):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    if 할인율 < 0 or 할인율 > 100:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  오류", "-# - 할인율은 0~100 사이여야 합니다", 0xED4245),
            ephemeral=True
        )
        return

    with sqlite3.connect(DATABASE) as conn:
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (f"discount_{유저.id}", str(할인율)))
        conn.commit()

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = 0x5865F2
    con.add_item(ui.TextDisplay(
        f"### <:acy2:1489883409001091142>  할인율 설정 완료\n"
        f"-# - **대상 유저**: {유저.mention}\n"
        f"-# - **할인율**: {할인율}%\n"
        f"-# - **처리자**: {it.user.mention}"
    ))
    view.add_item(con)
    await it.response.send_message(view=view, ephemeral=True)

    try:
        log_view = ui.LayoutView(timeout=None)
        log_con = ui.Container()
        log_con.accent_color = 0x5865F2
        log_con.add_item(ui.TextDisplay(
            f"### <:acy2:1489883409001091142>  할인 설정 로그\n"
            f"-# - **대상**: {유저.mention}\n"
            f"-# - **할인율**: {할인율}%\n"
            f"-# - **처리자**: {it.user.mention}"
        ))
        log_view.add_item(log_con)
        await send_log("discount_log", log_view)
    except Exception as e:
        print(f"[할인로그 실패] {e}")

@bot.tree.command(name="잔액조회", description="특정 유저의 잔액을 확인합니다")
@app_commands.describe(유저="조회할 디스코드 유저")
async def 잔액조회(it: discord.Interaction, 유저: discord.Member):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()

        cur.execute("SELECT balance FROM users WHERE user_id = ?", (str(유저.id),))
        row = cur.fetchone()
        balance = row[0] if row else 0

        cur.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM orders WHERE user_id = ? AND status = 'completed'",
            (str(유저.id),)
        )
        used = cur.fetchone()[0]

        cur.execute("SELECT value FROM config WHERE key = ?", (f"discount_{유저.id}",))
        d = cur.fetchone()
        discount = int(d[0]) if d else 0

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = 0x5865F2
    con.add_item(ui.TextDisplay(
        f"### <:acy2:1489883409001091142>  {유저.display_name} 잔액 조회\n"
        f"-# - **보유 잔액**: `{balance:,}원`\n"
        f"-# - **누적 사용**: `{used:,}원`\n"
        f"-# - **할인율**: `{discount}%`\n"
        f"-# - **조회자**: {it.user.mention}"
    ))
    view.add_item(con)
    await it.response.send_message(view=view, ephemeral=True)


@bot.tree.command(name="주문조회", description="특정 유저의 전체 주문 내역을 확인합니다")
@app_commands.describe(유저="조회할 디스코드 유저", 페이지="페이지 번호 (기본: 1)")
async def 주문조회(it: discord.Interaction, 유저: discord.Member, 페이지: int = 1):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    limit = 10
    offset = (페이지 - 1) * limit

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()

        cur.execute(
            "SELECT order_id, amount, status, created_at FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (str(유저.id), limit, offset)
        )
        rows = cur.fetchall()

        cur.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?", (str(유저.id),))
        total = cur.fetchone()[0]

    if not rows:
        await it.response.send_message(
            view=await get_container_view("<:acy2:1489883409001091142>  주문 없음", "-# - 주문 내역이 없습니다", 0x5865F2),
            ephemeral=True
        )
        return

    total_pages = (total + limit - 1) // limit
    status_map = {"completed": "<:upvote:1489930275868770305> 완료", "failed": "<:downvote:1489930277450158080> 실패", "pending": "대기", "charge": "충전"}

    text = (
        f"### <:acy2:1489883409001091142>  {유저.display_name} 주문 내역\n"
        f"-# - 총 {total}건 | {페이지}/{total_pages} 페이지\n"
    )
    for row in rows:
        status_text = status_map.get(row[2], row[2])
        text += f"-# - `{row[3][:10]}` | {status_text} | **{row[1]:,}원** | `{row[0]}`\n"

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = 0x5865F2
    con.add_item(ui.TextDisplay(text))
    view.add_item(con)
    await it.response.send_message(view=view, ephemeral=True)


@bot.tree.command(name="전체통계", description="전체 서비스 통계를 확인합니다")
async def 전체통계(it: discord.Interaction):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'charge'")
        total_charge = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'completed'")
        total_sales = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
        total_orders = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'failed'")
        total_failed = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'completed' AND DATE(created_at) = DATE('now')")
        today_sales = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'charge' AND DATE(created_at) = DATE('now')")
        today_charge = cur.fetchone()[0]

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = 0x5865F2
    con.add_item(ui.TextDisplay(f"### <:acy2:1489883409001091142>  전체 통계"))
    con.add_item(ui.TextDisplay(f"-# - **총 유저 수**: {total_users:,}명"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(f"-# - **총 충전 금액**: {total_charge:,}원\n-# - **총 매출**: {total_sales:,}원\n-# - **총 주문 수**: {total_orders:,}건\n-# - **총 실패 수**: {total_failed:,}건"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(f"-# - **오늘 충전**: {today_charge:,}원\n-# - **오늘 매출**: {today_sales:,}원\n"))
    view.add_item(con)
    await it.response.send_message(view=view, ephemeral=True)


@bot.tree.command(name="쿠키상태", description="현재 로블록스 쿠키 상태를 확인합니다")
async def 쿠키상태(it: discord.Interaction):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    await it.response.defer(ephemeral=True)

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        cookie_row = cur.fetchone()

    cookie = cookie_row[0] if cookie_row else None
    is_success, result = get_roblox_data(cookie)

    if is_success:
        view = await get_container_view(
            "<:upvote:1489930275868770305>  쿠키 정상",
            f"-# - 상태: 정상\n-# - 보유 로벅스: {result:,} R$",
            0x57F287
        )
    else:
        view = await get_container_view(
            "<:downvote:1489930277450158080>  쿠키 오류",
            f"-# - 상태: 만료 또는 오류\n-# - 사유: {result}",
            0xED4245
        )

    await it.followup.send(view=view, ephemeral=True)


@bot.tree.command(name="주문취소", description="특정 주문을 취소하고 잔액을 복구합니다")
@app_commands.describe(거래id="취소할 거래 ID")
async def 주문취소(it: discord.Interaction, 거래id: str):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id, amount, status FROM orders WHERE order_id = ?", (거래id,))
        order = cur.fetchone()

    if not order:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  오류", "-# - 해당 거래 ID를 찾을 수 없습니다", 0xED4245),
            ephemeral=True
        )
        return

    user_id, amount, status = order

    if status in ("failed", "charge"):
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  취소 불가", f"-# - 이미 {status} 상태인 주문입니다", 0xED4245),
            ephemeral=True
        )
        return

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE orders SET status = 'failed' WHERE order_id = ?", (거래id,))
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()

    try:
        member = await it.guild.fetch_member(int(user_id))
        mention = member.mention
    except Exception:
        mention = f"`{user_id}`"

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = 0x57F287
    con.add_item(ui.TextDisplay(
        f"### <:upvote:1489930275868770305>  주문 취소 완료\n"
        f"-# - **거래ID**: `{거래id}`\n"
        f"-# - **대상 유저**: {mention}\n"
        f"-# - **복구 금액**: {amount:,}원\n"
        f"-# - **처리자**: {it.user.mention}"
    ))
    view.add_item(con)
    await it.response.send_message(view=view, ephemeral=True)

    try:
        log_view = ui.LayoutView(timeout=None)
        log_con = ui.Container()
        log_con.accent_color = 0xED4245
        log_con.add_item(ui.TextDisplay(
            f"### <:acy2:1489883409001091142>  주문취소 로그\n"
            f"-# - **대상**: {mention}\n"
            f"-# - **거래ID**: `{거래id}`\n"
            f"-# - **복구 금액**: {amount:,}원\n"
            f"-# - **처리자**: {it.user.mention}"
        ))
        log_view.add_item(log_con)
        await send_log("cancel_log", log_view)
    except Exception as e:
        print(f"[취소로그 실패] {e}")

@bot.tree.command(name="점검모드", description="구매를 일시 중단하거나 재개합니다")
async def 점검모드(it: discord.Interaction):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'maintenance'")
        current = cur.fetchone()

    is_maintenance = current and current[0] == "1"

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES ('maintenance', ?)",
            ("0" if is_maintenance else "1")
        )
        conn.commit()

    if is_maintenance:
        view = await get_container_view(
            "<:upvote:1489930275868770305>  점검 해제",
            "-# - 구매가 재개되었습니다",
            0x57F287
        )
    else:
        view = await get_container_view(
            "<:downvote:1489930277450158080>  점검 모드",
            "-# - 구매가 일시 중단되었습니다",
            0xED4245
        )

    await it.response.send_message(view=view, ephemeral=True)


@bot.tree.command(name="유저목록", description="전체 유저 잔액 순위를 확인합니다")
@app_commands.describe(페이지="페이지 번호 (기본: 1)")
async def 유저목록(it: discord.Interaction, 페이지: int = 1):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    limit = 10
    offset = (페이지 - 1) * limit

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]

        cur.execute(
            "SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = cur.fetchall()

    if not rows:
        await it.response.send_message(
            view=await get_container_view("<:acy2:1489883409001091142>  유저 없음", "-# - 등록된 유저가 없습니다", 0x5865F2),
            ephemeral=True
        )
        return

    total_pages = (total + limit - 1) // limit
    text = (
        f"### <:acy2:1489883409001091142>  유저 잔액 순위\n"
        f"-# - 총 {total}명 | {페이지}/{total_pages} 페이지\n"
    )

    for i, (user_id, balance) in enumerate(rows):
        rank = offset + i + 1
        try:
            member = await it.guild.fetch_member(int(user_id))
            name = member.display_name
        except Exception:
            name = f"{user_id}"
        text += f"-# - **{rank}위** | {name} | `{balance:,}원`\n"

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = 0x5865F2
    con.add_item(ui.TextDisplay(text))
    view.add_item(con)
    await it.response.send_message(view=view, ephemeral=True)

@bot.tree.command(name="미완료주문", description="pending 상태 주문 목록을 확인합니다")
async def 미완료주문(it: discord.Interaction):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT order_id, user_id, amount, created_at FROM orders WHERE status = 'pending' ORDER BY created_at DESC"
        )
        rows = cur.fetchall()

    if not rows:
        await it.response.send_message(
            view=await get_container_view("<:upvote:1489930275868770305>  미완료 없음", "-# - pending 상태 주문이 없습니다", 0x57F287),
            ephemeral=True
        )
        return

    text = (
        f"### <:acy2:1489883409001091142>  미완료 주문 목록\n"
        f"-# - 총 {len(rows)}건\n"
    )

    for row in rows:
        order_id, user_id, amount, created_at = row
        try:
            member = await it.guild.fetch_member(int(user_id))
            name = member.display_name
        except Exception:
            name = f"{user_id}"
        text += f"-# - `{created_at[:10]}` | **{amount:,}원** | {name} | `{order_id}`\n"

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = 0xFEE75C
    con.add_item(ui.TextDisplay(text))
    view.add_item(con)
    await it.response.send_message(view=view, ephemeral=True)


@bot.tree.command(name="블랙리스트", description="특정 유저의 구매를 차단하거나 해제합니다")
@app_commands.describe(유저="차단/해제할 디스코드 유저")
async def 블랙리스트(it: discord.Interaction, 유저: discord.Member):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    key = f"blacklist_{유저.id}"

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = ?", (key,))
        current = cur.fetchone()

    is_blocked = current and current[0] == "1"

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, "0" if is_blocked else "1")
        )
        conn.commit()

    if is_blocked:
        view = ui.LayoutView(timeout=None)
        con = ui.Container()
        con.accent_color = 0x57F287
        con.add_item(ui.TextDisplay(
            f"### <:upvote:1489930275868770305>  차단 해제\n"
            f"-# - **대상 유저**: {유저.mention}\n"
            f"-# - 구매가 가능한 상태로 변경되었습니다\n"
            f"-# - **처리자**: {it.user.mention}"
        ))
        view.add_item(con)
    else:
        view = ui.LayoutView(timeout=None)
        con = ui.Container()
        con.accent_color = 0xED4245
        con.add_item(ui.TextDisplay(
            f"### <:downvote:1489930277450158080>  차단 완료\n"
            f"-# - **대상 유저**: {유저.mention}\n"
            f"-# - 구매가 불가한 상태로 변경되었습니다\n"
            f"-# - **처리자**: {it.user.mention}"
        ))
        view.add_item(con)

    await it.response.send_message(view=view, ephemeral=True)

async def send_log(log_type: str, view):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = ?", (log_type,))
            row = cur.fetchone()
        if row:
            channel = bot.get_channel(int(row[0]))
            if channel:
                await channel.send(view=view)
    except Exception as e:
        print(f"[로그 실패] {e}")


@bot.tree.command(name="로그설정", description="로그 채널을 설정합니다")
@app_commands.describe(종류="로그 종류", 채널="로그를 전송할 채널")
@app_commands.choices(종류=[
    app_commands.Choice(name="구매 로그", value="purchase_log"),
    app_commands.Choice(name="충전 로그", value="charge_log"),
    app_commands.Choice(name="수동충전 로그", value="manual_charge_log"),
    app_commands.Choice(name="주문취소 로그", value="cancel_log"),
    app_commands.Choice(name="할인 설정 로그", value="discount_log"),
    app_commands.Choice(name="재고 로그", value="stock_log"),
])
async def 로그설정(it: discord.Interaction, 종류: app_commands.Choice[str], 채널: discord.TextChannel):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (종류.value, str(채널.id))
        )
        conn.commit()

    await it.response.send_message(
        view=await get_container_view(
            "<:upvote:1489930275868770305>  설정 완료",
            f"-# - **{종류.name}** 채널: {채널.mention}",
            0x57F287
        ),
        ephemeral=True
    )

@bot.tree.command(name="자충설정", description="자동충전 server_id와 pw를 설정합니다")
@app_commands.describe(server_id="서버 ID", pw="비밀번호")
async def 충전설정(it: discord.Interaction, server_id: str, pw: str):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('charge_server_id', ?)", (server_id,))
        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('charge_pw', ?)", (pw,))
        conn.commit()

    await it.response.send_message(
        view=await get_container_view(
            "<:upvote:1489930275868770305>  설정 완료",
            f"-# - server_id: `{server_id}`\n-# - pw: `{pw}`",
            0x57F287
        ),
        ephemeral=True
    )

@bot.tree.command(name="코인설정", description="NOWPayments API 키를 설정합니다")
@app_commands.describe(api_key="NOWPayments API 키")
async def 코인설정(it: discord.Interaction, api_key: str):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('nowpayments_key', ?)", (api_key,))
        conn.commit()

    await it.response.send_message(
        view=await get_container_view("<:upvote:1489930275868770305>  설정 완료", "-# - NOWPayments API 키가 등록되었습니다", 0x57F287),
        ephemeral=True
    )

# ─────────────────────────────────────────
# 실행
# ─────────────────────────────────────────

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=88)

def run_web():
    uvicorn.run(web_app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    print("로벅스 자동 판매 시작")
    Thread(target=run_fastapi, daemon=True).start()  # 포트 80 - 자동충전
    Thread(target=run_web, daemon=True).start()       # 포트 8080 - 웹
    bot.run(TOKEN)
