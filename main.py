import discord
from discord import ui
import sqlite3
import requests
import asyncio
import random
import string
import re

DATABASE = 'robux_shop.db'

# --- 공통 컨테이너 생성 함수 ---
def create_container_msg(title, description, color=0x5865F2):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"### {title}\n{description}"))
    return ui.LayoutView().add_item(con)

def generate_order_id():
    chars = string.ascii_uppercase + string.digits
    return f"{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=6))}"

# --- [요청 사항] Universe API를 활용한 정보 조회 ---
def fetch_gamepass_via_universe(pass_id):
    """
    1. 먼저 기존 details API로 universeId를 찾습니다.
    2. 해당 universeId의 모든 게임패스 리스트를 요청한 API로 긁어옵니다.
    3. 리스트에서 일치하는 pass_id의 상세 정보를 반환합니다.
    """
    try:
        # 1. 기본 정보를 통해 UniverseId 획득
        basic_url = f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
        basic_res = requests.get(basic_url, timeout=5)
        if basic_res.status_code != 200: return None
        
        u_id = basic_res.json().get("universeId")
        if not u_id: return None

        # 2. 요청하신 Universe 기반 Full View API 호출
        # pageSize를 100으로 설정하여 해당 게임의 패스들을 긁어옵니다.
        universe_url = f"https://apis.roblox.com/game-passes/v1/universes/{u_id}/game-passes"
        params = {
            "passView": "Full",
            "pageSize": 100
        }
        uni_res = requests.get(universe_url, params=params, timeout=5)
        
        if uni_res.status_code == 200:
            data = uni_res.json().get("gamePasses", [])
            # 리스트에서 사용자가 입력한 ID와 일치하는 항목 검색
            for gp in data:
                if str(gp.get("id")) == str(pass_id):
                    return {
                        "id": pass_id,
                        "name": gp.get("name"),
                        "price": gp.get("price", 0),
                        "sellerId": gp.get("creatorId"),
                        "sellerName": gp.get("creatorName"),
                        "productId": gp.get("productId")
                    }
    except Exception as e:
        print(f"Universe API Error: {e}")
    return None

# --- 실제 구매 처리 ---
def process_purchase(cookie, info):
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Referer": f"https://www.roblox.com/game-pass/{info['id']}"
    }
    try:
        # CSRF 토큰 갱신
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        token = auth_res.headers.get("x-csrf-token")
        if not token: return False, "세션 만료 (관리자 쿠키 확인 필요)"
        headers["X-CSRF-TOKEN"] = token

        # Economy API를 통한 결제
        buy_url = f"https://economy.roblox.com/v1/purchases/products/{info['productId']}"
        payload = {
            "expectedCurrency": 1,
            "expectedPrice": info['price'],
            "expectedSellerId": info['sellerId']
        }
        buy_res = session.post(buy_url, headers=headers, json=payload)
        
        if buy_res.status_code == 200:
            res = buy_res.json()
            if res.get("purchased"): return True, "성공"
            return False, res.get("reason", "구매 실패")
        return False, f"서버 오류 ({buy_res.status_code})"
    except Exception as e:
        return False, str(e)

# --- 구매 확인 뷰 (컨테이너 기반) ---
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id, cookie):
        super().__init__(timeout=None)
        self.info = info
        self.money = money
        self.user_id = str(user_id)
        self.cookie = cookie

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            f"### 📋 주문서 확인\n"
            f"- **아이템**: `{self.info['name']}`\n"
            f"- **로벅스**: `{self.info['price']:,} R$`\n"
            f"- **지불금액**: `{self.money:,}원` (잔액 차감)\n\n"
            f"위 정보가 맞다면 **구매 확정**을 눌러주세요."
        ))
        
        btn_row = ui.ActionRow()
        btn_ok = ui.Button(label="구매 확정", style=discord.ButtonStyle.success, emoji="✅")
        btn_ok.callback = self.on_confirm
        btn_no = ui.Button(label="거부", style=discord.ButtonStyle.danger, emoji="✖️")
        btn_no.callback = self.on_cancel
        
        btn_row.add_item(btn_ok)
        btn_row.add_item(btn_no)
        con.add_item(btn_row)
        
        self.clear_items()
        self.add_item(con)
        return self

    async def on_confirm(self, it: discord.Interaction):
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        row = cur.fetchone()

        if not row or row[0] < self.money:
            conn.close()
            return await it.response.send_message(view=create_container_msg("❌ 잔액 부족", "충전된 잔액이 부족합니다.", 0xED4245), ephemeral=True)

        await it.response.edit_message(view=create_container_msg("⌛ 처리 중", "API 통신 및 결제를 진행 중입니다...", 0xFEE75C))

        success, msg = process_purchase(self.cookie, self.info)
        
        if success:
            order_id = generate_order_id()
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=create_container_msg("✅ 구매 완료", f"주문번호: `{order_id}`\n상품명: `{self.info['name']}`", 0x57F287))
        else:
            await it.edit_original_response(view=create_container_msg("❌ 구매 실패 (환불)", f"사유: `{msg}`", 0xED4245))
        
        conn.close()

    async def on_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=create_container_msg("✖️ 취소됨", "구매 진행을 취소했습니다.", 0x99AAB5))

# --- 입력 모달 ---
class GamepassModal(ui.Modal, title="게임패스 구매 정보"):
    input_data = ui.TextInput(label="게임패스 링크 또는 ID", placeholder="정확한 링크나 숫자를 입력해주세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        raw = self.input_data.value.strip()
        nums = re.findall(r'\d+', raw)
        if not nums:
            return await it.response.send_message(view=create_container_msg("❌ 인식 실패", "올바른 ID를 찾을 수 없습니다.", 0xED4245), ephemeral=True)
        
        pass_id = max(nums, key=len)

        # 유니버스 API 기반 조회 실행
        info = fetch_gamepass_via_universe(pass_id)
        if not info:
            return await it.response.send_message(view=create_container_msg("❌ 조회 실패", "로블록스 서버에서 해당 게임패스를 찾을 수 없습니다.", 0xED4245), ephemeral=True)

        # 설정 및 가격 계산
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        conn.close()

        if not c_row:
            return await it.response.send_message(view=create_container_msg("❌ 시스템 오류", "관리자 쿠키 설정이 비어있습니다.", 0xED4245), ephemeral=True)

        rate = int(r_row[0]) if r_row else 1300
        money = int((info['price'] / rate) * 10000)

        view = GamepassConfirmView(info, money, it.user.id, c_row[0])
        await it.response.send_message(view=await view.build(), ephemeral=True)

