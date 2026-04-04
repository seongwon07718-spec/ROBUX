import discord
from discord import ui
import sqlite3
import requests
import asyncio
import random
import string
import re

DATABASE = 'robux_shop.db'

def generate_order_id():
    chars = string.ascii_uppercase + string.digits
    return f"{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=6))}"

# --- [수정] 더 정확한 게임패스 정보 조회 API (카탈로그 기반) ---
def get_gamepass_details(pass_id):
    """로블록스 카탈로그 API를 사용하여 게임패스 정보를 가져옵니다."""
    try:
        # v1/game-passes 대신 v1/multiget-item-details 사용 (더 안정적)
        url = "https://catalog.roblox.com/v1/catalog/items/details"
        params = {
            "items": [f"1:{pass_id}"] # 1은 GamePass 타입을 의미
        }
        res = requests.post(url, json=params, timeout=5)
        
        if res.status_code == 200:
            data = res.json().get('data', [])
            if data:
                item = data[0]
                return {
                    "id": pass_id,
                    "name": item.get("name"),
                    "price": item.get("price", 0),
                    "seller": item.get("creatorName"),
                    "productId": item.get("productId")
                }
    except Exception as e:
        print(f"API Error: {e}")
    return None

# --- 구매 로직 ---
async def perform_roblox_purchase(cookie, info):
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
        x_token = auth_res.headers.get("x-csrf-token")
        if not x_token: return False, "보안 토큰 만료"
        headers["X-CSRF-TOKEN"] = x_token

        # 실제 구매 요청
        buy_payload = {
            "expectedCurrency": 1,
            "expectedPrice": info['price'],
            "expectedSellerId": 0 # 0으로 설정하면 서버에서 자동 매칭
        }
        
        # ProductId가 상세 정보에 포함되어 있어야 함
        p_id = info.get("productId")
        if not p_id: return False, "상품 ID(ProductId) 조회 실패"

        buy_res = session.post(
            f"https://economy.roblox.com/v1/purchases/products/{p_id}",
            headers=headers,
            json=buy_payload
        )

        if buy_res.status_code == 200:
            result = buy_res.json()
            if result.get("purchased"): return True, "성공"
            return False, result.get("reason", "알 수 없는 거절")
        return False, f"서버 응답 오류 ({buy_res.status_code})"
    except Exception as e:
        return False, str(e)

# --- 구매 확인 뷰 ---
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, robux_price, user_id, cookie):
        super().__init__(timeout=None)
        self.info = info
        self.robux_price = robux_price
        self.user_id = str(user_id)
        self.cookie = cookie

    async def build_ui(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        
        # 정보 섹션
        con.add_item(ui.Section(
            ui.TextDisplay(
                f"### 🛒 구매 확인\n"
                f"- **상품명**: `{self.info['name']}`\n"
                f"- **판매자**: `{self.info['seller']}`\n"
                f"- **가격**: `{self.info['price']:,} R$`\n"
                f"- **결제 예정 금액**: `{self.robux_price:,}원`"
            )
        ))
        
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 버튼 배열
        confirm_btn = ui.Button(label="구매 확정", style=discord.ButtonStyle.success, emoji="✅")
        confirm_btn.callback = self.on_confirm
        
        cancel_btn = ui.Button(label="거부", style=discord.ButtonStyle.danger, emoji="✖️")
        cancel_btn.callback = self.on_cancel
        
        con.add_item(ui.ActionRow(confirm_btn, cancel_btn))
        self.clear_items()
        self.add_item(con)
        return con

    async def on_confirm(self, it: discord.Interaction):
        # 잔액 체크 및 구매 진행 (생략 - 이전 로직과 동일)
        pass

    async def on_cancel(self, it: discord.Interaction):
        await it.response.edit_message(content="취소되었습니다.", view=None)

# --- [수정] 인식 모달 ---
class GamepassModal(ui.Modal, title="게임패스 구매 정보"):
    # 텍스트 입력창 하나로 통합
    data_input = ui.TextInput(
        label="게임패스 링크 또는 ID",
        placeholder="예: 1784490889 또는 링크 전체 입력",
        required=True
    )

    async def on_submit(self, it: discord.Interaction):
        raw = self.data_input.value.strip()
        
        # [해결] 링크 내의 숫자를 추출하는 가장 확실한 정규식
        # https://www.roblox.com/game-pass/1784490889/unnamed 형태 대응
        match = re.findall(r'\d+', raw)
        if not match:
            return await it.response.send_message("❌ 숫자가 포함된 링크나 ID를 입력해주세요.", ephemeral=True)
        
        # 가장 길거나 링크 구조상 ID일 확률이 높은 마지막/첫번째 숫자 선택
        # 보통 roblox 링크에서 ID는 5자리 이상임
        pass_id = next((x for x in match if len(x) >= 5), match[0])

        # 정보 조회
        info = get_gamepass_details(pass_id)
        if not info:
            return await it.response.send_message(f"❌ 게임패스(ID: {pass_id}) 정보를 로블록스 서버에서 찾을 수 없습니다.\n-# 링크가 올바른지 다시 확인해주세요.", ephemeral=True)

        # 가격 설정 로드
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        conn.close()

        if not c_row: return await it.response.send_message("관리자 쿠키가 설정되지 않았습니다.", ephemeral=True)

        rate = int(r_row[0]) if r_row else 1300
        required_money = int((info['price'] / rate) * 10000)

        view = GamepassConfirmView(info, required_money, it.user.id, c_row[0])
        con = await view.build_ui()
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

