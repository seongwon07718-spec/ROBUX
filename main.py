import discord
from discord import ui
import sqlite3
import requests
import asyncio
import random
import string
import re

DATABASE = 'robux_shop.db'

# --- 모든 응답을 컨테이너 뷰로 감싸는 표준 함수 ---
def get_container_view(title, description, color=0x5865F2):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"### {title}\n{description}"))
    view = ui.LayoutView()
    view.add_item(con)
    return view

# --- [유지] 3중 체크 및 정밀 상세 조회 ---
def fetch_gamepass_details(pass_id, admin_cookie=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    cookies = {".ROBLOSECURITY": admin_cookie} if admin_cookie else {}
    try:
        url1 = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res1 = requests.get(url1, headers=headers, cookies=cookies, timeout=5)
        if res1.status_code == 200:
            data = res1.json()
            return {
                "id": pass_id, "name": data.get("Name"), "price": data.get("PriceInRobux") or 0,
                "sellerId": data.get("Creator", {}).get("Id"), "productId": data.get("ProductId"), "isForSale": data.get("IsForSale")
            }
    except: pass
    try:
        url2 = f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
        res2 = requests.get(url2, headers=headers, cookies=cookies, timeout=5)
        if res2.status_code == 200:
            data = res2.json()
            return {
                "id": pass_id, "name": data.get("name"), "price": data.get("price") or 0,
                "sellerId": data.get("creatorId"), "productId": data.get("productId"), "isForSale": True
            }
    except: pass
    return None

# --- [유지] 링크에서 게임패스 ID만 정밀 추출하는 함수 ---
def extract_pass_id(input_str):
    link_match = re.search(r'game-pass/(\d+)', input_str)
    if link_match: return link_match.group(1)
    catalog_match = re.search(r'catalog/(\d+)', input_str)
    if catalog_match: return catalog_match.group(1)
    nums = re.findall(r'\d+', input_str)
    if nums: return max(nums, key=len)
    return None

# --- 구매 실행 로직 (CSRF 토큰 처리 포함) ---
def execute_purchase(cookie, info):
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    try:
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        token = auth_res.headers.get("x-csrf-token")
        if not token: return False, "토큰 획득 실패"
        headers["X-CSRF-TOKEN"] = token
        buy_url = f"https://economy.roblox.com/v1/purchases/products/{info['productId']}"
        payload = {"expectedCurrency": 1, "expectedPrice": info['price'], "expectedSellerId": info['sellerId']}
        buy_res = session.post(buy_url, headers=headers, json=payload, timeout=10)
        if buy_res.status_code == 200:
            res_json = buy_res.json()
            if res_json.get("purchased"): return True, "성공"
            return False, res_json.get("reason", "구매 거절됨")
        return False, f"HTTP {buy_res.status_code}"
    except Exception as e: return False, str(e)

# --- [수정] 구매 확인 및 버튼 콜백 완성 ---
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id, cookie):
        super().__init__(timeout=120)
        self.info, self.money, self.user_id, self.cookie = info, money, str(user_id), cookie

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        # 가격 및 정보 시각화 강화
        price_info = (
            f"**📦 상품**: `{self.info['name']}`\n"
            f"**💎 가격**: `{self.info['price']:,} Robux`\n"
            f"**💳 결제금액**: `{self.money:,}원`"
        )
        con.add_item(ui.TextDisplay(f"### 🛒 구매 확인\n{price_info}"))
        
        row = ui.ActionRow()
        # 확정 버튼
        btn_confirm = ui.Button(label="구매 확정", style=discord.ButtonStyle.success, emoji="✅")
        btn_confirm.callback = self.self_confirm
        # 거부(취소) 버튼
        btn_cancel = ui.Button(label="구매 거부", style=discord.ButtonStyle.danger, emoji="✖️")
        btn_cancel.callback = self.self_cancel
        
        row.add_item(btn_confirm)
        row.add_item(btn_cancel)
        con.add_item(row)
        self.clear_items()
        self.add_item(con)
        return self

    async def self_confirm(self, it: discord.Interaction):
        # 잔액 체크
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        row = cur.fetchone()
        
        if not row or row[0] < self.money:
            conn.close()
            return await it.response.edit_message(view=get_container_view("❌ 잔액 부족", "충전 후 다시 시도해 주세요.", 0xED4245))

        # 진행 중 표시
        await it.response.edit_message(view=get_container_view("⌛ 처리 중", "로블록스 서버와 통신 중입니다...", 0xFEE75C))

        # 실제 구매 로직 실행
        success, msg = execute_purchase(self.cookie, self.info)
        
        if success:
            order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=get_container_view("✅ 구매 성공", f"주문번호: `{order_id}`\n지급이 완료되었습니다.", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 구매 실패", f"사유: `{msg}`", 0xED4245))
        conn.close()

    async def self_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소됨", "구매 요청을 거부했습니다.", 0x99AAB5))

# --- [유지] 모달 클래스 ---
class GamepassModal(ui.Modal, title="로블록스 게임패스 구매"):
    id_input = ui.TextInput(label="게임패스 ID 또는 링크", placeholder="여기에 붙여넣으세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        raw_val = self.id_input.value.strip()
        pass_id = extract_pass_id(raw_val)
        
        if not pass_id:
            return await it.response.send_message(view=get_container_view("❌ 인식 오류", "올바른 ID나 링크를 입력해주세요.", 0xED4245), ephemeral=True)

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        admin_cookie = c_row[0] if c_row else None
        info = fetch_gamepass_details(pass_id, admin_cookie)
        
        if not info:
            return await it.response.send_message(view=get_container_view("❌ 찾을 수 없음", f"ID `{pass_id}` 정보를 불러올 수 없습니다.", 0xED4245), ephemeral=True)

        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000)

        view_obj = GamepassConfirmView(info, money, it.user.id, admin_cookie)
        await it.response.send_message(view=await view_obj.build(), ephemeral=True)
