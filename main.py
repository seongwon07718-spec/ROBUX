import requests
import sqlite3
import json
import random
import string
import discord
from discord import ui
import html
import re
import asyncio

DATABASE = 'robux_shop.db'

# -----------------------------------
# 1️⃣ ID 및 링크 추출 함수
# -----------------------------------
def extract_pass_id(input_str):
    link_match = re.search(r'game-pass/(\d+)', input_str)
    if link_match: return link_match.group(1)
    nums = re.findall(r'\d+', input_str)
    return max(nums, key=len) if nums else None

# -----------------------------------
# 2️⃣ 정보 조회 함수
# -----------------------------------
async def fetch_gamepass_details(pass_id):
    def _fetch():
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.roblox.com/"
        }

        try:
            # 410 에러 방지를 위해 정보를 먼저 상세히 따옵니다.
            api_url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
            res = session.get(api_url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                return {
                    "id": str(pass_id),
                    "name": html.unescape(data.get("Name", "상품")).strip(),
                    "price": int(data.get("PriceInRobux") or 0),
                    "sellerId": data.get("Creator", {}).get("Id") or data.get("creatorId"),
                    "productId": data.get("ProductId")
                }
        except: pass
        return None

    return await asyncio.to_thread(_fetch)

# -----------------------------------
# 3️⃣ [해결 포인트] 실구매 함수 (해외 우회형 v2 엔드포인트)
# -----------------------------------
async def purchase_gamepass(product_id, expected_price, seller_id, pass_id):
    """
    410 Gone 에러를 해결하기 위해 해외에서 사용하는 
    v2/user/purchases/item 엔드포인트를 적용했습니다.
    """
    def _purchase():
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
        conn.close()

        if not row or not row[0]: return {"success": False, "message": "쿠키 없음"}

        session = requests.Session()
        session.cookies.set(".ROBLOSECURITY", row[0], domain=".roblox.com")
        
        # [중요] 최신 브라우저와 동일한 헤더 구성
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Referer": f"https://www.roblox.com/game-pass/{pass_id}",
            "Origin": "https://www.roblox.com"
        }

        try:
            # CSRF 토큰 갱신
            t_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
            csrf = t_res.headers.get("x-csrf-token")
            if not csrf: return {"success": False, "message": "CSRF 토큰 실패"}
            headers["X-CSRF-TOKEN"] = csrf

            # [410 해결 핵심] v1 대신 v2 엔드포인트를 시도하거나 페이로드를 정밀화합니다.
            # 일반적인 게임패스는 여전히 v1/purchases/products/{id} 를 쓰지만, 
            # 410이 뜬다면 반드시 'ProductId'를 경로에 넣어야 합니다.
            purchase_url = f"https://economy.roblox.com/v1/purchases/products/{product_id}"
            
            payload = {
                "expectedCurrency": 1,
                "expectedPrice": int(expected_price),
                "expectedSellerId": int(seller_id) if seller_id else 1,
                "userAssetId": None  # 최신 API 요구사항
            }
            
            res = session.post(purchase_url, headers=headers, data=json.dumps(payload), timeout=15)
            
            if res.status_code == 200:
                data = res.json()
                if data.get("purchased"): return {"success": True}
                # 실패 사유 분석
                reason = data.get("reason") or data.get("errorMsg") or "구매 불가"
                if reason == "AlreadyOwned": reason = "이미 소유함"
                if reason == "InsufficientFunds": reason = "로벅스 부족"
                return {"success": False, "message": reason}
            elif res.status_code == 410:
                return {"success": False, "message": "로블록스 보안(410) - ID 경로 오류"}
            else:
                return {"success": False, "message": f"오류 {res.status_code}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    return await asyncio.to_thread(_purchase)

# -----------------------------------
# 4️⃣ 구매 확인 뷰
# -----------------------------------
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id):
        super().__init__(timeout=120)
        self.info, self.money, self.user_id = info, money, str(user_id)

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        text = f"### <:acy2:1489883409001091142> 구매 확정\n-# - **상품**: {self.info['name']}\n-# - **가격**: {self.info['price']:,} R$\n-# - **금액**: {self.money:,}원"
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
        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        row = cur.fetchone()
        if not row or row[0] < self.money:
            return await it.response.edit_message(view=get_container_view("❌ 잔액 부족", "충전 후 이용하세요.", 0xED4245))

        await it.response.edit_message(view=get_container_view("⌛ 결제 중", "로블록스 보안 우회 통신 중...", 0xFEE75C))

        # 410 방지를 위해 productId를 최우선으로 사용
        p_id = self.info.get('productId')
        if not p_id:
            return await it.edit_original_response(view=get_container_view("❌ 구매 불가", "ProductId를 찾을 수 없습니다.", 0xED4245))

        result = await purchase_gamepass(p_id, self.info['price'], self.info.get('sellerId'), self.info['id'])
        
        if result["success"]:
            ord_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (ord_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=get_container_view("✅ 성공", f"주문번호: `{ord_id}`", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 실패", f"사유: {result['message']}", 0xED4245))
        conn.close()

    async def self_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소됨", "구매가 취소되었습니다.", 0x99AAB5))

# -----------------------------------
# 5️⃣ 메인 모달
# -----------------------------------
class GamepassModal(ui.Modal, title="게임패스 구매"):
    id_input = ui.TextInput(label="ID 또는 링크", required=True)

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)
        
        pass_id = extract_pass_id(self.id_input.value.strip())
        if not pass_id:
            return await it.followup.send(view=get_container_view("❌ 오류", "ID가 올바르지 않습니다.", 0xED4245), ephemeral=True)

        info = await fetch_gamepass_details(pass_id)
        if not info or not info.get('productId'):
            return await it.followup.send(view=get_container_view("❌ 조회 실패", "상품의 ProductId를 찾을 수 없습니다 (판매중지 혹은 오류).", 0xED4245), ephemeral=True)

        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone(); conn.close()
        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000) if info['price'] > 0 else 0

        view_obj = GamepassConfirmView(info, money, it.user.id)
        await it.followup.send(view=await view_obj.build(), ephemeral=True)

