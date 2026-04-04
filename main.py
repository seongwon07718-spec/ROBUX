import discord
from discord import ui
import sqlite3
import requests
import asyncio
import random
import string
import re

# --- 설정 및 주문 ID 생성 ---
DATABASE = 'robux_shop.db'

def generate_order_id():
    chars = string.ascii_uppercase + string.digits
    return f"{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=6))}"

# --- 로블록스 실제 구매 API 엔진 ---
def roblox_buy_gamepass(cookie, pass_info):
    """실제 로블록스 서버에 구매 요청을 보냅니다."""
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Referer": f"https://www.roblox.com/game-pass/{pass_info['id']}"
    }

    try:
        # 1. CSRF 토큰 획득
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        x_token = auth_res.headers.get("x-csrf-token")
        if not x_token: return False, "CSRF 토큰 획득 실패"
        headers["X-CSRF-TOKEN"] = x_token

        # 2. 제품 ID(ProductId) 조회
        # 게임패스 ID와 구매 시 필요한 제품 ID는 다릅니다.
        details = session.get(f"https://economy.roblox.com/v1/game-passes/{pass_info['id']}/details").json()
        product_id = details.get("ProductId")
        if not product_id: return False, "제품 정보를 찾을 수 없음"

        # 3. 실제 구매 요청
        buy_payload = {
            "expectedCurrency": 1,
            "expectedPrice": pass_info['price'],
            "expectedSellerId": details.get("Creator", {}).get("Id")
        }
        
        buy_res = session.post(
            f"https://economy.roblox.com/v1/purchases/products/{product_id}",
            headers=headers,
            json=buy_payload
        )

        if buy_res.status_code == 200:
            result = buy_res.json()
            if result.get("purchased"):
                return True, "성공"
            return False, result.get("reason", "알 수 없는 이유로 실패")
        
        return False, f"HTTP 에러 {buy_res.status_code}"
    except Exception as e:
        return False, f"시스템 오류: {str(e)}"

# --- 구매 확인 뷰 (컨테이너 내부 배열) ---
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, robux_price, user_id, cookie):
        super().__init__(timeout=None)
        self.info = info
        self.robux_price = robux_price
        self.user_id = str(user_id)
        self.cookie = cookie

    async def build_confirm_ui(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            f"### 🛒 구매 정보 최종 확인\n"
            f"- **아이템**: `{self.info['name']}`\n"
            f"- **가격**: `{self.info['price']:,} R$`\n"
            f"- **차감 금액**: `{self.robux_price:,}원` (잔액에서 차감)\n\n"
            f"⚠️ '구매 확정' 클릭 시 즉시 구매 및 잔액이 차감됩니다."
        ))
        
        # 버튼들을 액션로우에 담아 컨테이너에 추가
        confirm_btn = ui.Button(label="구매 확정", style=discord.ButtonStyle.success, emoji="✅")
        confirm_btn.callback = self.on_confirm
        
        cancel_btn = ui.Button(label="거부", style=discord.ButtonStyle.danger, emoji="✖️")
        cancel_btn.callback = self.on_cancel
        
        con.add_item(ui.ActionRow(confirm_btn, cancel_btn))
        self.clear_items()
        self.add_item(con)
        return con

    async def on_confirm(self, it: discord.Interaction):
        # 1. 유저 잔액 체크
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        user_row = cur.fetchone()
        
        if not user_row or user_row[0] < self.robux_price:
            conn.close()
            return await it.response.send_message("❌ 잔액이 부족합니다. 충전 후 이용해주세요.", ephemeral=True)

        # 로딩 표시
        loading_con = ui.Container()
        loading_con.accent_color = 0x5865F2
        loading_con.add_item(ui.TextDisplay("### <a:1792loading:1487444148716965949> 로블록스 API 통신 중..."))
        await it.response.edit_message(view=ui.LayoutView().add_item(loading_con))

        # 2. 실제 구매 수행
        success, message = roblox_buy_gamepass(self.cookie, self.info)
        
        res_con = ui.Container()
        if success:
            order_id = generate_order_id()
            # DB 차감 및 기록
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.robux_price, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.robux_price, self.info['price']))
            conn.commit()
            
            res_con.accent_color = 0x57F287
            res_con.add_item(ui.TextDisplay(f"### ✨ 구매 성공!\n- **주문번호**: `{order_id}`\n- **상품**: `{self.info['name']}`\n- **남은 잔액**: `{user_row[0] - self.robux_price:,}원`"))
        else:
            # 실패 시 자동 환불 (잔액 유지)
            res_con.accent_color = 0xED4245
            res_con.add_item(ui.TextDisplay(f"### ❌ 구매 실패 (환불됨)\n- **사유**: `{message}`\n- 잔액은 차감되지 않았습니다."))
        
        conn.close()
        await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

    async def on_cancel(self, it: discord.Interaction):
        await it.response.edit_message(content="구매가 취소되었습니다.", view=None)

# --- 게임패스 링크 입력 모달 ---
class GamepassModal(ui.Modal, title="게임패스 구매 신청"):
    link = ui.TextInput(label="게임패스 링크", placeholder="https://www.roblox.com/game-pass/12345/...", required=True)

    async def on_submit(self, it: discord.Interaction):
        # ID 추출
        match = re.search(r"game-pass/(\d+)", self.link.value)
        if not match:
            return await it.response.send_message("❌ 올바른 로블록스 게임패스 링크가 아닙니다.", ephemeral=True)
        
        pass_id = match.group(1)
        
        # 설정 로드
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        if not c_row: return await it.response.send_message("설정된 쿠키가 없습니다.", ephemeral=True)
        
        cookie = c_row[0]
        rate = int(r_row[0]) if r_row else 1300
        
        # 1. 상품 정보 미리 가져오기
        details = requests.get(f"https://economy.roblox.com/v1/game-passes/{pass_id}/details").json()
        if "Name" not in details:
            return await it.response.send_message("상품 정보를 불러올 수 없습니다.", ephemeral=True)

        info = {"id": pass_id, "name": details["Name"], "price": details["PriceInRobux"]}
        required_money = int((info['price'] / rate) * 10000)

        # 2. 확인 UI 생성 (컨테이너 방식)
        confirm_view = GamepassConfirmView(info, required_money, it.user.id, cookie)
        con = await confirm_view.build_confirm_ui()
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

# --- 자판기 클래스 내 구매 버튼 연결 ---
async def shop_callback(self, it: discord.Interaction):
    con = ui.Container()
    con.accent_color = 0x5865F2
    con.add_item(ui.TextDisplay("### 🛍️ 구매 방식 선택"))
    
    # 버튼 배열 (컨테이너 내부 ActionRow)
    btn_gp = ui.Button(label="게임패스", style=discord.ButtonStyle.gray, emoji="🎮")
    btn_gp.callback = lambda i: i.response.send_modal(GamepassModal())
    
    btn_ig = ui.Button(label="인게임", style=discord.ButtonStyle.gray, emoji="💎", disabled=True)
    btn_gr = ui.Button(label="그룹", style=discord.ButtonStyle.gray, emoji="👥", disabled=True)
    
    con.add_item(ui.ActionRow(btn_gp, btn_ig, btn_gr))
    await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

