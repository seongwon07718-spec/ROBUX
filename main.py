import discord
from discord import ui
import sqlite3
import requests
import re
import json

DATABASE = 'robux_shop.db'

# --- [유지] 알렉스님의 정밀 ID 추출 함수 ---
def extract_pass_id(input_str):
    link_match = re.search(r'game-pass/(\d+)', input_str)
    if link_match: return link_match.group(1)
    catalog_match = re.search(r'catalog/(\d+)', input_str)
    if catalog_match: return catalog_match.group(1)
    nums = re.findall(r'\d+', input_str)
    if nums: return max(nums, key=len)
    return None

# --- [수정] 가격 0원 및 404 방지 함수 ---
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
        # 1차: Economy API 시도
        url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = session.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            # 가격 필드 대소문자 정밀 체크
            price = data.get("PriceInRobux")
            if price is None: price = data.get("price")
            if price is None: price = 0
            
            return {
                "id": pass_id,
                "name": data.get("Name") or data.get("name") or "Unknown",
                "price": int(price),
                "sellerId": data.get("Creator", {}).get("Id") or data.get("creatorId"),
                "productId": data.get("ProductId")
            }
            
        # 2차: 웹 페이지 JSON 파싱 (API 404 발생 시)
        web_url = f"https://www.roblox.com/game-pass/{pass_id}"
        web_res = session.get(web_url, headers=headers, timeout=5)
        if web_res.status_code == 200:
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', web_res.text)
            if match:
                web_data = json.loads(match.group(1))
                props = web_data.get("props", {}).get("pageProps", {})
                info = props.get("gamePassInfo") or props.get("gamePass") or {}
                
                price = info.get("price") or info.get("PriceInRobux") or 0
                return {
                    "id": pass_id,
                    "name": info.get("name") or "Unknown",
                    "price": int(price),
                    "sellerId": info.get("creatorId"),
                    "productId": info.get("productId")
                }
    except Exception as e:
        print(f"API Response Log Error: {e}")
    
    return None

# --- [수정] 모달 클래스 (디스코드 응답 오류 해결) ---
class GamepassModal(ui.Modal, title="게임패스 방식"):
    id_input = ui.TextInput(label="게임패스 ID 또는 링크", placeholder="아이디나 링크를 입력하세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        # 1. 타임아웃 방지 (생각 중... 상태 돌입)
        await it.response.defer(ephemeral=True)
        
        raw_val = self.id_input.value.strip()
        pass_id = extract_pass_id(raw_val)
        
        if not pass_id:
            return await it.followup.send(content="❌ 올바른 ID나 링크를 입력해주세요.", ephemeral=True)

        # 2. 정보 가져오기 (일반 함수이므로 await 없음)
        info = fetch_gamepass_details(pass_id)
        
        if not info or info.get('price') is None:
            return await it.followup.send(content=f"❌ ID `{pass_id}` 정보를 불러올 수 없습니다.", ephemeral=True)

        # 3. 비율 로드 및 가격 계산
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        rate = int(r_row[0]) if r_row else 1000
        # 가격이 0원이면 에러 방지
        money = int((info['price'] / rate) * 10000) if info['price'] > 0 else 0

        # 4. 결과 전송 (defer()를 썼으므로 it.followup.send 사용!)
        # 여기서는 GamepassConfirmView 같은 커스텀 뷰를 보낸다고 가정합니다.
        # await it.followup.send(view=await GamepassConfirmView(info, money, it.user.id).build(), ephemeral=True)
        
        # 테스트용 메시지 출력
        await it.followup.send(content=f"✅ 확인됨: {info['name']}\n💰 가격: {info['price']} Robux\n💳 금액: {money}원", ephemeral=True)

