import discord
from discord import ui
import sqlite3
import requests
import asyncio
import random
import string
import re

DATABASE = 'robux_shop.db'

# --- [수정] 모든 응답을 컨테이너 뷰로 감싸는 표준 함수 ---
def get_container_view(title, description, color=0x5865F2):
    # ui.Container V2 규격에 맞춘 선언
    con = ui.Container()
    con.accent_color = color
    # 마크다운을 지원하는 TextDisplay 사용
    con.add_item(ui.TextDisplay(f"### {title}\n{description}"))
    
    # 레이아웃 뷰에 담아 리턴 (구성 요소 에러 방지)
    view = ui.LayoutView()
    view.add_item(con)
    return view

def generate_order_id():
    chars = string.ascii_uppercase + string.digits
    return f"{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=6))}"

# --- [안정성 강화] 로블록스 상세 정보 조회 API ---
def fetch_gamepass_details(pass_id):
    try:
        # 이 엔드포인트가 ProductId를 가장 정확하게 반환합니다.
        url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return {
                "id": pass_id,
                "name": data.get("Name"),
                "price": data.get("PriceInRobux") or 0,
                "sellerId": data.get("Creator", {}).get("Id"),
                "productId": data.get("ProductId"),
                "isForSale": data.get("IsForSale")
            }
    except Exception as e:
        print(f"Fetch Error: {e}")
    return None

# --- [핵심] 로블록스 구매 실행 함수 ---
def execute_purchase(cookie, info):
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json"
    }
    try:
        # 1. CSRF 토큰 갱신 (반드시 필요)
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        token = auth_res.headers.get("x-csrf-token")
        if not token: return False, "토큰 확보 실패 (쿠키 만료)"
        headers["X-CSRF-TOKEN"] = token

        # 2. 실제 구매 API 호출
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
            return False, res_json.get("reason", "구매 거절됨")
        return False, f"HTTP {buy_res.status_code}"
    except Exception as e:
        return False, str(e)

# --- 구매 최종 확인 컨테이너 뷰 ---
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id, cookie):
        super().__init__(timeout=120)
        self.info = info
        self.money = money
        self.user_id = str(user_id)
        self.cookie = cookie

    async def build(self):
        # UI 구성
        con = ui.Container()
        con.accent_color = 0x5865F2
        
        desc = (
            f"**상품명**: `{self.info['name']}`\n"
            f"**가격**: `{self.info['price']:,} R$`\n"
            f"**결제금액**: `{self.money:,}원`"
        )
        con.add_item(ui.TextDisplay(f"### 🛒 구매를 확정하시겠습니까?\n{desc}"))
        
        # 버튼 액션 로우
        row = ui.ActionRow()
        btn_ok = ui.Button(label="구매 확정", style=discord.ButtonStyle.success, emoji="✅")
        btn_ok.callback = self.on_confirm
        
        btn_no = ui.Button(label="취소", style=discord.ButtonStyle.secondary)
        btn_no.callback = self.on_cancel
        
        row.add_item(btn_ok)
        row.add_item(btn_no)
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
            return await it.response.edit_message(view=get_container_view("❌ 잔액 부족", "충전 후 다시 시도해 주세요.", 0xED4245))

        # 처리 중 알림
        await it.response.edit_message(view=get_container_view("⌛ 결제 진행 중", "로블록스 API와 통신하고 있습니다...", 0xFEE75C))

        # 구매 실행
        success, msg = execute_purchase(self.cookie, self.info)
        
        if success:
            order_id = generate_order_id()
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=get_container_view("✅ 구매 성공", f"주문번호: `{order_id}`\n로벅스 지급이 완료되었습니다.", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 구매 실패", f"사유: `{msg}`", 0xED4245))
        conn.close()

    async def on_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소됨", "결제가 취소되었습니다.", 0x99AAB5))

# --- [수정] 입력 모달 (필드 이름 불일치 문제 해결) ---
class GamepassModal(ui.Modal, title="게임패스 구매 정보 입력"):
    # 필드 객체를 클래스 변수로 선언 (인식 오류 방지)
    id_input = ui.TextInput(
        label="게임패스 ID 또는 링크", 
        placeholder="숫자 ID를 입력하거나 링크를 붙여넣으세요.", 
        min_length=1,
        required=True
    )

    async def on_submit(self, it: discord.Interaction):
        raw_val = self.id_input.value.strip()
        nums = re.findall(r'\d+', raw_val)
        if not nums:
            return await it.response.send_message(view=get_container_view("❌ 입력 오류", "숫자로 된 ID를 찾을 수 없습니다.", 0xED4245), ephemeral=True)
        
        pass_id = max(nums, key=len)

        # 정보 로드
        info = fetch_gamepass_details(pass_id)
        if not info or not info['isForSale']:
            return await it.response.send_message(view=get_container_view("❌ 인식 실패", "판매 중인 게임패스가 아니거나 정보를 불러올 수 없습니다.", 0xED4245), ephemeral=True)

        # 설정값 로드
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        conn.close()

        if not c_row:
            return await it.response.send_message(view=get_container_view("❌ 설정 오류", "관리자 쿠키가 등록되지 않았습니다.", 0xED4245), ephemeral=True)

        # 가격 계산 로직 (수식은 필요에 따라 수정하세요)
        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000)

        # 컨테이너 뷰 생성 및 전송
        view_obj = GamepassConfirmView(info, money, it.user.id, c_row[0])
        await it.response.send_message(view=await view_obj.build(), ephemeral=True)
