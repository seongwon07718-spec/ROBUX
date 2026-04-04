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

# --- [강화] 상세 정보 조회 (가격 및 ProductId 추출 집중) ---
def fetch_gamepass_details(pass_id, admin_cookie=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    cookies = {".ROBLOSECURITY": admin_cookie} if admin_cookie else {}
    
    try:
        url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = requests.get(url, headers=headers, cookies=cookies, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return {
                "id": pass_id,
                "name": data.get("Name", "이름 없음"),
                "price": data.get("PriceInRobux") or 0,
                "sellerId": data.get("Creator", {}).get("Id"),
                "productId": data.get("ProductId"),
                "isForSale": data.get("IsForSale", False)
            }
    except: pass
    return None

# --- 로블록스 실제 구매 API 호출 함수 ---
def execute_purchase(cookie, info):
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    try:
        # CSRF 토큰 갱신
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        token = auth_res.headers.get("x-csrf-token")
        if not token: return False, "인증 실패(쿠키 확인 필요)"
        headers["X-CSRF-TOKEN"] = token

        # 구매 요청
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
            return False, res_json.get("reason", "로블록스 거절")
        return False, f"HTTP {buy_res.status_code}"
    except Exception as e:
        return False, str(e)

# --- [수정] 가격 강조 및 버튼 작동 확인 뷰 ---
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
        
        # 가격 정보를 더 자세히 표시
        price_details = (
            f"**📦 상품명**: `{self.info['name']}`\n"
            f"**💎 주문 로벅스**: `{self.info['price']:,} R$`\n"
            f"**💳 최종 결제액**: `{self.money:,}원`"
        )
        con.add_item(ui.TextDisplay(f"### 🛒 구매 정보 확인\n{price_details}"))
        
        # 버튼 로우 생성
        row = ui.ActionRow()
        
        # 구매 확정 버튼
        btn_confirm = ui.Button(label="구매 확정", style=discord.ButtonStyle.success, emoji="✅")
        btn_confirm.callback = self.on_confirm_click
        
        # 취소 버튼
        btn_cancel = ui.Button(label="취소", style=discord.ButtonStyle.secondary, emoji="✖️")
        btn_cancel.callback = self.on_cancel_click
        
        row.add_item(btn_confirm)
        row.add_item(btn_cancel)
        con.add_item(row)
        
        self.clear_items()
        self.add_item(con)
        return self

    async def on_confirm_click(self, it: discord.Interaction):
        # 중복 클릭 방지 위해 처리 중 메시지로 교체
        await it.response.edit_message(view=get_container_view("⌛ 처리 중", "로블록스 결제 API를 호출하고 있습니다.", 0xFEE75C))
        
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        res = cur.fetchone()

        if not res or res[0] < self.money:
            conn.close()
            return await it.edit_original_response(view=get_container_view("❌ 잔액 부족", "계정 잔액이 모자랍니다.", 0xED4245))

        # 실제 구매 실행
        success, msg = execute_purchase(self.cookie, self.info)
        
        if success:
            order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=get_container_view("✅ 구매 완료", f"주문번호: `{order_id}`\n상품: `{self.info['name']}`", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 구매 실패", f"사유: `{msg}`", 0xED4245))
        conn.close()

    async def on_cancel_click(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소됨", "주문이 취소되었습니다.", 0x99AAB5))

# --- 모달 클래스 (ID 추출 포함) ---
class GamepassModal(ui.Modal, title="로블록스 게임패스 구매"):
    id_input = ui.TextInput(label="ID 또는 링크", placeholder="여기에 입력하세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        raw_val = self.id_input.value.strip()
        
        # ID 추출 (숫자만 골라내기)
        nums = re.findall(r'\d+', raw_val)
        if not nums:
            return await it.response.send_message(view=get_container_view("❌ 오류", "ID를 인식할 수 없습니다.", 0xED4245), ephemeral=True)
        pass_id = max(nums, key=len)

        # 데이터베이스 설정 로드
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        if not c_row:
            return await it.response.send_message(view=get_container_view("❌ 설정 오류", "관리자 쿠키가 없습니다.", 0xED4245), ephemeral=True)

        # 상세 정보 조회
        info = fetch_gamepass_details(pass_id, c_row[0])
        if not info:
            return await it.response.send_message(view=get_container_view("❌ 정보 없음", "정보를 불러올 수 없습니다. ID를 확인하세요.", 0xED4245), ephemeral=True)

        # 가격 계산
        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000)

        # 확인 뷰 전송
        view_obj = GamepassConfirmView(info, money, it.user.id, c_row[0])
        await it.response.send_message(view=await view_obj.build(), ephemeral=True)
