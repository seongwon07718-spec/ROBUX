import discord
from discord import ui
import sqlite3
import requests
import asyncio
import random
import string
import re

DATABASE = 'robux_shop.db'

# --- 유틸리티: 모든 응답을 컨테이너로 감싸는 함수 ---
def wrap_in_container(title, description, color=0x5865F2, items=None):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"### {title}\n{description}"))
    if items:
        for item in items:
            con.add_item(item)
    return ui.LayoutView().add_item(con)

def generate_order_id():
    chars = string.ascii_uppercase + string.digits
    return f"{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=6))}"

# --- [글로벌 표준] 카탈로그 아이템 상세 조회 API ---
def fetch_gamepass_details(pass_id):
    """해외 대형 자판기에서 사용하는 카탈로그 조회 방식입니다."""
    try:
        url = "https://catalog.roblox.com/v1/catalog/items/details"
        # ItemType 1은 GamePass를 의미합니다.
        payload = {"items": [{"itemType": 1, "id": int(pass_id)}]}
        res = requests.post(url, json=payload, timeout=7)
        
        if res.status_code == 200:
            data = res.json().get('data', [])
            if data:
                item = data[0]
                # 필수 정보: 이름, 가격, 판매자ID, 제품ID(구매에 필수)
                return {
                    "id": pass_id,
                    "name": item.get("name"),
                    "price": item.get("price", 0),
                    "sellerId": item.get("creatorTargetId"),
                    "productId": item.get("productId")
                }
    except Exception as e:
        print(f"Fetch Error: {e}")
    return None

# --- [글로벌 표준] 실제 구매 프로세스 API ---
def process_real_buy(cookie, info):
    """로블록스 경제 시스템 구매 API 엔드포인트입니다."""
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json",
        "Referer": f"https://www.roblox.com/game-pass/{info['id']}"
    }

    try:
        # 1. CSRF 갱신 (반드시 시도해야 함)
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        token = auth_res.headers.get("x-csrf-token")
        if not token: return False, "보안 토큰 획득 실패 (쿠키 만료 의심)"
        headers["X-CSRF-TOKEN"] = token

        # 2. 구매 페이로드
        buy_url = f"https://economy.roblox.com/v1/purchases/products/{info['productId']}"
        payload = {
            "expectedCurrency": 1,
            "expectedPrice": info['price'],
            "expectedSellerId": info['sellerId']
        }
        
        buy_res = session.post(buy_url, headers=headers, json=payload)
        
        if buy_res.status_code == 200:
            res_json = buy_res.json()
            if res_json.get("purchased"):
                return True, "성공"
            return False, res_json.get("reason", "알 수 없는 오류")
        return False, f"HTTP {buy_res.status_code} 오류"
    except Exception as e:
        return False, str(e)

# --- 구매 확인 뷰 ---
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id, cookie):
        super().__init__(timeout=None)
        self.info = info
        self.money = money
        self.user_id = str(user_id)
        self.cookie = cookie

    async def build_view(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            f"### 🛒 주문 정보 확인\n"
            f"- **아이템**: `{self.info['name']}`\n"
            f"- **가격**: `{self.info['price']:,} R$`\n"
            f"- **결제 금액**: `{self.money:,}원` (잔액 차감)\n\n"
            f"정말로 구매하시겠습니까?"
        ))
        
        btn_row = ui.ActionRow()
        confirm = ui.Button(label="구매 확정", style=discord.ButtonStyle.success, emoji="✅")
        confirm.callback = self.on_confirm
        cancel = ui.Button(label="거부", style=discord.ButtonStyle.danger, emoji="✖️")
        cancel.callback = self.on_cancel
        
        btn_row.add_item(confirm)
        btn_row.add_item(cancel)
        con.add_item(btn_row)
        
        self.clear_items()
        self.add_item(con)
        return self

    async def on_confirm(self, it: discord.Interaction):
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        user_balance = cur.fetchone()

        if not user_balance or user_balance[0] < self.money:
            conn.close()
            return await it.response.send_message(view=wrap_in_container("❌ 잔액 부족", f"현재 잔액이 부족합니다.\n필요 금액: `{self.money:,}원`", 0xED4245), ephemeral=True)

        # 로딩 표시
        await it.response.edit_message(view=wrap_in_container("⌛ 처리 중", "로블록스 서버와 통신 중입니다...", 0xFEE75C))

        # 실제 구매
        success, msg = process_real_buy(self.cookie, self.info)
        
        if success:
            order_id = generate_order_id()
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=wrap_in_container("✅ 구매 완료", f"주문이 성공적으로 처리되었습니다.\n- **주문번호**: `{order_id}`\n- **상품**: `{self.info['name']}`", 0x57F287))
        else:
            await it.edit_original_response(view=wrap_in_container("❌ 구매 실패 (자동 환불)", f"사유: `{msg}`\n잔액은 차감되지 않았습니다.", 0xED4245))
        
        conn.close()

    async def on_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=wrap_in_container("✖️ 취소됨", "구매가 취소되었습니다.", 0x99AAB5))

# --- 메인 모달 ---
class GamepassModal(ui.Modal, title="게임패스 구매 정보"):
    link_or_id = ui.TextInput(label="게임패스 링크 또는 ID", placeholder="링크를 붙여넣거나 숫자 ID만 입력하세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        raw = self.link_or_id.value.strip()
        # 모든 숫자 그룹을 찾아 가장 긴 것(ID)을 선택하는 로직
        nums = re.findall(r'\d+', raw)
        if not nums:
            return await it.response.send_message(view=wrap_in_container("❌ 인식 실패", "입력값에서 숫자 ID를 찾을 수 없습니다.", 0xED4245), ephemeral=True)
        
        pass_id = max(nums, key=len)

        # 정보 로드
        info = fetch_gamepass_details(pass_id)
        if not info:
            return await it.response.send_message(view=wrap_in_container("❌ 조회 실패", f"로블록스에서 ID `{pass_id}`의 정보를 가져오지 못했습니다.", 0xED4245), ephemeral=True)

        if info['price'] <= 0:
            return await it.response.send_message(view=wrap_in_container("❌ 판매 중지", "이 아이템은 현재 판매 중이 아닙니다.", 0xED4245), ephemeral=True)

        # 가격 계산
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        rate_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        cookie_row = cur.fetchone()
        conn.close()

        if not cookie_row:
            return await it.response.send_message(view=wrap_in_container("❌ 시스템 오류", "관리자 쿠키가 설정되지 않았습니다.", 0xED4245), ephemeral=True)

        rate = int(rate_row[0]) if rate_row else 1300
        money = int((info['price'] / rate) * 10000)

        confirm_view = GamepassConfirmView(info, money, it.user.id, cookie_row[0])
        await it.response.send_message(view=await confirm_view.build_view(), ephemeral=True)

