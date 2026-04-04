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
# 1️⃣ ID 및 링크 추출
# -----------------------------------
def extract_pass_id(input_str):
    link_match = re.search(r'game-pass/(\d+)', input_str)
    if link_match: return link_match.group(1)
    nums = re.findall(r'\d+', input_str)
    return max(nums, key=len) if nums else None

# -----------------------------------
# 2️⃣ 정보 조회
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
# 3️⃣ [핵심] 실구매 함수 (2단계 우회 로직)
# -----------------------------------
async def purchase_gamepass(product_id, expected_price, seller_id, pass_id):
    """
    410 Gone 해결을 위한 2단계 시도 로직:
    1차: game-passes 전용 엔드포인트 (가장 최신 보안 우회)
    2차: products 일반 엔드포인트 (구형 상품용)
    """
    def _purchase():
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
        conn.close()

        if not row or not row[0]: return {"success": False, "message": "관리자 쿠키 없음"}

        session = requests.Session()
        session.cookies.set(".ROBLOSECURITY", row[0], domain=".roblox.com")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Referer": f"https://www.roblox.com/game-pass/{pass_id}",
            "Origin": "https://www.roblox.com"
        }

        try:
            # CSRF 토큰 갱신
            t_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
            csrf = t_res.headers.get("x-csrf-token")
            if not csrf: return {"success": False, "message": "CSRF 갱신 실패"}
            headers["X-CSRF-TOKEN"] = csrf

            # --- [1차 시도] Gamepass 전용 경로 ---
            url1 = f"https://economy.roblox.com/v1/purchases/game-passes/{pass_id}"
            payload = {
                "expectedPrice": int(expected_price),
                "expectedSellerId": int(seller_id)
            }
            res = session.post(url1, headers=headers, data=json.dumps(payload), timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                if data.get("purchased"): return {"success": True}
            
            # --- [2차 시도] ProductId 일반 경로 (1차 실패 시 실행) ---
            url2 = f"https://economy.roblox.com/v1/purchases/products/{product_id}"
            payload_v2 = {
                "expectedCurrency": 1,
                "expectedPrice": int(expected_price),
                "expectedSellerId": int(seller_id)
            }
            res2 = session.post(url2, headers=headers, data=json.dumps(payload_v2), timeout=10)
            
            if res2.status_code == 200:
                data2 = res2.json()
                if data2.get("purchased"): return {"success": True}
                return {"success": False, "message": data2.get("reason") or "조건 부적합"}
            
            return {"success": False, "message": f"보안 강화 상품 (410) - 엔드포인트 차단됨"}

        except Exception as e:
            return {"success": False, "message": f"통신 에러: {str(e)}"}

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
        text = f"### <:acy2:1489883409001091142> 결제 확인\n-# - **상품**: {self.info['name']}\n-# - **가격**: {self.info['price']:,} R$\n-# - **결제**: {self.money:,}원"
        con.add_item(ui.TextDisplay(text))
        
        row = ui.ActionRow()
        btn_ok = ui.Button(label="결제 승인", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>")
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
            return await it.response.edit_message(view=get_container_view("❌ 잔액 부족", "충전 후 진행하세요.", 0xED4245))

        await it.response.edit_message(view=get_container_view("⌛ 결제 요청 중", "로블록스 보안 서버 우회 중입니다...", 0xFEE75C))

        p_id = self.info.get('productId') or self.info.get('id')
        # 인자 4개 정확히 전달
        result = await purchase_gamepass(p_id, self.info['price'], self.info.get('sellerId'), self.info['id'])
        
        if result["success"]:
            ord_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (ord_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=get_container_view("✅ 결제 완료", f"주문번호: `{ord_id}`\n상품이 성공적으로 전달되었습니다.", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 결제 실패", f"사유: {result['message']}", 0xED4245))
        conn.close()

    async def self_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소됨", "결제를 취소하였습니다.", 0x99AAB5))

# -----------------------------------
# 5️⃣ 모달 (InteractionResponded 해결)
# -----------------------------------
class GamepassModal(ui.Modal, title="게임패스 구매"):
    id_input = ui.TextInput(label="아이디/링크", placeholder="구매할 게임패스 정보를 입력하세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)
        
        pass_id = extract_pass_id(self.id_input.value.strip())
        if not pass_id:
            return await it.followup.send(view=get_container_view("❌ 오류", "올바른 ID 형식이 아닙니다.", 0xED4245), ephemeral=True)

        info = await fetch_gamepass_details(pass_id)
        if not info:
            return await it.followup.send(view=get_container_view("❌ 조회 실패", "로블록스에서 상품 정보를 가져오지 못했습니다.", 0xED4245), ephemeral=True)

        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone(); conn.close()
        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000) if info['price'] > 0 else 0

        view_obj = GamepassConfirmView(info, money, it.user.id)
        await it.followup.send(view=await view_obj.build(), ephemeral=True)

