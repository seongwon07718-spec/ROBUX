import discord
from discord import ui
import sqlite3
import requests
import asyncio
import random
import string
import re

DATABASE = 'robux_shop.db'

# --- 모든 메시지를 컨테이너로 만드는 공통 함수 ---
def create_container_msg(title, description, color=0x5865F2, footer=None):
    con = ui.Container()
    con.accent_color = color
    msg = f"### {title}\n{description}"
    if footer:
        msg += f"\n-# {footer}"
    con.add_item(ui.TextDisplay(msg))
    return ui.LayoutView().add_item(con)

def generate_order_id():
    chars = string.ascii_uppercase + string.digits
    return f"{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=6))}"

# --- [최종 해결] 게임패스 정보 조회 (APIS 엔드포인트) ---
def fetch_gamepass_reliable(pass_id):
    """로블록스 최신 APIS 엔드포인트를 사용하여 게임패스 정보를 가져옵니다."""
    try:
        # 이 경로는 현재 가장 안정적으로 게임패스 정보를 반환합니다.
        url = f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
        res = requests.get(url, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            # APIS 응답 구조에 맞게 매핑
            return {
                "id": pass_id,
                "name": data.get("name"),
                "price": data.get("price", 0),
                "sellerId": data.get("creatorId"),
                "sellerName": data.get("creatorName"),
                "productId": data.get("productId") # 구매에 핵심적인 ID
            }
    except Exception as e:
        print(f"API Error: {e}")
    return None

# --- 실제 구매 처리 ---
def execute_roblox_buy(cookie, info):
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Referer": f"https://www.roblox.com/game-pass/{info['id']}"
    }

    try:
        # 1. CSRF 갱신
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        token = auth_res.headers.get("x-csrf-token")
        if not token: return False, "쿠키 세션이 만료되었거나 올바르지 않습니다."
        headers["X-CSRF-TOKEN"] = token

        # 2. 구매 요청 (Economy API)
        buy_url = f"https://economy.roblox.com/v1/purchases/products/{info['productId']}"
        payload = {
            "expectedCurrency": 1,
            "expectedPrice": info['price'],
            "expectedSellerId": info['sellerId']
        }
        
        buy_res = session.post(buy_url, headers=headers, json=payload)
        
        if buy_res.status_code == 200:
            res_data = buy_res.json()
            if res_data.get("purchased"):
                return True, "성공"
            return False, res_data.get("reason", "알 수 없는 거절")
        
        return False, f"HTTP {buy_res.status_code} 오류 (재고 부족 또는 설정 문제)"
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
            f"### 🛒 구매 정보 확인\n"
            f"- **상품명**: `{self.info['name']}`\n"
            f"- **판매자**: `{self.info['sellerName']}`\n"
            f"- **로벅스**: `{self.info['price']:,} R$`\n"
            f"- **결제 금액**: `{self.money:,}원`"
        ))
        
        confirm = ui.Button(label="구매 확정", style=discord.ButtonStyle.success, emoji="✅")
        confirm.callback = self.on_confirm
        cancel = ui.Button(label="거부", style=discord.ButtonStyle.danger, emoji="✖️")
        cancel.callback = self.on_cancel
        
        con.add_item(ui.ActionRow(confirm, cancel))
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
            return await it.response.send_message(view=create_container_msg("❌ 잔액 부족", f"충전 후 이용해주세요.\n필요 금액: `{self.money:,}원`", 0xED4245), ephemeral=True)

        # 처리 중 컨테이너
        await it.response.edit_message(view=create_container_msg("⌛ 처리 중", "로블록스 서버에서 결제를 진행하고 있습니다...", 0xFEE75C))

        success, msg = execute_roblox_buy(self.cookie, self.info)
        
        if success:
            order_id = generate_order_id()
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=create_container_msg("✅ 구매 성공", f"성공적으로 구매되었습니다.\n- **주문번호**: `{order_id}`\n- **잔여 잔액**: `{row[0]-self.money:,}원`", 0x57F287))
        else:
            await it.edit_original_response(view=create_container_msg("❌ 구매 실패 (환불됨)", f"사유: `{msg}`", 0xED4245))
        
        conn.close()

    async def on_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=create_container_msg("✖️ 취소됨", "주문을 취소했습니다.", 0x99AAB5))

# --- 입력 모달 ---
class GamepassModal(ui.Modal, title="게임패스 정보 입력"):
    data_input = ui.TextInput(label="게임패스 링크 또는 ID", placeholder="정확한 링크나 숫자 ID를 입력하세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        raw = self.data_input.value.strip()
        
        # [정규식 보강] 링크에서 ID만 완벽하게 추출
        # 숫자만 있거나, 링크 내부에 숫자(ID)를 찾아냄
        id_search = re.findall(r'\d+', raw)
        if not id_search:
            return await it.response.send_message(view=create_container_msg("❌ 입력 오류", "올바른 게임패스 ID 또는 링크가 아닙니다.", 0xED4245), ephemeral=True)
        
        # 로블록스 ID는 보통 자릿수가 긺. 가장 긴 숫자를 ID로 판단.
        pass_id = max(id_search, key=len)

        # 정보 로드 (신규 API)
        info = fetch_gamepass_reliable(pass_id)
        if not info or not info['name']:
            return await it.response.send_message(view=create_container_msg("❌ 인식 불가", f"ID `{pass_id}`의 정보를 찾을 수 없습니다.\n비공개 아이템이거나 링크가 잘못되었습니다.", 0xED4245), ephemeral=True)

        if info['price'] <= 0:
            return await it.response.send_message(view=create_container_msg("❌ 판매 중지", "가격이 설정되지 않았거나 판매 중인 아이템이 아닙니다.", 0xED4245), ephemeral=True)

        # 설정값 로드
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        conn.close()

        if not c_row:
            return await it.response.send_message(view=create_container_msg("❌ 시스템 에러", "관리자 쿠키가 등록되지 않았습니다.", 0xED4245), ephemeral=True)

        rate = int(r_row[0]) if r_row else 1300
        money = int((info['price'] / rate) * 10000)

        view = GamepassConfirmView(info, money, it.user.id, c_row[0])
        await it.response.send_message(view=await view.build_view(), ephemeral=True)

