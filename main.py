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

# --- [강화] 3중 체크 및 정밀 상세 조회 ---
def fetch_gamepass_details(pass_id, admin_cookie=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    cookies = {".ROBLOSECURITY": admin_cookie} if admin_cookie else {}

    # 1단계: Economy API (가장 정확함)
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

    # 2단계: Apis v1 (백업용)
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

# --- [강화] 링크에서 게임패스 ID만 정밀 추출하는 함수 ---
def extract_pass_id(input_str):
    # 1. 링크 형태일 때 (roblox.com/game-pass/123456/...)
    link_match = re.search(r'game-pass/(\d+)', input_str)
    if link_match:
        return link_match.group(1)
    
    # 2. 카탈로그 링크 형태일 때 (roblox.com/catalog/123456/...)
    catalog_match = re.search(r'catalog/(\d+)', input_str)
    if catalog_match:
        return catalog_match.group(1)

    # 3. 그냥 숫자만 있을 때
    nums = re.findall(r'\d+', input_str)
    if nums:
        # 가장 긴 숫자를 ID로 추정 (보통 게임패스 ID는 김)
        return max(nums, key=len)
    
    return None

# --- 구매 실행 및 모달 클래스 ---
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id, cookie):
        super().__init__(timeout=120)
        self.info, self.money, self.user_id, self.cookie = info, money, str(user_id), cookie

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        desc = f"**상품**: `{self.info['name']}`\n**가격**: `{self.info['price']} R$`\n**결제**: `{self.money:,}원`"
        con.add_item(ui.TextDisplay(f"### 🛒 구매 확인\n{desc}"))
        row = ui.ActionRow()
        btn = ui.Button(label="구매 확정", style=discord.ButtonStyle.success)
        btn.callback = self.self_confirm
        row.add_item(btn)
        con.add_item(row)
        self.clear_items(); self.add_item(con)
        return self

    async def self_confirm(self, it: discord.Interaction):
        # (기존 execute_purchase 로직 실행 부분... 중략)
        pass

class GamepassModal(ui.Modal, title="로블록스 게임패스 구매"):
    id_input = ui.TextInput(label="게임패스 ID 또는 링크", placeholder="여기에 붙여넣으세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        raw_val = self.id_input.value.strip()
        
        # [핵심] ID 추출 로직 호출
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
        
        # 정보 조회 (3중 체크)
        info = fetch_gamepass_details(pass_id, admin_cookie)
        
        if not info:
            # 404 로그가 남지 않도록 여기서 상세 처리
            return await it.response.send_message(view=get_container_view("❌ 찾을 수 없음", f"ID `{pass_id}`에 해당하는 게임패스 정보를 불러올 수 없습니다.\n판매 중인지 확인해주세요.", 0xED4245), ephemeral=True)

        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000)

        view_obj = GamepassConfirmView(info, money, it.user.id, admin_cookie)
        await it.response.send_message(view=await view_obj.build(), ephemeral=True)
