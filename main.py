import sqlite3
import random
import string
import re
import requests
import asyncio
import discord
from discord import ui

DATABASE = 'robux_shop.db'

# -----------------------------------
# 1️⃣ 로블록스 API 통신용 유틸리티
# -----------------------------------
class RobloxAPI:
    def __init__(self, cookie=None):
        self.session = requests.Session()
        if cookie:
            self.session.cookies.set(".ROBLOSECURITY", cookie.split('=')[-1])
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }

    def get_csrf_token(self):
        # 강제 403 유도를 통한 토큰 탈취
        resp = self.session.post("https://auth.roblox.com/v2/logout", headers=self.headers)
        return resp.headers.get("x-csrf-token")

    def get_user_id(self, nickname):
        url = "https://users.roblox.com/v1/usernames/users"
        resp = self.session.post(url, json={"usernames": [nickname], "excludeBannedUsers": True})
        data = resp.json().get("data", [])
        return data[0].get("id") if data else None

    def get_user_places(self, user_id):
        # 유저의 공개 게임(플레이스) 목록 조회
        url = f"https://games.roblox.com/v2/users/{user_id}/games?accessFilter=Public&limit=10"
        resp = self.session.get(url)
        return resp.json().get("data", [])

    def get_place_gamepasses(self, universe_id):
        # 특정 유니버스(게임)의 게임패스 목록 조회
        url = f"https://games.roblox.com/v1/games/{universe_id}/game-passes?limit=10"
        resp = self.session.get(url)
        return resp.json().get("data", [])

# -----------------------------------
# 2️⃣ 최종 구매 엔진 (수동 CSRF 적용)
# -----------------------------------
def process_manual_buy(pass_id, user_id, money):
    conn = sqlite3.connect(DATABASE); cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    row = cur.fetchone(); conn.close()
    if not row: return {"success": False, "message": "쿠키 없음"}

    api = RobloxAPI(row[0])
    
    # 상품 상세 정보 획득
    info_resp = api.session.get(f"https://economy.roblox.com/v1/game-pass/{pass_id}/product-info")
    if info_resp.status_code != 200: return {"success": False, "message": "정보 조회 실패"}
    info = info_resp.json()
    
    # CSRF 토큰 갱신
    token = api.get_csrf_token()
    headers = api.headers.copy()
    headers.update({"x-csrf-token": token, "Content-Type": "application/json", "Referer": f"https://www.roblox.com/game-pass/{pass_id}"})
    
    # 구매 요청
    payload = {"expectedCurrency": 1, "expectedPrice": info.get("PriceInRobux", 0), "expectedSellerId": info.get("Creator", {}).get("Id")}
    buy_url = f"https://economy.roblox.com/v1/purchases/products/{info.get('ProductId')}"
    
    resp = api.session.post(buy_url, json=payload, headers=headers)
    result = resp.json()
    
    if resp.status_code == 200 and result.get("purchased"):
        # DB 처리 (생략 없이 로직 포함)
        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (money, user_id))
        cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                    (order_id, user_id, money, info.get("PriceInRobux", 0)))
        conn.commit(); conn.close()
        return {"success": True, "order_id": order_id}
    return {"success": False, "message": result.get("reason", "구매 조건 미달")}

# -----------------------------------
# 3️⃣ 뷰 계층 (UI)
# -----------------------------------

# [3] 최종 결제 단계
class FinalBuyView(ui.LayoutView):
    def __init__(self, pass_info, money, user_id):
        super().__init__(timeout=60)
        self.pass_info, self.money, self.user_id = pass_info, money, str(user_id)

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        text = f"### <:acy2:1489883409001091142> 최종 결제 확인\n-# - **아이템**: {self.pass_info['name']}\n-# - **가격**: {self.pass_info['price']:,} R$\n-# - **차감금액**: {self.money:,}원"
        con.add_item(ui.TextDisplay(text))
        row = ui.ActionRow()
        btn = ui.Button(label="승인", style=discord.ButtonStyle.gray, emoji="✅")
        btn.callback = self.do_buy
        row.add_item(btn)
        con.add_item(row)
        self.clear_items(); self.add_item(con)
        return self

    async def do_buy(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("⌛ 처리 중", "결제 요청 전송 중...", 0xFEE75C))
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, process_manual_buy, self.pass_info['id'], self.user_id, self.money)
        if res["success"]:
            await it.edit_original_response(view=get_container_view("✅ 완료", f"주문번호: `{res['order_id']}`", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 실패", res["message"], 0xED4245))

# [2] 게임패스 선택 단계
class PassSelectView(ui.LayoutView):
    def __init__(self, passes, user_id):
        super().__init__(timeout=60)
        self.passes, self.user_id = passes, user_id

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### 🎁 게임패스 선택\n구매할 아이템을 아래 목록에서 선택하세요."))
        
        select = ui.Select(placeholder="아이템을 선택하세요...")
        for p in self.passes:
            price = p.get('price', 0)
            select.add_option(label=f"{p['name']} ({price} R$)", value=str(p['id']), description=f"ID: {p['id']}")
        
        select.callback = self.on_select
        con.add_item(ui.ActionRow().add_item(select))
        self.clear_items(); self.add_item(con)
        return self

    async def on_select(self, it: discord.Interaction):
        selected_id = int(it.data['values'][0])
        pass_data = next(p for p in self.passes if p['id'] == selected_id)
        
        # 금액 계산
        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r = cur.fetchone(); conn.close()
        rate = int(r[0]) if r else 1000
        money = int((pass_data['price'] / rate) * 10000)

        view = FinalBuyView(pass_data, money, it.user.id)
        await it.response.edit_message(view=await view.build())

# [1] 플레이스(게임) 선택 단계
class PlaceSelectView(ui.LayoutView):
    def __init__(self, places, user_id):
        super().__init__(timeout=60)
        self.places, self.user_id = places, user_id

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### 🎮 마켓플레이스 선택\n게임패스가 등록된 게임을 선택하세요."))
        
        select = ui.Select(placeholder="게임을 선택하세요...")
        for p in self.places:
            select.add_option(label=p['name'], value=str(p['rootPlaceId']), description=f"UniverseID: {p['id']}")
        
        select.callback = self.on_select
        con.add_item(ui.ActionRow().add_item(select))
        self.clear_items(); self.add_item(con)
        return self

    async def on_select(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)
        place_id = int(it.data['values'][0])
        # UniverseId를 찾아야 함
        place_data = next(p for p in self.places if p['rootPlaceId'] == place_id)
        universe_id = place_data['id']
        
        api = RobloxAPI()
        passes = api.get_place_gamepasses(universe_id)
        
        if not passes:
            return await it.followup.send(view=get_container_view("❌ 오류", "이 게임에는 등록된 게임패스가 없습니다.", 0xED4245), ephemeral=True)
        
        view = PassSelectView(passes, it.user.id)
        await it.edit_original_response(view=await view.build())

# -----------------------------------
# 4️⃣ 시작 모달
# -----------------------------------
class NicknameSearchModal(ui.Modal, title="유저 검색 구매"):
    nick_input = ui.TextInput(label="로블록스 닉네임", placeholder="검색할 유저의 닉네임을 입력하세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)
        api = RobloxAPI()
        user_id = api.get_user_id(self.nick_input.value.strip())
        
        if not user_id:
            return await it.followup.send(view=get_container_view("❌ 검색 실패", "존재하지 않는 닉네임입니다.", 0xED4245), ephemeral=True)
        
        places = api.get_user_places(user_id)
        if not places:
            return await it.followup.send(view=get_container_view("❌ 결과 없음", "공개된 마켓플레이스가 없습니다.", 0xED4245), ephemeral=True)
            
        view = PlaceSelectView(places, it.user.id)
        await it.followup.send(view=await view.build(), ephemeral=True)

