import asyncio
import sqlite3
import random
import string
import re
import html
import discord
from discord import ui
from roblox import Client

DATABASE = 'robux_shop.db'

# -----------------------------------
# 1️⃣ ID 및 링크 추출 함수
# -----------------------------------
def extract_pass_id(input_str):
    if not input_str: return None
    link_match = re.search(r'game-pass/(\d+)', input_str)
    if link_match: return link_match.group(1)
    nums = re.findall(r'\d+', input_str)
    return max(nums, key=len) if nums else None

# -----------------------------------
# 2️⃣ 정보 조회 및 구매 로직 (roblox.py 기반)
# -----------------------------------
async def process_roblox_purchase(pass_id, user_id, money):
    """
    roblox.py 라이브러리를 사용하여 정보를 조회하고 구매를 수행합니다.
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        return {"success": False, "message": "관리자 쿠키가 설정되지 않았습니다."}

    try:
        # roblox.py 클라이언트 초기화
        client = Client(row[0])
        
        # 1. 게임패스 정보 가져오기
        # get_gamepass는 내부적으로 economy v1 API를 최적화해서 호출합니다.
        gamepass = await client.get_gamepass(int(pass_id))
        
        if not gamepass:
            return {"success": False, "message": "상품 정보를 찾을 수 없습니다."}

        # 2. 구매 수행 (roblox.py의 purchase 기능을 사용하면 410 에러 방지용 헤더가 자동 포함됨)
        # 이미 소유한 경우를 대비해 예외 처리를 강화합니다.
        try:
            await gamepass.purchase()
            
            # 3. 구매 성공 시 DB 처리 (돈 차감 및 주문 기록)
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()
            ord_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (money, str(user_id)))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (ord_id, str(user_id), money, gamepass.price))
            conn.commit()
            conn.close()
            
            return {"success": True, "order_id": ord_id, "name": gamepass.name, "price": gamepass.price}
            
        except Exception as p_error:
            # roblox.py에서 발생하는 에러 메시지 처리
            error_msg = str(p_error)
            if "AlreadyOwned" in error_msg:
                return {"success": False, "message": "이미 소유한 아이템입니다."}
            elif "InsufficientFunds" in error_msg:
                return {"success": False, "message": "관리자 계정의 로벅스가 부족합니다."}
            return {"success": False, "message": f"구매 실패: {error_msg}"}

    except Exception as e:
        return {"success": False, "message": f"시스템 에러: {str(e)}"}

# -----------------------------------
# 3️⃣ 구매 확인 뷰
# -----------------------------------
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id):
        super().__init__(timeout=120)
        self.info, self.money, self.user_id = info, money, user_id

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        text = f"### <:acy2:1489883409001091142> 최종 결제 확인\n-# - **아이템**: {self.info['name']}\n-# - **가격**: {self.info['price']:,} R$\n-# - **결제금액**: {self.money:,}원"
        con.add_item(ui.TextDisplay(text))
        
        row = ui.ActionRow()
        btn_ok = ui.Button(label="승인", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>")
        btn_ok.callback = self.self_confirm
        btn_no = ui.Button(label="취소", style=discord.ButtonStyle.gray, emoji="<:downvote:1489930277450158080>")
        btn_no.callback = self.self_cancel
        row.add_item(btn_ok); row.add_item(btn_no)
        con.add_item(row)
        self.clear_items(); self.add_item(con)
        return self

    async def self_confirm(self, it: discord.Interaction):
        # 1. 잔액 확인
        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (str(self.user_id),))
        row = cur.fetchone(); conn.close()
        
        if not row or row[0] < self.money:
            return await it.response.edit_message(view=get_container_view("❌ 잔액 부족", "충전 후 다시 이용해주세요.", 0xED4245))

        await it.response.edit_message(view=get_container_view("⌛ 처리 중", "roblox.py 라이브러리를 통해 결제 진행 중...", 0xFEE75C))

        # 2. 실제 구매 처리 (roblox.py 라이브러리 사용)
        result = await process_roblox_purchase(self.info['id'], self.user_id, self.money)
        
        if result["success"]:
            await it.edit_original_response(view=get_container_view("✅ 결제 완료", f"주문번호: `{result['order_id']}`\n정상적으로 지급되었습니다.", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 결제 실패", f"사유: {result['message']}", 0xED4245))

    async def self_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소됨", "구매 요청이 취소되었습니다.", 0x99AAB5))

# -----------------------------------
# 4️⃣ 메인 모달
# -----------------------------------
class GamepassModal(ui.Modal, title="게임패스 구매"):
    id_input = ui.TextInput(label="아이템 ID 또는 링크", required=True)

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)
        
        pass_id = extract_pass_id(self.id_input.value.strip())
        if not pass_id:
            return await it.followup.send(view=get_container_view("❌ 입력 오류", "올바른 정보를 입력해주세요.", 0xED4245), ephemeral=True)

        # 정보 조회를 위해 임시 클라이언트 생성
        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone(); conn.close()
        
        if not c_row:
            return await it.followup.send(view=get_container_view("❌ 설정 오류", "쿠키가 설정되지 않았습니다.", 0xED4245), ephemeral=True)

        try:
            client = Client(c_row[0])
            gamepass = await client.get_gamepass(int(pass_id))
            
            info = {
                "id": str(pass_id),
                "name": gamepass.name,
                "price": gamepass.price
            }

            conn = sqlite3.connect(DATABASE); cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
            r_row = cur.fetchone(); conn.close()
            rate = int(r_row[0]) if r_row else 1000
            money = int((info['price'] / rate) * 10000) if info['price'] > 0 else 0

            view_obj = GamepassConfirmView(info, money, it.user.id)
            await it.followup.send(view=await view_obj.build(), ephemeral=True)
            
        except Exception as e:
            await it.followup.send(view=get_container_view("❌ 조회 실패", f"상품 정보를 가져올 수 없습니다.\n사유: {str(e)}", 0xED4245), ephemeral=True)

