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
from pydantic import BaseModel
from threading import Thread
from buy_gamepass import process_manual_buy_selenium

# ─────────────────────────────────────────

# 설정

# ─────────────────────────────────────────

DATABASE = “robux_shop.db”
TOKEN = “qDKSO08qlfsTBufSew”
BANK_K = “7777-03-6763823 (카카오뱅크)”

GIFT_GAMES = [
(“Rivals”, “17625359962”),
(“Blade Ball”, “13772394625”),
(“Blox Fruits”, “2753915549”),
(“Adopt Me!”, “920587237”),
(“Murder Mystery 2”, “142823291”),
(“Jailbreak”, “606849621”),
(“Dress to Impress”, “12699763399”),
(“Deepwoken”, “4111023553”),
(“Da Hood”, “2788229376”),
]

# ─────────────────────────────────────────

# DB 초기화

# ─────────────────────────────────────────

def init_db():
with sqlite3.connect(DATABASE) as conn:
cur = conn.cursor()
cur.execute(“CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)”)
cur.execute(“CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)”)
cur.execute(”””
CREATE TABLE IF NOT EXISTS orders (
order_id TEXT PRIMARY KEY,
user_id TEXT,
amount INTEGER,
robux INTEGER,
status TEXT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
“””)
conn.commit()

init_db()

# ─────────────────────────────────────────

# FastAPI (입금 감지)

# ─────────────────────────────────────────

app = FastAPI()
pending_deposits = {}

class ChargeData(BaseModel):
message: str

@app.post(”/charge”)
async def receive_charge(data: ChargeData):
msg = data.message.strip()
amount_match = re.search(r’입금\s*([\d,]+)원’, msg)
name_match = re.search(r’원\n([가-힣]+)\n잔액’, msg)

```
if amount_match and name_match:
    key = f"{name_match.group(1)}_{amount_match.group(1).replace(',', '')}"
    pending_deposits[key] = True
else:
    fallback = re.search(r'([가-힣]+)\s*(\d+)', msg)
    if fallback:
        pending_deposits[f"{fallback.group(1)}_{fallback.group(2)}"] = True

return {"ok": True}
```

# ─────────────────────────────────────────

# 유틸 함수

# ─────────────────────────────────────────

async def get_container_view(title: str, description: str, color: int):
view = ui.LayoutView()
con = ui.Container()
con.accent_color = color
con.add_item(ui.TextDisplay(f”### {title}\n-# {description}”))
view.add_item(con)
return view

def create_container_msg(title, description, color):
con = ui.Container()
con.accent_color = color
con.add_item(ui.TextDisplay(f”### {title}”))
con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
con.add_item(ui.TextDisplay(description))
return con

def get_roblox_data(cookie):
if not cookie:
return False, “입력된 쿠키가 없습니다.”

```
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
```

# ─────────────────────────────────────────

# Roblox API

# ─────────────────────────────────────────

class RobloxAPI:
BASE_HEADERS = {
“User-Agent”: (
“Mozilla/5.0 (Windows NT 10.0; Win64; x64) “
“AppleWebKit/537.36 (KHTML, like Gecko) “
“Chrome/121.0.0.0 Safari/537.36”
)
}

```
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
```

# ─────────────────────────────────────────

# 게임패스 구매 뷰

# ─────────────────────────────────────────

class FinalBuyView(ui.LayoutView):

```
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

    btn = ui.Button(label="진행하기", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>")
    btn.callback = self.do_buy
    con.add_item(ui.ActionRow(btn))
    self.add_item(con)

async def do_buy(self, it: discord.Interaction):
    start_time = asyncio.get_event_loop().time()

    await it.response.edit_message(
        view=await get_container_view(
            "<a:1792loading:1487444148716965949>  구매 진행 중",
            "-# - 로블록스 서버 API 연결 중입니다\n-# - 구매를 진행하는데 약간의 시간이 소요될 수 있습니다",
            0x5865F2
        )
    )

    loop = asyncio.get_running_loop()
    res = await loop.run_in_executor(
        None, process_manual_buy_selenium,
        self.pass_info["id"], self.user_id, self.money
    )
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
```

class PassSelectView(ui.LayoutView):

```
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
            view=await get_container_view("<:downvote:1489930277450158080>  오류", "-# 오류가 발생했습니다", 0xED4245),
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
```

class PlaceSelectView(ui.LayoutView):

```
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
        con.add_item(ui.TextDisplay("<:downvote:1489930277450158080>  선택 가능한 공개 게임이 없습니다"))
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
```

# ─────────────────────────────────────────

# 모달

# ─────────────────────────────────────────

class NicknameSearchModal(ui.Modal, title=“유저 검색”):

```
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
```

class GiftModal(ui.Modal, title=“글로벌 선물 방식”):

```
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
                        "✅ 게임 실행됨",
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
```

class CookieModal(ui.Modal, title=“로블록스 쿠키 등록”):

```
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
            f"-# - 계정에 접속을 성공했습니다\n-# - 현재 재고: **{result:,}로벅스**",
            0x57F287
        )
    else:
        con = create_container_msg(
            "<:downvote:1489930277450158080>  쿠키 등록 실패",
            f"-# - 인증에 실패하였습니다\n-# - 사유: `{result}`",
            0xED4245
        )

    await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
```

class RobuxCalculatorModal(ui.Modal, title=“로벅스 가격 계산기”):

```
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
```

class ChargeModal(ui.Modal, title=“계좌이체 충전 신청”):

```
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
        f"**입금 계좌**: `{BANK_K}`\n"
        f"**입금 금액**: `{int(self.amount.value):,}원`\n"
        f"**입금자명**: `{self.depositor.value}`"
    ))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

    copy_btn = ui.Button(label="계좌복사", style=discord.ButtonStyle.gray, emoji="<:success:1489875582874554429>")
    copy_btn.callback = self.copy_callback
    con.add_item(ui.ActionRow(copy_btn))
    await msg.edit(view=ui.LayoutView().add_item(con))

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
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### <:emoji_19:1487441741484392498>  충전 완료"))
        con.add_item(ui.TextDisplay(f"-# - 잔액이 성공적으로 충전되었습니다\n-# - **충전 금액:** `{int(self.amount.value):,}원`"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay("-# 정보 버튼을 눌러 잔액을 확인하세요!"))
    else:
        con.accent_color = 0xED4245
        con.add_item(ui.TextDisplay("### <:downvote:1489930277450158080>  충전 실패"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay("-# - 시간 내에 입금이 확인되지 않았습니다\n-# - 다시 충전 신청을 해주세요"))

    await msg.edit(view=ui.LayoutView().add_item(con))
```

# ─────────────────────────────────────────

# 자판기 뷰

# ─────────────────────────────────────────

class RobuxVending(ui.LayoutView):

```
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
        emoji="<:icons_dblurple:1489880744644837387>"
    )
    price_button = ui.Button(
        label=f"1.0 = {rate}로벅스",
        style=discord.ButtonStyle.gray,
        disabled=True,
        emoji="<:icons_dblurple:1489880744644837387>"
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
    con.add_item(ui.TextDisplay(f"### <:emoji_19:1487441741484392498>  {it.user.display_name} 님의 정보"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
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
                            view=await get_container_view("📋 최근 충전 내역", "-# - 충전 내역이 없습니다", 0x5865F2),
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
                            view=await get_container_view("🛒 최근 구매 내역", "-# - 구매 내역이 없습니다", 0x5865F2),
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
        "### <:emoji_19:1487441741484392498>  충전 수단\n"
        "-# - 원하시는 **충전 방식**을 선택해주세요\n"
        "-# - 현재 가능한 결제 수단은 **계좌이체**"
    ))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

    btn_bank = ui.Button(label="계좌이체", style=discord.ButtonStyle.gray, emoji="<:opt_online:1489872305138962452>")

    async def bank_cb(i: discord.Interaction):
        await i.response.send_modal(ChargeModal())

    btn_bank.callback = bank_cb
    con.add_item(ui.ActionRow(btn_bank))
    await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
```

# ─────────────────────────────────────────

# 봇

# ─────────────────────────────────────────

class MyBot(commands.Bot):

```
def __init__(self):
    super().__init__(command_prefix="!", intents=discord.Intents.all())
    self.vending_msg_info = {}

async def setup_hook(self):
    self.stock_updater.start()
    await self.tree.sync()

@tasks.loop(minutes=2.0)
async def stock_updater(self):
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

@stock_updater.before_loop
async def before_stock_updater(self):
    await self.wait_until_ready()
```

bot = MyBot()

# ─────────────────────────────────────────

# 슬래시 커맨드

# ─────────────────────────────────────────

@bot.tree.command(name=“자판기”, description=“로벅스 자판기를 전송합니다”)
async def spawn_vending(it: discord.Interaction):
await it.response.send_message(
view=await get_container_view(”<:acy2:1489883409001091142>  자판기”, “-# - 자판기가 전송되었습니다”, 0x5865F2),
ephemeral=True
)
view = RobuxVending(bot)
con = await view.build_main_menu()
msg = await it.channel.send(view=ui.LayoutView().add_item(con))
bot.vending_msg_info[it.channel_id] = msg.id

@bot.tree.command(name=“쿠키등록”, description=“로블록스 쿠키를 등록합니다”)
@app_commands.checks.has_permissions(administrator=True)
async def set_cookie(it: discord.Interaction):
await it.response.send_modal(CookieModal())

@bot.tree.command(name=“가격설정”, description=“로벅스 가격을 설정합니다”)
@app_commands.describe(수량=“1.0당 지급할 로벅스 양 (예: 1300)”)
@app_commands.checks.has_permissions(administrator=True)
async def set_rate(it: discord.Interaction, 수량: int):
with sqlite3.connect(DATABASE) as conn:
conn.execute(“INSERT OR REPLACE INTO config (key, value) VALUES (‘robux_rate’, ?)”, (str(수량),))
conn.commit()
await it.response.send_message(
view=await get_container_view(”<:acy2:1489883409001091142>  가격 설정 완료”, f”-# - 1.0당 {수량:,}로벅스로 설정되었습니다”, 0x5865F2),
ephemeral=True
)

@bot.tree.command(name=“관리자설정”, description=“관리자 ID를 설정합니다”)
async def 관리자설정(it: discord.Interaction):
with sqlite3.connect(DATABASE) as conn:
conn.execute(“INSERT OR REPLACE INTO config (key, value) VALUES (‘admin_id’, ?)”, (str(it.user.id),))
conn.commit()
await it.response.send_message(
view=await get_container_view(”<:acy2:1489883409001091142>  설정 완료”, “-# - 관리자로 설정되었습니다”, 0x5865F2),
ephemeral=True
)

@bot.tree.command(name=“수동충전”, description=“유저 잔액을 수동으로 조정합니다”)
@app_commands.describe(유저=“대상 디스코드 유저”, 금액=“충전/차감할 금액”, 여부=“추가 또는 차감”)
@app_commands.choices(여부=[
app_commands.Choice(name=“추가”, value=“추가”),
app_commands.Choice(name=“차감”, value=“차감”),
])
async def 수동충전(it: discord.Interaction, 유저: discord.Member, 금액: int, 여부: app_commands.Choice[str]):
with sqlite3.connect(DATABASE) as conn:
cur = conn.cursor()
cur.execute(“SELECT value FROM config WHERE key = ‘admin_id’”)
row = cur.fetchone()

```
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
    f"### <:emoji_19:1487441741484392498>  수동 충전 완료\n"
    f"-# - **대상 유저**: {유저.mention}\n"
    f"-# - **처리 내용**: {action_text}\n"
    f"-# - **이전 잔액**: {current:,}원\n"
    f"-# - **변경 후 잔액**: {new_balance:,}원\n"
    f"-# - **처리자**: {it.user.mention}"
))
view.add_item(con)
await it.response.send_message(view=view, ephemeral=True)
```

@bot.tree.command(name=“할인”, description=“유저 할인율을 설정합니다”)
@app_commands.describe(유저=“대상 디스코드 유저”, 할인율=“할인율 (0~100)”)
async def 할인(it: discord.Interaction, 유저: discord.Member, 할인율: int):
with sqlite3.connect(DATABASE) as conn:
cur = conn.cursor()
cur.execute(“SELECT value FROM config WHERE key = ‘admin_id’”)
row = cur.fetchone()

```
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
    f"### <:emoji_19:1487441741484392498>  할인율 설정 완료\n"
    f"-# - **대상 유저**: {유저.mention}\n"
    f"-# - **할인율**: {할인율}%\n"
    f"-# - **처리자**: {it.user.mention}"
))
view.add_item(con)
await it.response.send_message(view=view, ephemeral=True)
```

@bot.tree.command(name=“api_갱신”, description=“로블록스 API 상태를 확인하고 갱신합니다”)
async def api_갱신(it: discord.Interaction):
with sqlite3.connect(DATABASE) as conn:
cur = conn.cursor()
cur.execute(“SELECT value FROM config WHERE key = ‘admin_id’”)
row = cur.fetchone()

```
if not row or str(it.user.id) != row[0]:
    await it.response.send_message(
        view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
        ephemeral=True
    )
    return

await it.response.send_message(
    view=await get_container_view("<a:1792loading:1487444148716965949>  API 확인 중", "-# - 로블록스 API 상태를 확인하는 중입니다...", 0x5865F2),
    ephemeral=True
)

with sqlite3.connect(DATABASE) as conn:
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    cookie_row = cur.fetchone()

cookie = cookie_row[0] if cookie_row else None
clean_cookie = None
if cookie:
    clean_cookie = cookie.strip()
    if "=" in clean_cookie:
        clean_cookie = clean_cookie.split("=", 1)[-1]

session = requests.Session()
if clean_cookie:
    session.cookies.set(".ROBLOSECURITY", clean_cookie, domain=".roblox.com")

account_status = "❌ 오류"
account_name = "알 수 없음"
account_robux = 0

try:
    me = session.get("https://users.roblox.com/v1/users/authenticated", timeout=5).json()
    if me.get("id"):
        account_name = me.get("name", "알 수 없음")
        account_status = "✅ 정상"
        robux_resp = session.get("https://economy.roblox.com/v1/user/currency", timeout=5).json()
        account_robux = robux_resp.get("robux", 0)
    else:
        account_status = "⚠️ 쿠키 만료"
except Exception:
    account_status = "❌ 연결 실패"

gamepass_status = "❌ 오류"
try:
    test_resp = session.get(
        "https://apis.roproxy.com/game-passes/v1/universes/6516243967/game-passes?passView=Full&pageSize=1",
        timeout=5
    )
    if test_resp.status_code == 200 and account_status == "✅ 정상":
        gamepass_status = "✅ 가능"
    elif test_resp.status_code == 503:
        gamepass_status = "⚠️ 점검"
    else:
        gamepass_status = "❌ 오류"
except Exception:
    gamepass_status = "❌ 연결 실패"

gift_status = "⚠️ 준비 중"
try:
    resp = requests.get("https://apis.roproxy.com/universes/v1/places/17625359962/universe", timeout=5)
    gift_status = "⚠️ 준비 중" if resp.status_code == 200 else "❌ 오류"
except Exception:
    gift_status = "❌ 연결 실패"

view = ui.LayoutView(timeout=None)
con = ui.Container()
con.accent_color = 0x5865F2
con.add_item(ui.TextDisplay(
    f"### <:acy2:1489883409001091142>  API 갱신 결과\n"
    f"-# ─────────────────────\n"
    f"-# 🔑 **계정 상태**: {account_status}\n"
    f"-# - **계정명**: {account_name}\n"
    f"-# - **보유 로벅스**: {account_robux:,} R$\n"
    f"-# ─────────────────────\n"
    f"-# 🎮 **게임패스 지급**: {gamepass_status}\n"
    f"-# 🎁 **글로벌 선물**: {gift_status}\n"
    f"-# 👥 **그룹 지급**: ⚠️ 준비 중\n"
    f"-# ─────────────────────"
))
view.add_item(con)
await it.edit_original_response(view=view)
```

# ─────────────────────────────────────────

# 실행

# ─────────────────────────────────────────

def run_fastapi():
uvicorn.run(app, host=“0.0.0.0”, port=88)

if **name** == “**main**”:
print(“로벅스 자동 판매 시작”)
Thread(target=run_fastapi, daemon=True).start()
bot.run(TOKEN)
