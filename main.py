import discord
from discord import ui
import sqlite3
import requests
import asyncio
import random
import string
import re

DATABASE = 'robux_shop.db'

# --- 모든 응답을 컨테이너 뷰로 감싸는 표준 함수 ---
def get_container_view(title, description, color=0x5865F2):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"### {title}\n{description}"))
    view = ui.LayoutView()
    view.add_item(con)
    return view

# --- [정밀] 상세 정보 조회 (이름, 판매자, 가격 100% 추출) ---
def fetch_gamepass_details(pass_id, admin_cookie=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    cookies = {".ROBLOSECURITY": admin_cookie} if admin_cookie else {}

    try:
        # 가장 데이터가 풍부한 Economy API 사용
        url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = requests.get(url, headers=headers, cookies=cookies, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            # 필드명이 대문자로 시작하는 경우가 많으므로 정확히 매칭
            return {
                "id": pass_id,
                "name": data.get("Name", "알 수 없는 상품"),
                "price": data.get("PriceInRobux") or 0,
                "sellerName": data.get("Creator", {}).get("Name", "알 수 없는 판매자"),
                "sellerId": data.get("Creator", {}).get("Id"),
                "productId": data.get("ProductId"),
                "isForSale": data.get("IsForSale", False)
            }
    except Exception as e:
        print(f"조회 에러: {e}")
    return None

# --- 구매 실행 로직 (CSRF 포함) ---
def execute_purchase(cookie, info):
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    try:
        # CSRF 토큰 갱신
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        token = auth_res.headers.get("x-csrf-token")
        if not token: return False, "토큰 획득 실패"
        headers["X-CSRF-TOKEN"] = token

        # 실제 구매 API
        buy_url = f"https://economy.roblox.com/v1/purchases/products/{info['productId']}"
        payload = {
            "expectedCurrency": 1, 
            "expectedPrice": info['price'], 
            "expectedSellerId": info['sellerId']
        }
        buy_res = session.post(buy_url, headers=headers, json=payload, timeout=10)
        
        if buy_res.status_code == 200:
            res_json = buy_res.json()
            if res_json.get("purchased"): return True, "성공"
            return False, res_json.get("reason", "구매 거부됨")
        return False, f"HTTP {buy_res.status_code}"
    except Exception as e:
        return False, str(e)

# --- [수정] 버튼 작동이 확실한 확인 뷰 ---
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id, cookie):
        super().__init__(timeout=120)
        self.info = info
        self.money = money
        self.user_id = str(user_id)
        self.cookie = cookie

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        
        # 정보 출력 레이아웃
        info_text = (
            f"**📦 상품명**: `{self.info['name']}`\n"
            f"**👤 판매자**: `{self.info['sellerName']}`\n"
            f"**💰 가격**: `{self.info['price']:,} R$`\n"
            f"**💳 결제 예정**: `{self.money:,}원`"
        )
        con.add_item(ui.TextDisplay(f"### 🛒 구매 정보 확인\n{info_text}"))
        
        # 버튼 액션 로우
        row = ui.ActionRow()
        
        # 확정 버튼
        btn_confirm = ui.Button(label="구매 확정", style=discord.ButtonStyle.success, emoji="✅")
        btn_confirm.callback = self.on_confirm_click # 콜백 연결
        
        # 취소 버튼
        btn_cancel = ui.Button(label="취소하기", style=discord.ButtonStyle.danger, emoji="✖️")
        btn_cancel.callback = self.on_cancel_click # 콜백 연결
        
        row.add_item(btn_confirm)
        row.add_item(btn_cancel)
        con.add_item(row)
        
        self.clear_items()
        self.add_item(con)
        return self

    # 확정 버튼 클릭 시 실행
    async def on_confirm_click(self, it: discord.Interaction):
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        row = cur.fetchone()

        if not row or row[0] < self.money:
            conn.close()
            return await it.response.edit_message(view=get_container_view("❌ 잔액 부족", "충전 후 이용해 주세요.", 0xED4245))

        await it.response.edit_message(view=get_container_view("⌛ 처리 중", "로블록스 서버와 통신 중입니다...", 0xFEE75C))

        success, msg = execute_purchase(self.cookie, self.info)
        
        if success:
            order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=get_container_view("✅ 구매 성공", f"주문번호: `{order_id}`\n성공적으로 지급되었습니다.", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 구매 실패", f"사유: `{msg}`", 0xED4245))
        conn.close()

    # 취소 버튼 클릭 시 실행
    async def on_cancel_click(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소됨", "구매 요청이 취소되었습니다.", 0x99AAB5))

# --- 모달 클래스 ---
class GamepassModal(ui.Modal, title="게임패스 구매 정보 입력"):
    id_input = ui.TextInput(label="게임패스 ID 또는 링크", placeholder="여기에 입력하세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        raw_val = self.id_input.value.strip()
        nums = re.findall(r'\d+', raw_val)
        if not nums:
            return await it.response.send_message(view=get_container_view("❌ 오류", "ID를 인식할 수 없습니다.", 0xED4245), ephemeral=True)
        
        pass_id = max(nums, key=len)

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        if not c_row:
            return await it.response.send_message(view=get_container_view("❌ 설정 오류", "쿠키가 등록되지 않았습니다.", 0xED4245), ephemeral=True)

        info = fetch_gamepass_details(pass_id, c_row[0])
        if not info:
            return await it.response.send_message(view=get_container_view("❌ 정보 없음", "해당 ID의 정보를 가져올 수 없습니다.", 0xED4245), ephemeral=True)

        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000)

        view_obj = GamepassConfirmView(info, money, it.user.id, c_row[0])
        await it.response.send_message(view=await view_obj.build(), ephemeral=True)
