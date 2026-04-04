import requests
import sqlite3
import json
import random
import string
import discord
from discord import ui
import html
import re

DATABASE = 'robux_shop.db'

# -----------------------------------
# 1️⃣ 로블록스 구매 핵심 함수 (InvalidArguments 해결)
# -----------------------------------
def purchase_gamepass(product_id, expected_price, seller_id):
    """
    로블록스 API 사양에 맞춘 구매 함수입니다.
    데이터 타입을 int로 강제 변환하여 인자 오류를 방지합니다.
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        return {"success": False, "message": "관리자 쿠키가 설정되지 않았습니다."}

    admin_cookie = row[0]
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", admin_cookie, domain=".roblox.com")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com"
    }

    try:
        # CSRF 토큰 갱신
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        csrf_token = auth_res.headers.get("x-csrf-token")
        if not csrf_token:
            return {"success": False, "message": "CSRF 토큰 획득 실패 (쿠키 만료 확인 필요)"}
        
        headers["X-CSRF-TOKEN"] = csrf_token

        # 구매 요청 실행 (v1 purchase endpoint)
        purchase_url = f"https://economy.roblox.com/v1/purchases/products/{product_id}"
        
        # [중요] InvalidArguments 방지: 모든 값을 명시적으로 int로 변환
        payload = {
            "expectedCurrency": 1,
            "expectedPrice": int(expected_price),
            "expectedSellerId": int(seller_id) if seller_id else 1
        }

        res = session.post(purchase_url, headers=headers, data=json.dumps(payload), timeout=10)

        if res.status_code == 200:
            data = res.json()
            if data.get("purchased") is True:
                return {"success": True, "message": "구매 성공!", "data": data}
            else:
                reason = data.get("reason") or data.get("errorMsg") or "알 수 없는 오류"
                return {"success": False, "message": reason}
        else:
            error_data = res.json() if res.text else {}
            error_msg = error_data.get("errors", [{}])[0].get("message", res.text)
            return {"success": False, "message": f"서버 오류: {error_msg}"}
    except Exception as e:
        return {"success": False, "message": f"시스템 오류: {str(e)}"}

# -----------------------------------
# 2️⃣ 구매 확인 및 버튼 콜백 (컨테이너 UI 적용)
# -----------------------------------
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
        price_info = (
            f"-# - **게임패스 이름**: {self.info['name']}\n"
            f"-# - **게임패스 가격**: {self.info['price']:,}로벅스\n"
            f"-# - **결제금액**: {self.money:,}원"
        )
        con.add_item(ui.TextDisplay(f"### <:acy2:1489883409001091142>  구매 단계\n{price_info}"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        row = ui.ActionRow()
        btn_confirm = ui.Button(label="진행", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>")
        btn_confirm.callback = self.self_confirm
        
        btn_cancel = ui.Button(label="취소", style=discord.ButtonStyle.gray, emoji="<:downvote:1489930277450158080>")
        btn_cancel.callback = self.self_cancel
        
        row.add_item(btn_confirm)
        row.add_item(btn_cancel)
        con.add_item(row)
        self.clear_items()
        self.add_item(con)
        return self

    async def self_confirm(self, it: discord.Interaction):
        # 1. 잔액 검사
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        row = cur.fetchone()
        
        if not row or row[0] < self.money:
            conn.close()
            return await it.response.edit_message(view=get_container_view("❌ 잔액 부족", "충전 후 다시 시도해 주세요.", 0xED4245))

        # 2. 처리 중 메시지
        await it.response.edit_message(view=get_container_view("⌛ 처리 중", "로블록스 서버와 통신 중입니다...", 0xFEE75C))

        # 3. 실제 구매 실행 (info에서 sellerId를 반드시 추출하여 전달)
        result = purchase_gamepass(
            product_id=self.info['productId'], 
            expected_price=self.info['price'], 
            seller_id=self.info.get('sellerId')
        )
        
        if result["success"]:
            # 성공 시 데이터 처리
            order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            
            # 컨테이너 뷰로 성공 알림
            await it.edit_original_response(view=get_container_view("✅ 구매 성공", f"주문번호: `{order_id}`\n지급이 완료되었습니다.", 0x57F287))
        else:
            # 실패 사유 전송
            await it.edit_original_response(view=get_container_view("❌ 구매 실패", f"사유: `{result['message']}`", 0xED4245))
        
        conn.close()

    async def self_cancel(self, it: discord.Interaction):
        # 취소 컨테이너 뷰
        await it.response.edit_message(view=get_container_view("취소됨", "구매 요청을 취소했습니다.", 0x99AAB5))

# -----------------------------------
# 3️⃣ 메인 모달 (입력 처리)
# -----------------------------------
class GamepassModal(ui.Modal, title="게임패스 방식"):
    id_input = ui.TextInput(label="게임패스 ID 또는 링크", placeholder="아이디나 링크를 입력하세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        # 타임아웃 방지
        await it.response.defer(ephemeral=True)
        
        raw_val = self.id_input.value.strip()
        pass_id = extract_pass_id(raw_val) # ID 추출 함수 호출 (별도 정의 필요)
        
        if not pass_id:
            return await it.followup.send(view=get_container_view("❌ 입력 오류", "올바른 ID나 링크를 입력해주세요.", 0xED4245), ephemeral=True)

        # 정보 가져오기 (fetch_gamepass_details 별도 정의 필요)
        info = fetch_gamepass_details(pass_id)
        
        if not info or info.get('productId') is None:
            return await it.followup.send(view=get_container_view("❌ 정보 조회 실패", f"ID `{pass_id}` 정보를 불러올 수 없습니다.", 0xED4245), ephemeral=True)

        # 비율 계산
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000) if info['price'] > 0 else 0

        # 구매 확인 단계 빌드
        view_obj = GamepassConfirmView(info, money, it.user.id, "DB_COOKIE")
        await it.followup.send(view=await view_obj.build(), ephemeral=True)

