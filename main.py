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

# --- [수정] 100% 인식을 위한 정보 조회 함수 ---
def fetch_gamepass_details(pass_id, admin_cookie=None):
    try:
        # 로블록스 서버를 속이기 위한 정밀 헤더
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://www.roblox.com/"
        }
        
        # 관리자 쿠키가 있다면 조회 시에도 사용 (권한 에러 방지)
        cookies = {}
        if admin_cookie:
            cookies[".ROBLOSECURITY"] = admin_cookie

        url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = requests.get(url, headers=headers, cookies=cookies, timeout=7)
        
        if res.status_code == 200:
            data = res.json()
            # 필수 데이터 존재 여부 확인
            if "ProductId" in data:
                return {
                    "id": pass_id,
                    "name": data.get("Name", "이름 없음"),
                    "price": data.get("PriceInRobux") or 0,
                    "sellerId": data.get("Creator", {}).get("Id"),
                    "productId": data.get("ProductId"),
                    "isForSale": data.get("IsForSale", False)
                }
        print(f"API Response Log: {res.status_code} - {res.text}") # 디버깅용 로그
    except Exception as e:
        print(f"Fetch Error: {e}")
    return None

# --- 구매 실행 함수 (기존 로직 유지) ---
def execute_purchase(cookie, info):
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json"
    }
    try:
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        token = auth_res.headers.get("x-csrf-token")
        if not token: return False, "토큰 확보 실패"
        headers["X-CSRF-TOKEN"] = token

        buy_url = f"https://economy.roblox.com/v1/purchases/products/{info['productId']}"
        payload = {
            "expectedCurrency": 1, 
            "expectedPrice": info['price'], 
            "expectedSellerId": info['sellerId']
        }
        buy_res = session.post(buy_url, headers=headers, json=payload, timeout=10)
        
        if buy_res.status_code == 200:
            res_json = buy_res.json()
            if res_json.get("purchased"): return True, "성공"
            return False, res_json.get("reason", "거절됨")
        return False, f"HTTP {buy_res.status_code}"
    except Exception as e:
        return False, str(e)

# --- 모달 및 뷰 클래스 ---
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
        desc = f"**상품**: `{self.info['name']}`\n**가격**: `{self.info['price']} R$`\n**결제**: `{self.money:,}원`"
        con.add_item(ui.TextDisplay(f"### 🛒 구매 확인\n{desc}"))
        
        row = ui.ActionRow()
        btn_ok = ui.Button(label="확정", style=discord.ButtonStyle.success)
        btn_ok.callback = self.on_confirm
        row.add_item(btn_ok)
        con.add_item(row)
        
        self.clear_items()
        self.add_item(con)
        return self

    async def on_confirm(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("⌛ 진행 중", "구매를 처리하고 있습니다.", 0xFEE75C))
        success, msg = execute_purchase(self.cookie, self.info)
        if success:
            await it.edit_original_response(view=get_container_view("✅ 성공", "지급 완료!", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 실패", f"사유: {msg}", 0xED4245))

class GamepassModal(ui.Modal, title="게임패스 구매"):
    id_input = ui.TextInput(label="ID/링크", placeholder="ID를 입력하세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        raw_val = self.id_input.value.strip()
        nums = re.findall(r'\d+', raw_val)
        if not nums:
            return await it.response.send_message(view=get_container_view("❌ 에러", "ID를 찾을 수 없습니다.", 0xED4245), ephemeral=True)
        
        pass_id = max(nums, key=len)

        # DB에서 쿠키 먼저 가져오기 (조회 시 사용하기 위함)
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        admin_cookie = c_row[0] if c_row else None
        
        # [수정 포인트] 쿠키를 함께 넘겨서 조회 성공률 극대화
        info = fetch_gamepass_details(pass_id, admin_cookie)
        
        if not info:
            return await it.response.send_message(view=get_container_view("❌ 인식 불가", "로블록스 API가 응답하지 않거나 ID가 잘못되었습니다.", 0xED4245), ephemeral=True)

        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000)

        view_obj = GamepassConfirmView(info, money, it.user.id, admin_cookie)
        await it.response.send_message(view=await view_obj.build(), ephemeral=True)
