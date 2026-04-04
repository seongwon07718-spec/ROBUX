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
    """4x4x4x6 형식의 고유 주문 ID 생성"""
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
        # 1. CSRF 토큰 획득 (로블록스 필수 보안 절차)
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        x_token = auth_res.headers.get("x-csrf-token")
        if not x_token: 
            return False, "보안 토큰(CSRF)을 가져오지 못했습니다."
        headers["X-CSRF-TOKEN"] = x_token

        # 2. 제품 ID(ProductId) 및 판매자 정보 조회
        details_res = session.get(f"https://economy.roblox.com/v1/game-passes/{pass_info['id']}/details")
        if details_res.status_code != 200:
            return False, "게임패스 정보를 불러올 수 없습니다. (ID 확인 필요)"
            
        details = details_res.json()
        product_id = details.get("ProductId")
        seller_id = details.get("Creator", {}).get("Id")
        
        if not product_id: 
            return False, "구매에 필요한 ProductId를 찾을 수 없습니다."

        # 3. 실제 구매 요청 (POST)
        buy_payload = {
            "expectedCurrency": 1,
            "expectedPrice": pass_info['price'],
            "expectedSellerId": seller_id
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
            # 실패 사유 상세 분석
            reason = result.get("reason", "알 수 없는 이유")
            if reason == "InsufficientFunds": return False, "재고 계정의 로벅스가 부족합니다."
            if reason == "AlreadyOwned": return False, "이미 소유한 아이템입니다."
            return False, f"구매 거부됨: {reason}"
        
        return False, f"로블록스 서버 응답 오류 ({buy_res.status_code})"
    except Exception as e:
        return False, f"시스템 치명적 오류: {str(e)}"

# --- 구매 확인 뷰 (컨테이너 내부 정렬) ---
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
            f"- **결제 금액**: `{self.robux_price:,}원` (잔액 차감)\n\n"
            f"주문하신 정보가 맞다면 아래 **구매 확정** 버튼을 눌러주세요."
        ))
        
        # 버튼 배열
        confirm_btn = ui.Button(label="구매 확정", style=discord.ButtonStyle.success, emoji="✅")
        confirm_btn.callback = self.on_confirm
        
        cancel_btn = ui.Button(label="거부/취소", style=discord.ButtonStyle.danger, emoji="✖️")
        cancel_btn.callback = self.on_cancel
        
        con.add_item(ui.ActionRow(confirm_btn, cancel_btn))
        self.clear_items()
        self.add_item(con)
        return con

    async def on_confirm(self, it: discord.Interaction):
        # 1. 잔액 검증
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        user_row = cur.fetchone()
        
        if not user_row or user_row[0] < self.robux_price:
            conn.close()
            return await it.response.send_message("❌ 잔액이 부족합니다. 충전 후 다시 시도해주세요.", ephemeral=True)

        # 2. 로딩 화면
        loading_con = ui.Container()
        loading_con.accent_color = 0x5865F2
        loading_con.add_item(ui.TextDisplay("### <a:1792loading:1487444148716965949> 로블록스 서버와 통신 중입니다..."))
        await it.response.edit_message(view=ui.LayoutView().add_item(loading_con))

        # 3. 실제 구매 로직 실행
        success, message = roblox_buy_gamepass(self.cookie, self.info)
        
        res_con = ui.Container()
        if success:
            order_id = generate_order_id()
            # 잔액 차감 및 주문 내역 저장
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.robux_price, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.robux_price, self.info['price']))
            conn.commit()
            
            res_con.accent_color = 0x57F287
            res_con.add_item(ui.TextDisplay(
                f"### ✨ 구매가 완료되었습니다!\n"
                f"- **주문번호**: `{order_id}`\n"
                f"- **상품명**: `{self.info['name']}`\n"
                f"- **남은 잔액**: `{user_row[0] - self.robux_price:,}원`"
            ))
        else:
            # 실패 시 환불 처리 (차감하지 않음)
            res_con.accent_color = 0xED4245
            res_con.add_item(ui.TextDisplay(f"### ❌ 구매 실패 (자동 환불)\n- **사유**: `{message}`\n- 계정의 잔액은 차감되지 않았습니다."))
        
        conn.close()
        await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

    async def on_cancel(self, it: discord.Interaction):
        await it.response.edit_message(content="구매가 취소되었습니다. 메뉴를 닫으셔도 좋습니다.", view=None)

# --- [개선] 링크 및 ID 인식 모달 ---
class GamepassModal(ui.Modal, title="게임패스 구매 정보 입력"):
    input_value = ui.TextInput(
        label="게임패스 링크 또는 ID를 입력하세요", 
        placeholder="예: 1784490889 또는 https://www.roblox.com/game-pass/1784490889/...", 
        required=True,
        min_length=5
    )

    async def on_submit(self, it: discord.Interaction):
        raw_text = self.input_value.value.strip()
        
        # 1. 정규표현식을 이용한 정밀 추출 (숫자만 있거나, URL 내부에 숫자가 있는 경우 모두 포함)
        # /game-pass/ 뒤의 숫자만 가져오거나, 숫자만 입력된 경우를 처리
        id_match = re.search(r"(?:game-pass/|id=)?(\d+)", raw_text, re.IGNORECASE)
        
        if id_match:
            pass_id = id_match.group(1)
        elif raw_text.isdigit():
            pass_id = raw_text
        else:
            return await it.response.send_message("❌ 입력하신 정보에서 게임패스 ID를 찾을 수 없습니다. 정확한 링크나 숫자를 입력해주세요.", ephemeral=True)
        
        # 2. 서버 설정 정보 로드
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        if not c_row: 
            return await it.response.send_message("❌ 관리자 설전에 로블록스 쿠키가 등록되어 있지 않습니다.", ephemeral=True)
        
        cookie = c_row[0]
        rate = int(r_row[0]) if r_row else 1300
        
        # 3. 상품 정보 실시간 조회 (Roblox API)
        try:
            details_req = requests.get(f"https://economy.roblox.com/v1/game-passes/{pass_id}/details")
            if details_req.status_code != 200:
                raise Exception("조회 실패")
            details = details_req.json()
            
            if "Name" not in details:
                raise Exception("비정상 데이터")
        except:
            return await it.response.send_message(f"❌ 게임패스(ID: {pass_id}) 정보를 찾을 수 없습니다. 존재하지 않거나 비공개 아이템일 수 있습니다.", ephemeral=True)

        info = {
            "id": pass_id, 
            "name": details["Name"], 
            "price": details.get("PriceInRobux", 0)
        }
        
        if info['price'] <= 0:
            return await it.response.send_message("❌ 이 게임패스는 현재 판매 중이 아니거나 가격이 0원입니다.", ephemeral=True)

        # 4. 가격 계산 (1.0당 로벅스 비율 적용)
        required_money = int((info['price'] / rate) * 10000)

        # 5. 최종 확인 UI 생성 및 전송
        confirm_view = GamepassConfirmView(info, required_money, it.user.id, cookie)
        con = await confirm_view.build_confirm_ui()
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

