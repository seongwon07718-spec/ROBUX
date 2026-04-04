import discord
from discord import ui
import sqlite3
import requests
import asyncio
import random
import string
import re

DATABASE = 'robux_shop.db'

# --- 모든 응답을 컨테이너 뷰로 감싸는 함수 (이미지 오류 해결) ---
def get_container_view(title, description, color=0x5865F2):
    con = ui.Container()
    con.accent_color = color
    # ui.TextDisplay에 마크다운 적용
    con.add_item(ui.TextDisplay(f"### {title}\n{description}"))
    # 에러 이미지의 'has_components_v2' 오류 방지를 위해 LayoutView에 추가하여 리턴
    return ui.LayoutView().add_item(con)

def generate_order_id():
    chars = string.ascii_uppercase + string.digits
    return f"{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=6))}"

# --- [요청] Universe API를 사용한 정밀 조회 ---
def fetch_gamepass_via_universe(pass_id):
    try:
        # 1. UniverseId 획득을 위한 기본 정보 조회
        basic_url = f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
        basic_res = requests.get(basic_url, timeout=5)
        if basic_res.status_code != 200: return None
        u_id = basic_res.json().get("universeId")
        if not u_id: return None

        # 2. Universe 기반 Full View API (요청하신 방식)
        universe_url = f"https://apis.roblox.com/game-passes/v1/universes/{u_id}/game-passes"
        params = {"passView": "Full", "pageSize": 100}
        uni_res = requests.get(universe_url, params=params, timeout=5)
        
        if uni_res.status_code == 200:
            data = uni_res.json().get("gamePasses", [])
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
        print(f"API Error: {e}")
    return None

# --- 로블록스 구매 실행 함수 ---
def execute_purchase(cookie, info):
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    try:
        # CSRF 토큰 갱신
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        token = auth_res.headers.get("x-csrf-token")
        if not token: return False, "토큰 획득 실패 (쿠키 만료)"
        headers["X-CSRF-TOKEN"] = token

        # Economy API 구매 엔드포인트
        buy_url = f"https://economy.roblox.com/v1/purchases/products/{info['productId']}"
        payload = {
            "expectedCurrency": 1, 
            "expectedPrice": info['price'], 
            "expectedSellerId": info['sellerId']
        }
        buy_res = session.post(buy_url, headers=headers, json=payload)
        
        if buy_res.status_code == 200:
            res_json = buy_res.json()
            if res_json.get("purchased"): return True, "성공"
            return False, res_json.get("reason", "알 수 없는 거절")
        return False, f"HTTP {buy_res.status_code}"
    except Exception as e:
        return False, str(e)

# --- 구매 최종 확인 뷰 ---
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
            f"### 🛒 구매 정보 확인\n"
            f"- **상품**: `{self.info['name']}`\n"
            f"- **가격**: `{self.info['price']:,} R$`\n"
            f"- **결제**: `{self.money:,}원`"
        ))
        row = ui.ActionRow()
        confirm = ui.Button(label="구매 확정", style=discord.ButtonStyle.success, emoji="✅")
        confirm.callback = self.on_confirm
        cancel = ui.Button(label="취소", style=discord.ButtonStyle.danger, emoji="✖️")
        cancel.callback = self.on_cancel
        row.add_item(confirm)
        row.add_item(cancel)
        con.add_item(row)
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
            return await it.response.send_message(view=get_container_view("❌ 잔액 부족", "충전 후 이용해주세요.", 0xED4245), ephemeral=True)

        await it.response.edit_message(view=get_container_view("⌛ 처리 중", "로블록스 결제 API를 호출하고 있습니다.", 0xFEE75C))

        success, msg = execute_purchase(self.cookie, self.info)
        
        if success:
            order_id = generate_order_id()
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=get_container_view("✅ 구매 완료", f"주문번호: `{order_id}`\n상품: `{self.info['name']}`", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 구매 실패", f"사유: `{msg}`", 0xED4245))
        conn.close()

    async def on_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소", "주문이 취소되었습니다.", 0x99AAB5))

# --- [수정] 에러가 났던 모달 클래스 ---
class GamepassModal(ui.Modal, title="게임패스 구매 정보 입력"):
    # 에러 이미지의 'input_field' 속성 오류를 해결하기 위해 이름을 정확히 매칭합니다.
    # 텍스트 입력창 정의
    input_field = ui.TextInput(
        label="게임패스 링크 또는 ID", 
        placeholder="정확한 링크나 ID를 입력하세요.", 
        required=True
    )

    async def on_submit(self, it: discord.Interaction):
        # self.input_field가 클래스 변수로 존재하므로 에러가 발생하지 않습니다.
        raw_val = self.input_field.value.strip()
        
        # 숫자 추출
        nums = re.findall(r'\d+', raw_val)
        if not nums:
            return await it.response.send_message(view=get_container_view("❌ 입력 오류", "숫자 ID를 찾을 수 없습니다.", 0xED4245), ephemeral=True)
        
        pass_id = max(nums, key=len)

        # 유니버스 API 조회
        info = fetch_gamepass_via_universe(pass_id)
        if not info:
            return await it.response.send_message(view=get_container_view("❌ 인식 실패", "로블록스 서버에서 정보를 찾을 수 없습니다.", 0xED4245), ephemeral=True)

        # 설정 로드
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        conn.close()

        if not c_row:
            return await it.response.send_message(view=get_container_view("❌ 시스템 오류", "관리자 쿠키가 등록되지 않았습니다.", 0xED4245), ephemeral=True)

        rate = int(r_row[0]) if r_row else 1300
        money = int((info['price'] / rate) * 10000)

        # 확인 뷰 전송
        view = GamepassConfirmView(info, money, it.user.id, c_row[0])
        await it.response.send_message(view=await view.build(), ephemeral=True)

