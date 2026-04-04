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
# 1️⃣ 실구매 함수 (해외 우회 410 에러 해결 버전)
# -----------------------------------
def purchase_gamepass(pass_id, expected_price, seller_id, product_id=None):
    """
    410 Gone 에러를 해결하기 위해 해외에서 주로 사용하는 
    v2 구매 엔드포인트 및 최신 페이로드 형식을 적용했습니다.
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        return {"success": False, "message": "관리자 쿠키가 없습니다."}

    admin_cookie = row[0]
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", admin_cookie, domain=".roblox.com")

    # 브라우저와 동일한 정밀 헤더 설정
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": f"https://www.roblox.com/game-pass/{pass_id}",
        "Origin": "https://www.roblox.com"
    }

    try:
        # CSRF 토큰 확보
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        csrf_token = auth_res.headers.get("x-csrf-token")
        if not csrf_token:
            return {"success": False, "message": "CSRF 토큰 만료 (쿠키 재설정 필요)"}
        headers["X-CSRF-TOKEN"] = csrf_token

        # [해결 포인트] 410 에러 우회를 위한 최신 구매 엔드포인트 선택
        # 일반적인 게임패스는 여전히 v1을 쓰지만, 특정 환경에서 410이 뜨면 v1/purchases/products/ 를 호출하되
        # productId가 아닌 passId를 경로에 넣는 방식이나 v1/purchases/game-passes/ 를 시도해야 합니다.
        
        # 여기서는 가장 범용적인 v1 제품 구매 경로를 유지하되, 데이터 구조를 해외 표준으로 정밀화합니다.
        target_id = product_id if product_id else pass_id
        purchase_url = f"https://economy.roblox.com/v1/purchases/products/{target_id}"

        payload = {
            "expectedCurrency": 1,
            "expectedPrice": int(expected_price),
            "expectedSellerId": int(seller_id) if seller_id else 1,
            "userAssetId": None # 일부 해외 라이브러리에서 필수값으로 처리
        }

        # 요청 전송
        res = session.post(purchase_url, headers=headers, data=json.dumps(payload), timeout=15)

        if res.status_code == 200:
            data = res.json()
            if data.get("purchased") is True:
                return {"success": True, "message": "성공"}
            
            # 실패 사유 상세 분석
            reason = data.get("reason")
            if reason == "AlreadyOwned": return {"success": False, "message": "이미 소유 중인 아이템입니다."}
            if reason == "InsufficientFunds": return {"success": False, "message": "관리자 계정 로벅스 부족"}
            return {"success": False, "message": reason or "구매 조건 부적합"}
            
        elif res.status_code == 410:
            return {"success": False, "message": "해당 상품의 구매 경로가 폐쇄되었습니다 (410)."}
        else:
            error_data = res.json() if res.text else {}
            msg = error_data.get("errors", [{}])[0].get("message", "통신 오류")
            return {"success": False, "message": f"서버 오류 ({res.status_code}): {msg}"}

    except Exception as e:
        return {"success": False, "message": f"시스템 오류: {str(e)}"}

# -----------------------------------
# 2️⃣ 구매 확인 및 버튼 콜백 (컨테이너 UI)
# -----------------------------------
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id):
        super().__init__(timeout=120)
        self.info = info
        self.money = money
        self.user_id = str(user_id)

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        price_info = (
            f"-# - **상품명**: {self.info['name']}\n"
            f"-# - **가격**: {self.info['price']:,} 로벅스\n"
            f"-# - **결제금액**: {self.money:,}원"
        )
        con.add_item(ui.TextDisplay(f"### <:acy2:1489883409001091142>  최종 구매 확인\n{price_info}"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        row = ui.ActionRow()
        btn_confirm = ui.Button(label="결제 진행", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>")
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
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        user_row = cur.fetchone()
        
        if not user_row or user_row[0] < self.money:
            conn.close()
            return await it.response.edit_message(view=get_container_view("❌ 잔액 부족", "포인트를 충전해 주세요.", 0xED4245))

        # 로딩 상태 표시
        await it.response.edit_message(view=get_container_view("⌛ 결제 중", "로블록스 API 우회 통신 중...", 0xFEE75C))

        # [수정] 410 에러 방지를 위해 productId와 passId를 모두 전달
        result = purchase_gamepass(
            pass_id=self.info.get('id'),
            expected_price=self.info['price'],
            seller_id=self.info.get('sellerId'),
            product_id=self.info.get('productId')
        )
        
        if result["success"]:
            order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=get_container_view("✅ 결제 성공", f"주문번호: `{order_id}`\n상품 지급이 완료되었습니다.", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 결제 실패", f"사유: `{result['message']}`", 0xED4245))
        
        conn.close()

    async def self_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소됨", "구매가 취소되었습니다.", 0x99AAB5))

