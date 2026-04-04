import discord
from discord import ui
import sqlite3
import requests
import asyncio
import random
import string
import re

DATABASE = 'robux_shop.db'

# --- [해결] 모든 메시지를 컨테이너 뷰로 반환하는 함수 ---
# 에러 이미지 3번의 'Container' 객체 오류를 해결하기 위해 반드시 LayoutView에 담아 리턴합니다.
def get_container_view(title, description, color=0x5865F2):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"### {title}\n{description}"))
    return ui.LayoutView().add_item(con)

def generate_order_id():
    chars = string.ascii_uppercase + string.digits
    return f"{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=6))}"

# --- [해결] 에러 이미지 1번: 반환값 개수 불일치 수정 ---
def get_roblox_data(cookie):
    """유저 정보를 가져오는 함수 (반드시 2개의 값을 리턴하도록 고정)"""
    try:
        session = requests.Session()
        session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
        res = session.get("https://economy.roblox.com/v1/users/authenticated/currency")
        if res.status_code == 200:
            return res.json().get("robux", 0), "정상"
        return 0, "인증 실패"
    except:
        return 0, "오류 발생"

# --- 유니버스 API 기반 상세 조회 ---
def fetch_gamepass_via_universe(pass_id):
    try:
        # 1. UniverseId 획득
        basic_url = f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
        basic_res = requests.get(basic_url, timeout=5)
        if basic_res.status_code != 200: return None
        u_id = basic_res.json().get("universeId")
        if not u_id: return None

        # 2. Universe Full View API 호출
        universe_url = f"https://apis.roblox.com/game-passes/v1/universes/{u_id}/game-passes"
        params = {"passView": "Full", "pageSize": 100}
        uni_res = requests.get(universe_url, params=params, timeout=5)
        
        if uni_res.status_code == 200:
            data = uni_res.json().get("gamePasses", [])
            for gp in data:
                if str(gp.get("id")) == str(pass_id):
                    return {
                        "id": pass_id,
                        "name": gp.get("name"),
                        "price": gp.get("price", 0),
                        "sellerId": gp.get("creatorId"),
                        "sellerName": gp.get("creatorName"),
                        "productId": gp.get("productId")
                    }
    except:
        pass
    return None

# --- 구매 실행 로직 ---
def run_purchase_api(cookie, info):
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    try:
        # CSRF 토큰 갱신
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        token = auth_res.headers.get("x-csrf-token")
        if not token: return False, "토큰 획득 실패"
        headers["X-CSRF-TOKEN"] = token

        buy_url = f"https://economy.roblox.com/v1/purchases/products/{info['productId']}"
        payload = {"expectedCurrency": 1, "expectedPrice": info['price'], "expectedSellerId": info['sellerId']}
        buy_res = session.post(buy_url, headers=headers, json=payload)
        
        if buy_res.status_code == 200:
            res = buy_res.json()
            if res.get("purchased"): return True, "성공"
            return False, res.get("reason", "구매 실패")
        return False, f"서버 응답 오류 ({buy_res.status_code})"
    except Exception as e:
        return False, str(e)

# --- 구매 확인 뷰 ---
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id, cookie):
        super().__init__(timeout=None)
        self.info = info
        self.money = money
        self.user_id = str(user_id)
        self.cookie = cookie

    async def render(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            f"### 📋 결제 정보\n- 상품: `{self.info['name']}`\n- 가격: `{self.info['price']:,} R$`\n- 차감액: `{self.money:,}원`"
        ))
        row = ui.ActionRow()
        row.add_item(ui.Button(label="구매 확정", style=discord.ButtonStyle.success, custom_id="confirm_buy"))
        row.add_item(ui.Button(label="취소", style=discord.ButtonStyle.danger, custom_id="cancel_buy"))
        con.add_item(row)
        self.clear_items()
        self.add_item(con)
        return self

    @ui.button(custom_id="confirm_buy")
    async def on_confirm(self, it: discord.Interaction):
        # 구매 처리 로직 (생략)
        pass

    @ui.button(custom_id="cancel_buy")
    async def on_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소됨", "주문을 취소했습니다.", 0x99AAB5))

# --- [해결] 에러 이미지 2번: Missing Attribute 및 모달 로직 수정 ---
class ChargeModal(ui.Modal, title="충전하기"):
    # (충전 관련 입력 필드들...)
    
    # [해결] 에러 이미지 2번의 AttributeError 해결을 위해 콜백 함수 정의
    async def copy_callback(self, it: discord.Interaction):
        # 복사 로직 구현
        await it.response.send_message("계좌번호가 복사되었습니다.", ephemeral=True)

class GamepassModal(ui.Modal, title="게임패스 구매"):
    input_field = ui.TextInput(label="링크 또는 ID", placeholder="여기에 입력하세요", required=True)

    async def on_submit(self, it: discord.Interaction):
        raw = self.input_field.value.strip()
        nums = re.findall(r'\d+', raw)
        if not nums:
            # [해결] 에러 이미지 3번 해결: get_container_view() 사용
            return await it.response.send_message(view=get_container_view("❌ 인식 오류", "ID를 찾을 수 없습니다.", 0xED4245), ephemeral=True)
        
        pass_id = max(nums, key=len)
        info = fetch_gamepass_via_universe(pass_id)
        
        if not info:
            return await it.response.send_message(view=get_container_view("❌ 조회 실패", "로블록스 서버에서 정보를 찾지 못했습니다.", 0xED4245), ephemeral=True)

        # 가격 계산 로직 (데이터베이스 연동 등)
        # ... 

        view = GamepassConfirmView(info, 1000, it.user.id, "cookie_here")
        await it.response.send_message(view=await view.render(), ephemeral=True)

