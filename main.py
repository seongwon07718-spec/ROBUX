import asyncio
import sqlite3
import random
import string
import re
import discord
from discord import ui
from roblox import Client
from roblox.items import ItemType

DATABASE = 'robux_shop.db'

# -----------------------------------
# 1️⃣ 아이디 및 링크 추출 (정규식 강화)
# -----------------------------------
def extract_pass_id(input_str):
    if not input_str: return None
    # 링크 형태 (game-pass/12345) 또는 숫자만 있는 형태 모두 대응
    link_match = re.search(r'game-pass/(\d+)', input_str)
    if link_match: return int(link_match.group(1))
    nums = re.findall(r'\d+', input_str)
    return int(max(nums, key=len)) if nums else None

# -----------------------------------
# 2️⃣ 해외 샵 표준 구매 엔진 (roblox.py 기반)
# -----------------------------------
async def execute_roblox_purchase(pass_id: int, user_id: str, money: int):
    """
    해외 대행 샵에서 사용하는 roblox.py 표준 구매 로직입니다.
    인자 개수 오류를 방지하기 위해 필요한 데이터만 정확히 전달받습니다.
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        return {"success": False, "message": "관리자 쿠키가 설정되지 않았습니다."}

    try:
        # 클라이언트 세션 생성
        client = Client(row[0])
        
        # [해외 샵 표준] ItemType.gamepass를 명시하여 정확한 객체 로드
        # 스크린샷의 'ItemType 함수 없음' 에러를 방지하기 위해 상단에서 정확히 임포트함
        item = await client.get_base_item(item_id=pass_id, item_type=ItemType.gamepass)
        
        if not item:
            return {"success": False, "message": "아이템 정보를 불러올 수 없습니다."}

        # [핵심] purchase() 메서드는 내부적으로 410 Gone 에러 방지 헤더를 포함함
        try:
            await item.purchase()
            
            # 구매 성공 시 DB 트랜잭션 처리
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()
            order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            
            # 잔액 차감 및 주문 기록
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (money, user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, user_id, money, item.price))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "order_id": order_id, "item_name": item.name}

        except Exception as buy_error:
            err_msg = str(buy_error)
            if "AlreadyOwned" in err_msg: return {"success": False, "message": "이미 보유 중인 상품"}
            if "InsufficientFunds" in err_msg: return {"success": False, "message": "봇 계정 잔액 부족"}
            return {"success": False, "message": f"구매 거부: {err_msg}"}

    except Exception as sys_error:
        return {"success": False, "message": f"시스템 오류: {str(sys_error)}"}

# -----------------------------------
# 3️⃣ 결제 확인 뷰 (UI/UX 최적화)
# -----------------------------------
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id):
        super().__init__(timeout=120)
        self.info = info  # {'id': int, 'name': str, 'price': int}
        self.money = money
        self.user_id = str(user_id)

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        text = (f"### <:acy2:1489883409001091142> 로벅스 결제 승인\n"
                f"-# - **상품명**: {self.info['name']}\n"
                f"-# - **로벅스**: {self.info['price']:,} R$\n"
                f"-# - **결제금액**: {self.money:,}원")
        con.add_item(ui.TextDisplay(text))
        
        row = ui.ActionRow()
        btn_ok = ui.Button(label="결제 승인", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>")
        btn_ok.callback = self.on_confirm
        btn_no = ui.Button(label="취소", style=discord.ButtonStyle.gray, emoji="<:downvote:1489930277450158080>")
        btn_no.callback = self.on_cancel
        
        row.add_item(btn_ok); row.add_item(btn_no)
        con.add_item(row)
        self.clear_items(); self.add_item(con)
        return self

    async def on_confirm(self, it: discord.Interaction):
        # 1. 유저 잔액 재확인
        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        row = cur.fetchone(); conn.close()
        
        if not row or row[0] < self.money:
            return await it.response.edit_message(view=get_container_view("❌ 잔액 부족", "충전 후 다시 시도해주세요.", 0xED4245))

        await it.response.edit_message(view=get_container_view("⌛ 처리 중", "해외 표준 API를 통해 결제 중입니다...", 0xFEE75C))

        # 2. 해외 샵 표준 엔진 가동 (정확히 3개 인자 전달)
        result = await execute_roblox_purchase(self.info['id'], self.user_id, self.money)
        
        if result["success"]:
            await it.edit_original_response(view=get_container_view("✅ 결제 성공", f"주문번호: `{result['order_id']}`\n성공적으로 지급되었습니다.", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 결제 실패", f"사유: {result['message']}", 0xED4245))

    async def on_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("결제 취소", "요청하신 결제가 취소되었습니다.", 0x99AAB5))

# -----------------------------------
# 4️⃣ 메인 모달
# -----------------------------------
class GamepassModal(ui.Modal, title="게임패스 구매"):
    id_input = ui.TextInput(label="아이템 ID 또는 링크", placeholder="예: 1784490889", required=True)

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)
        
        p_id = extract_pass_id(self.id_input.value.strip())
        if not p_id:
            return await it.followup.send(view=get_container_view("❌ 입력 오류", "올바른 아이디 형식이 아닙니다.", 0xED4245), ephemeral=True)

        # 관리자 쿠키 확인
        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone(); conn.close()
        
        if not c_row:
            return await it.followup.send(view=get_container_view("❌ 설정 오류", "쿠키가 등록되지 않았습니다.", 0xED4245), ephemeral=True)

        try:
            # 조회 단계 (roblox.py 표준 방식)
            client = Client(c_row[0])
            item = await client.get_base_item(item_id=p_id, item_type=ItemType.gamepass)
            
            info = {"id": p_id, "name": item.name, "price": item.price}

            # 가격 계산
            conn = sqlite3.connect(DATABASE); cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
            r_row = cur.fetchone(); conn.close()
            rate = int(r_row[0]) if r_row else 1000
            money = int((info['price'] / rate) * 10000) if info['price'] > 0 else 0

            view_obj = GamepassConfirmView(info, money, it.user.id)
            await it.followup.send(view=await view_obj.build(), ephemeral=True)
            
        except Exception as e:
            await it.followup.send(view=get_container_view("❌ 조회 실패", f"상품 정보 획득 실패: {str(e)}", 0xED4245), ephemeral=True)

