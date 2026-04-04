import asyncio
import sqlite3
import random
import string
import re
import aiohttp
import discord
from discord import ui

DATABASE = 'robux_shop.db'

# -----------------------------------
# 1️⃣ ID 추출 함수
# -----------------------------------
def extract_pass_id(input_str):
    if not input_str: return None
    link_match = re.search(r'game-pass/(\d+)', input_str)
    if link_match: return int(link_match.group(1))
    nums = re.findall(r'\d+', input_str)
    return int(max(nums, key=len)) if nums else None

# -----------------------------------
# 2️⃣ 직접 우회 구매 엔진 (해외 고성능 샵 방식)
# -----------------------------------
async def direct_roblox_purchase(pass_id: int, user_id: str, money: int):
    """
    라이브러리 없이 직접 로블록스 API를 찌르는 방식입니다.
    CSRF 토큰을 실시간으로 갱신하여 403/410 에러를 방지합니다.
    """
    conn = sqlite3.connect(DATABASE); cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    row = cur.fetchone(); conn.close()

    if not row or not row[0]:
        return {"success": False, "message": "쿠키가 설정되지 않았습니다."}

    cookie = row[0]
    # .ROBLOSECURITY 형식이 아니면 자동으로 맞춰줌
    if not cookie.startswith("_|WARNING"):
        cookie = f".ROBLOSECURITY={cookie}"

    async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": cookie.split('=')[-1]}) as session:
        # A. 상품 정보 및 ProductId 조회
        info_url = f"https://economy.roblox.com/v1/game-pass/{pass_id}/product-info"
        async with session.get(info_url) as resp:
            if resp.status != 200:
                return {"success": False, "message": f"정보 조회 실패 (코드: {resp.status})"}
            data = await resp.json()
            product_id = data.get("ProductId")
            price = data.get("PriceInRobux", 0)
            seller_id = data.get("Creator", {}).get("Id")

        # B. 구매를 위한 CSRF 토큰 획득 (해외 샵 필수 로직)
        headers = {
            "Content-Type": "application/json",
            "Referer": f"https://www.roblox.com/game-pass/{pass_id}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # 빈 포스트를 보내 토큰을 강제로 받아옴
        async with session.post("https://auth.roblox.com/v2/logout") as resp:
            csrf_token = resp.headers.get("x-csrf-token")
        
        if not csrf_token:
            return {"success": False, "message": "CSRF 토큰 획득 실패 (쿠키 만료 가능성)"}
        
        headers["x-csrf-token"] = csrf_token

        # C. 실제 구매 요청 (Economy API v1)
        buy_url = f"https://economy.roblox.com/v1/purchases/products/{product_id}"
        payload = {
            "expectedCurrency": 1,
            "expectedPrice": price,
            "expectedSellerId": seller_id
        }

        async with session.post(buy_url, json=payload, headers=headers) as resp:
            result = await resp.json()
            
            # 구매 결과 판독
            if resp.status == 200 and result.get("purchased"):
                # 성공 시 DB 처리
                conn = sqlite3.connect(DATABASE); cur = conn.cursor()
                order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (money, user_id))
                cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                            (order_id, user_id, money, price))
                conn.commit(); conn.close()
                return {"success": True, "order_id": order_id}
            else:
                error_reason = result.get("reason", result.get("errorMsg", "알 수 없는 오류"))
                return {"success": False, "message": f"구매 실패: {error_reason}"}

# -----------------------------------
# 3️⃣ 결제 확인 뷰 (View)
# -----------------------------------
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id):
        super().__init__(timeout=120)
        self.info, self.money, self.user_id = info, money, str(user_id)

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        text = f"### <:acy2:1489883409001091142> 로벅스 결제 승인\n-# - **상품**: {self.info['name']}\n-# - **가격**: {self.info['price']:,} R$\n-# - **금액**: {self.money:,}원"
        con.add_item(ui.TextDisplay(text))
        
        row = ui.ActionRow()
        btn_ok = ui.Button(label="승인", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>")
        btn_ok.callback = self.on_confirm
        btn_no = ui.Button(label="취소", style=discord.ButtonStyle.gray, emoji="<:downvote:1489930277450158080>")
        btn_no.callback = self.on_cancel
        row.add_item(btn_ok); row.add_item(btn_no)
        con.add_item(row)
        self.clear_items(); self.add_item(con)
        return self

    async def on_confirm(self, it: discord.Interaction):
        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        u_row = cur.fetchone(); conn.close()
        
        if not u_row or u_row[0] < self.money:
            return await it.response.edit_message(view=get_container_view("❌ 잔액 부족", "충전 후 이용해주세요.", 0xED4245))

        await it.response.edit_message(view=get_container_view("⌛ 결제 중", "로블록스 서버와 직접 통신 중...", 0xFEE75C))

        # 직접 우회 로직 실행 (인자 3개 정확히 전달)
        result = await direct_roblox_purchase(self.info['id'], self.user_id, self.money)
        
        if result["success"]:
            await it.edit_original_response(view=get_container_view("✅ 성공", f"주문번호: `{result['order_id']}`", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 실패", f"사유: {result['message']}", 0xED4245))

    async def on_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소됨", "결제가 취소되었습니다.", 0x99AAB5))

# -----------------------------------
# 4️⃣ 모달 (Modal)
# -----------------------------------
class GamepassModal(ui.Modal, title="게임패스 구매"):
    id_input = ui.TextInput(label="아이템 ID 또는 링크", required=True)

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)
        p_id = extract_pass_id(self.id_input.value.strip())
        if not p_id: return await it.followup.send("ID가 올바르지 않습니다.", ephemeral=True)

        # 정보 조회 (직접 API 사용)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://economy.roblox.com/v1/game-pass/{p_id}/product-info") as resp:
                if resp.status != 200:
                    return await it.followup.send("상품 정보를 가져올 수 없습니다.", ephemeral=True)
                data = await resp.json()
                info = {"id": p_id, "name": data.get("Name"), "price": data.get("PriceInRobux", 0)}

        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone(); conn.close()
        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000) if info['price'] > 0 else 0

        view_obj = GamepassConfirmView(info, money, it.user.id)
        await it.followup.send(view=await view_obj.build(), ephemeral=True)

