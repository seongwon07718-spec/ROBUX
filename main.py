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
# 1️⃣ 정보 조회 함수 (성공했던 로직 고정)
# -----------------------------------
def fetch_gamepass_details(pass_id):
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.roblox.com/"
    }

    try:
        # 1차 시도: Economy API
        api_url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = session.get(api_url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return {
                "id": pass_id,
                "name": html.unescape(data.get("Name", "이름 없음")).strip(),
                "price": int(data.get("PriceInRobux") or data.get("price") or 0),
                "sellerId": data.get("Creator", {}).get("Id") or data.get("creatorId"),
                "productId": data.get("ProductId") or data.get("productId")
            }
    except: pass

    try:
        # 2차 시도: 웹 페이지 파싱
        url = f"https://www.roblox.com/game-pass/{pass_id}"
        res = session.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            res.encoding = 'utf-8'
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', res.text)
            if match:
                data = json.loads(match.group(1))
                props = data.get("props", {}).get("pageProps", {})
                info = props.get("gamePassInfo") or props.get("gamePass") or {}
                return {
                    "id": pass_id,
                    "name": html.unescape(info.get("name") or info.get("Name") or "이름 없음").strip(),
                    "price": int(info.get("price") or info.get("PriceInRobux") or 0),
                    "sellerId": info.get("creatorId") or info.get("CreatorId"),
                    "productId": info.get("productId") or info.get("ProductId")
                }
    except: pass

    return None

# -----------------------------------
# 2️⃣ 구매 확인 뷰 (컨테이너 UI)
# -----------------------------------
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id):
        super().__init__(timeout=120)
        self.info, self.money, self.user_id = info, money, str(user_id)

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        price_info = (
            f"-# - **상품**: {self.info['name']}\n"
            f"-# - **가격**: {self.info['price']:,} 로벅스\n"
            f"-# - **금액**: {self.money:,}원"
        )
        con.add_item(ui.TextDisplay(f"### <:acy2:1489883409001091142>  구매 확인\n{price_info}"))
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
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        user_row = cur.fetchone()
        
        if not user_row or user_row[0] < self.money:
            conn.close()
            return await it.response.edit_message(view=get_container_view("❌ 잔액 부족", "충전 후 시도해주세요.", 0xED4245))

        await it.response.edit_message(view=get_container_view("⌛ 처리 중", "구매를 진행 중입니다...", 0xFEE75C))

        # 구매 시 productId가 없으면 pass_id를 사용하도록 백업 처리
        p_id = self.info.get('productId') or self.info.get('id')
        result = purchase_gamepass(p_id, self.info['price'], self.info.get('sellerId'))
        
        if result["success"]:
            order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=get_container_view("✅ 구매 성공", f"주문번호: `{order_id}`", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 구매 실패", f"사유: `{result['message']}`", 0xED4245))
        conn.close()

    async def self_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소됨", "구매가 취소되었습니다.", 0x99AAB5))

# -----------------------------------
# 3️⃣ 메인 모달 (수정 포인트: 조건문 완화)
# -----------------------------------
class GamepassModal(ui.Modal, title="게임패스 구매"):
    id_input = ui.TextInput(label="아이디 또는 링크", placeholder="여기에 입력하세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)
        
        pass_id = extract_pass_id(self.id_input.value.strip())
        if not pass_id:
            return await it.followup.send(view=get_container_view("❌ 오류", "ID가 올바르지 않습니다.", 0xED4245), ephemeral=True)

        # 정보 가져오기
        info = fetch_gamepass_details(pass_id)
        
        # [수정] info 자체가 없거나 price가 아예 파싱이 안 된 경우에만 실패로 처리
        # productId가 없더라도 이름이나 가격이 조회되었다면 진행시킵니다.
        if not info:
            return await it.followup.send(view=get_container_view("❌ 조회 실패", f"해당 ID({pass_id})의 상품을 찾을 수 없습니다.", 0xED4245), ephemeral=True)

        # 비율 계산
        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone(); conn.close()
        rate = int(r_row[0]) if r_row else 1000
        
        # 0원 방지 및 최종 금액 계산
        gamepass_price = info.get('price', 0)
        money = int((gamepass_price / rate) * 10000) if gamepass_price > 0 else 0

        # 확인창 띄우기 (info에 데이터가 하나라도 있으면 무조건 진행)
        view_obj = GamepassConfirmView(info, money, it.user.id)
        await it.followup.send(view=await view_obj.build(), ephemeral=True)

