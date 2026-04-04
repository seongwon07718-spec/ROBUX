import discord
from discord import ui
import sqlite3
import requests
import asyncio
import random
import string
import re

# --- 설정 및 주문 ID 생성 (기존 로직 유지) ---
DATABASE = 'robux_shop.db'

def generate_order_id():
    chars = string.ascii_uppercase + string.digits
    return f"{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=6))}"

# --- 로블록스 실제 구매 API (기존 로직 유지) ---
def roblox_buy_gamepass(cookie, pass_info):
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Referer": f"https://www.roblox.com/game-pass/{pass_info['id']}"
    }
    try:
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        x_token = auth_res.headers.get("x-csrf-token")
        if not x_token: return False, "보안 토큰 획득 실패"
        headers["X-CSRF-TOKEN"] = x_token

        # 제품 정보 조회
        details = session.get(f"https://economy.roblox.com/v1/game-passes/{pass_info['id']}/details").json()
        product_id = details.get("ProductId")
        if not product_id: return False, "제품 ID를 찾을 수 없음"

        buy_payload = {
            "expectedCurrency": 1,
            "expectedPrice": pass_info['price'],
            "expectedSellerId": details.get("Creator", {}).get("Id")
        }
        buy_res = session.post(f"https://economy.roblox.com/v1/purchases/products/{product_id}", headers=headers, json=buy_payload)
        if buy_res.status_code == 200:
            result = buy_res.json()
            if result.get("purchased"): return True, "성공"
            return False, result.get("reason", "구매 거부됨")
        return False, f"서버 응답 오류 ({buy_res.status_code})"
    except Exception as e:
        return False, f"시스템 오류: {str(e)}"

# --- 구매 확인 뷰 ---
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
        
        confirm_btn = ui.Button(label="구매 확정", style=discord.ButtonStyle.success, emoji="✅")
        confirm_btn.callback = self.on_confirm
        cancel_btn = ui.Button(label="거부", style=discord.ButtonStyle.danger, emoji="✖️")
        cancel_btn.callback = self.on_cancel
        
        con.add_item(ui.ActionRow(confirm_btn, cancel_btn))
        self.clear_items()
        self.add_item(con)
        return con

    async def on_confirm(self, it: discord.Interaction):
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        user_row = cur.fetchone()
        
        if not user_row or user_row[0] < self.robux_price:
            conn.close()
            return await it.response.send_message("❌ 잔액이 부족합니다.", ephemeral=True)

        loading_con = ui.Container()
        loading_con.accent_color = 0x5865F2
        loading_con.add_item(ui.TextDisplay("### <a:1792loading:1487444148716965949> 로블록스 결제 시도 중..."))
        await it.response.edit_message(view=ui.LayoutView().add_item(loading_con))

        success, message = roblox_buy_gamepass(self.cookie, self.info)
        
        res_con = ui.Container()
        if success:
            order_id = generate_order_id()
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.robux_price, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.robux_price, self.info['price']))
            conn.commit()
            res_con.accent_color = 0x57F287
            res_con.add_item(ui.TextDisplay(f"### ✨ 구매 성공!\n- **주문번호**: `{order_id}`\n- **상품**: `{self.info['name']}`\n- **남은 잔액**: `{user_row[0] - self.robux_price:,}원`"))
        else:
            res_con.accent_color = 0xED4245
            res_con.add_item(ui.TextDisplay(f"### ❌ 구매 실패 (자동 환불)\n- **사유**: `{message}`"))
        
        conn.close()
        await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

    async def on_cancel(self, it: discord.Interaction):
        await it.response.edit_message(content="구매가 취소되었습니다.", view=None)

# --- [수정] 링크/ID 통합 인식 모달 ---
class GamepassModal(ui.Modal, title="게임패스 구매"):
    # 설명 문구에 ID 입력 가능함을 명시
    input_data = ui.TextInput(
        label="게임패스 링크 또는 ID", 
        placeholder="링크 전체 또는 숫자 ID만 입력 (예: 1234567)", 
        required=True
    )

    async def on_submit(self, it: discord.Interaction):
        # 1. 숫자만 입력된 경우와 링크에서 추출하는 경우 모두 대응
        raw_value = self.input_data.value.strip()
        
        # 숫자만 있는 경우
        if raw_value.isdigit():
            pass_id = raw_value
        else:
            # 링크에서 숫자 추출
            match = re.search(r"game-pass/(\d+)", raw_value)
            if match:
                pass_id = match.group(1)
            else:
                return await it.response.send_message("❌ 올바른 게임패스 ID 또는 링크를 입력해주세요.", ephemeral=True)
        
        # 설정 로드
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        if not c_row: return await it.response.send_message("서버 쿠키 설정이 없습니다.", ephemeral=True)
        
        cookie = c_row[0]
        rate = int(r_row[0]) if r_row else 1300
        
        # 상품 정보 로드
        try:
            details = requests.get(f"https://economy.roblox.com/v1/game-passes/{pass_id}/details").json()
            if "Name" not in details:
                raise Exception("잘못된 ID")
        except:
            return await it.response.send_message("❌ 존재하지 않거나 비공개된 게임패스입니다.", ephemeral=True)

        info = {"id": pass_id, "name": details["Name"], "price": details["PriceInRobux"]}
        required_money = int((info['price'] / rate) * 10000)

        # 확인 UI 컨테이너 생성
        confirm_view = GamepassConfirmView(info, required_money, it.user.id, cookie)
        con = await confirm_view.build_confirm_ui()
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

