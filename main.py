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

# --- [수정] 가격/이름/404 완벽 방지 함수 ---
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
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/"
    }

    try:
        # 1차: Economy API (가장 정확)
        url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = session.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            # 이름과 가격 필드를 대소문자 구분 없이 꼼꼼하게 체크
            name = data.get("Name") or data.get("name") or "이름 없음"
            price = data.get("PriceInRobux")
            if price is None: price = data.get("price", 0)
            
            return {
                "id": pass_id,
                "name": str(name).strip(), # 공백 제거 및 문자열화
                "price": int(price),
                "sellerId": data.get("Creator", {}).get("Id") or data.get("creatorId"),
                "productId": data.get("ProductId")
            }
            
        # 2차: 웹 페이지 JSON (API 실패 시 대비)
        web_url = f"https://www.roblox.com/game-pass/{pass_id}"
        web_res = session.get(web_url, headers=headers, timeout=5)
        if web_res.status_code == 200:
            # 인코딩 강제 설정 (이름 깨짐 방지)
            web_res.encoding = 'utf-8'
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', web_res.text)
            if match:
                web_data = json.loads(match.group(1))
                props = web_data.get("props", {}).get("pageProps", {})
                info = props.get("gamePassInfo") or props.get("gamePass") or {}
                
                name = info.get("name") or info.get("Name") or "이름 없음"
                price = info.get("price") or info.get("PriceInRobux") or 0
                return {
                    "id": pass_id,
                    "name": str(name).strip(),
                    "price": int(price),
                    "sellerId": info.get("creatorId"),
                    "productId": info.get("productId")
                }
    except Exception as e:
        print(f"조회 에러: {e}")
    
    return None

# --- [수정] 모달 클래스 (디스코드 에러 해결) ---
class GamepassModal(ui.Modal, title="게임패스 구매"):
    id_input = ui.TextInput(label="게임패스 ID 또는 링크", placeholder="아이디나 링크를 입력하세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        # 1. 타임아웃 방지 및 응답 예약 (매우 중요)
        await it.response.defer(ephemeral=True)
        
        raw_val = self.id_input.value.strip()
        pass_id = extract_pass_id(raw_val)
        
        if not pass_id:
            return await it.followup.send(content="❌ 올바른 ID나 링크를 입력해주세요.", ephemeral=True)

        # 2. 정보 로드 (일반 함수이므로 await 없음)
        info = fetch_gamepass_details(pass_id)
        
        if not info:
            return await it.followup.send(content=f"❌ ID `{pass_id}` 정보를 불러올 수 없습니다. 쿠키를 확인해주세요.", ephemeral=True)

        # 3. 비율 로드 및 가격 계산
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        rate = int(r_row[0]) if r_row else 1000
        # 가격 0원일 때 나누기 오류 방지
        money = int((info['price'] / rate) * 10000) if info['price'] > 0 else 0

        # 4. 결과 전송 (defer를 썼으므로 무조건 followup.send 사용)
        # 만약 GamepassConfirmView 같은 커스텀 뷰를 쓴다면 아래처럼 하세요:
        # view_obj = GamepassConfirmView(info, money, it.user.id)
        # await it.followup.send(view=await view_obj.build(), ephemeral=True)
        
        await it.followup.send(content=f"✅ **상품 확인 완료**\n이름: `{info['name']}`\n가격: `{info['price']} Robux`\n금액: `{money}원`", ephemeral=True)

