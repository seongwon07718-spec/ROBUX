import discord
from discord import ui
import sqlite3
import requests
import asyncio
import random
import string
import re

DATABASE = 'robux_shop.db'

# --- 모든 메시지를 컨테이너 뷰로 감싸는 함수 (기존 에러 해결용) ---
def get_container_view(title, description, color=0x5865F2):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"### {title}\n{description}"))
    return ui.LayoutView().add_item(con)

def generate_order_id():
    chars = string.ascii_uppercase + string.digits
    return f"{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=6))}"

# --- 유니버스 API 기반 상세 조회 (비공개/이름 없음 대응) ---
async def fetch_gamepass_via_universe(pass_id):
    """API 호출을 비동기적으로 처리하기 위해 run_in_executor를 사용하거나 일반 함수로 감쌉니다."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_logic, pass_id)

def _fetch_logic(pass_id):
    try:
        # 1. UniverseId 획득
        basic_url = f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
        res = requests.get(basic_url, timeout=5)
        if res.status_code != 200: return None
        u_id = res.json().get("universeId")
        if not u_id: return None

        # 2. Universe Full View API 호출 (요청하신 방식)
        uni_url = f"https://apis.roblox.com/game-passes/v1/universes/{u_id}/game-passes"
        params = {"passView": "Full", "pageSize": 100}
        uni_res = requests.get(uni_url, params=params, timeout=5)
        
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

# --- 구매 확인 뷰 ---
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id, cookie):
        super().__init__(timeout=None)
        self.info = info
        self.money = money
        self.user_id = str(user_id)
        self.cookie = cookie

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            f"### 🛒 주문 확인\n- 상품: `{self.info['name']}`\n- 로벅스: `{self.info['price']:,} R$`\n- 지불액: `{self.money:,}원`"
        ))
        row = ui.ActionRow()
        # 실제 버튼 콜백은 생략 (기존 로직 유지)
        row.add_item(ui.Button(label="구매 확정", style=discord.ButtonStyle.success, emoji="✅"))
        row.add_item(ui.Button(label="취소", style=discord.ButtonStyle.danger, emoji="✖️"))
        con.add_item(row)
        self.clear_items()
        self.add_item(con)
        return self

# --- [수정 핵심] 속성 에러 및 타임아웃 해결 모달 ---
class GamepassModal(ui.Modal, title="게임패스 구매"):
    # 1. 속성 에러 해결: 변수명을 input_field로 통일
    input_field = ui.TextInput(
        label="게임패스 링크 또는 ID",
        placeholder="여기에 입력하세요",
        required=True
    )

    async def on_submit(self, it: discord.Interaction):
        # 2. 타임아웃 해결: 디스코드 응답 대기 시간을 늘립니다.
        await it.response.defer(ephemeral=True)
        
        # self.input_field로 정확히 접근
        raw = self.input_field.value.strip()
        nums = re.findall(r'\d+', raw)
        if not nums:
            return await it.followup.send(view=get_container_view("❌ 인식 오류", "ID를 찾을 수 없습니다.", 0xED4245), ephemeral=True)
        
        pass_id = max(nums, key=len)

        # 3. API 호출 (오래 걸릴 수 있음)
        info = await fetch_gamepass_via_universe(pass_id)
        
        if not info:
            return await it.followup.send(view=get_container_view("❌ 조회 실패", "로블록스 정보를 가져오지 못했습니다.", 0xED4245), ephemeral=True)

        # 데이터베이스 및 가격 계산 (생략)
        # 예시 가격 1000원
        confirm_view = GamepassConfirmView(info, 1000, it.user.id, "관리자_쿠키_변수")
        await it.followup.send(view=await confirm_view.build(), ephemeral=True)

