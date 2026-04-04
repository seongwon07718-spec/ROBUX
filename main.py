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
# 1️⃣ 정보 조회 함수 (productId 추출 강화)
# -----------------------------------
def fetch_gamepass_details(pass_id):
    """
    해외 개발자들이 410 에러 방지를 위해 사용하는 방식:
    조회 API에서 반드시 'ProductId'를 따와야 실구매가 가능합니다.
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    row = cur.fetchone()
    conn.close()
    
    admin_cookie = row[0] if row else None
    session = requests.Session()
    if admin_cookie:
        session.cookies.set(".ROBLOSECURITY", admin_cookie, domain=".roblox.com")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://www.roblox.com/"
    }

    try:
        # 1차: Economy API (가장 정확함)
        api_url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = session.get(api_url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return {
                "id": str(pass_id),
                "name": html.unescape(data.get("Name", "이름 없음")).strip(),
                "price": int(data.get("PriceInRobux") or 0),
                "sellerId": data.get("Creator", {}).get("Id") or data.get("creatorId"),
                "productId": data.get("ProductId") # 구매 시 필수!
            }
    except: pass

    try:
        # 2차: 웹 데이터 파싱
        url = f"https://www.roblox.com/game-pass/{pass_id}"
        res = session.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            res.encoding = 'utf-8'
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', res.text)
            if match:
                data = json.loads(match.group(1))
                info = data.get("props", {}).get("pageProps", {}).get("gamePassInfo", {})
                return {
                    "id": str(pass_id),
                    "name": html.unescape(info.get("name") or "이름 없음").strip(),
                    "price": int(info.get("price") or 0),
                    "sellerId": info.get("creatorId"),
                    "productId": info.get("productId")
                }
    except: pass

    return None

# -----------------------------------
# 2️⃣ 실구매 함수 (410 에러 우회 버전)
# -----------------------------------
def purchase_gamepass(product_id, expected_price, seller_id, pass_id):
    """
    해외 Noblox.js 표준을 따르는 구매 로직.
    410 Gone 에러 방지: 반드시 ProductId를 경로에 포함해야 합니다.
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        return {"success": False, "message": "관리자 쿠키가 설정되지 않았습니다."}

    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", row[0], domain=".roblox.com")

    # 해외 표준 헤더 (Referer 필수)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": f"https://www.roblox.com/game-pass/{pass_id}",
        "Origin": "https://www.roblox.com"
    }

    try:
        # CSRF 토큰 갱신
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        csrf_token = auth_res.headers.get("x-csrf-token")
        if not csrf_token:
            return {"success": False, "message": "CSRF 토큰 획득 실패 (쿠키 만료)"}
        headers["X-CSRF-TOKEN"] = csrf_token

        # [핵심] 410 에러 해결: 경로에 ProductId 사용
        purchase_url = f"https://economy.roblox.com/v1/purchases/products/{product_id}"
        
        payload = {
            "expectedCurrency": 1,
            "expectedPrice": int(expected_price),
            "expectedSellerId": int(seller_id) if seller_id else 1
        }

        res = session.post(purchase_url, headers=headers, data=json.dumps(payload), timeout=15)

        if res.status_code == 200:
            data = res.json()
            if data.get("purchased") is True:
                return {"success": True, "message": "구매 성공"}
            reason = data.get("reason") or data.get("errorMsg") or "구매 조건 부적합"
            return {"success": False, "message": reason}
        elif res.status_code == 410:
            return {"success": False, "message": "상품 경로 폐쇄 (410 Gone) - ID 불일치"}
        else:
            return {"success": False, "message": f"서버 오류 ({res.status_code})"}

    except Exception as e:
        return {"success": False, "message": f"시스템 장애: {str(e)}"}

# -----------------------------------
# 3️⃣ 구매 확인 뷰 (컨테이너 UI)
# -----------------------------------
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id):
        super().__init__(timeout=120)
        self.info, self.money, self.user_id = info, money, str(user_id)

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        price_info = (
            f"-# - **아이템**: {self.info['name']}\n"
            f"-# - **로벅스**: {self.info['price']:,} R$\n"
            f"-# - **금액**: {self.money:,}원"
        )
        con.add_item(ui.TextDisplay(f"### <:acy2:1489883409001091142>  최종 결제 확인\n{price_info}"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        row = ui.ActionRow()
        btn_confirm = ui.Button(label="결제 승인", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>")
        btn_confirm.callback = self.self_confirm
        btn_cancel = ui.Button(label="결제 취소", style=discord.ButtonStyle.gray, emoji="<:downvote:1489930277450158080>")
        btn_cancel.callback = self.self_cancel
        
        row.add_item(btn_confirm)
        row.add_item(btn_cancel)
        con.add_item(row)
        self.clear_items()
        self.add_item(con)
        return self

    async def self_confirm(self, it: discord.Interaction):
        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        user_row = cur.fetchone()
        
        if not user_row or user_row[0] < self.money:
            conn.close()
            return await it.response.edit_message(view=get_container_view("❌ 잔액 부족", "포인트 충전 후 이용해주세요.", 0xED4245))

        await it.response.edit_message(view=get_container_view("⌛ 처리 중", "해외 우회 서버와 통신 중입니다...", 0xFEE75C))

        # 실구매 실행 (ProductId가 없을 경우를 대비해 pass_id로 백업)
        p_id = self.info.get('productId') or self.info.get('id')
        result = purchase_gamepass(p_id, self.info['price'], self.info.get('sellerId'), self.info['id'])
        
        if result["success"]:
            order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=get_container_view("✅ 구매 완료", f"주문번호: `{order_id}`\n상품 지급이 완료되었습니다.", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 구매 실패", f"사유: `{result['message']}`", 0xED4245))
        conn.close()

    async def self_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소됨", "구매 요청을 거부하였습니다.", 0x99AAB5))

# -----------------------------------
# 4️⃣ 메인 모달
# -----------------------------------
class GamepassModal(ui.Modal, title="게임패스 구매"):
    id_input = ui.TextInput(label="ID 또는 링크", placeholder="아이디나 링크를 입력하세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)
        
        pass_id = extract_pass_id(self.id_input.value.strip())
        if not pass_id:
            return await it.followup.send(view=get_container_view("❌ 입력 오류", "올바른 링크 형식이 아닙니다.", 0xED4245), ephemeral=True)

        info = fetch_gamepass_details(pass_id)
        if not info:
            return await it.followup.send(view=get_container_view("❌ 조회 실패", "로블록스에서 상품을 찾을 수 없습니다.", 0xED4245), ephemeral=True)

        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone(); conn.close()
        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000) if info['price'] > 0 else 0

        view_obj = GamepassConfirmView(info, money, it.user.id)
        await it.followup.send(view=await view_obj.build(), ephemeral=True)

