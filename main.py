import discord
from discord import ui
import sqlite3
import requests
import asyncio
import random
import string
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

# --- [수정] 404 방지 및 가격 정밀 파싱 함수 (일반 함수로 유지) ---
def fetch_gamepass_details(pass_id):
    # DB에서 쿠키 로드
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    row = cur.fetchone()
    conn.close()
    
    admin_cookie = row[0] if row else None
    
    session = requests.Session()
    if admin_cookie:
        session.cookies.set(".ROBLOSECURITY", admin_cookie, domain=".roblox.com")

    # 브라우저처럼 보이기 위한 필수 헤더
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/"
    }

    try:
        # 1차 시도: 공식 API
        url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = session.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            # 가격 필드 대소문자 모두 대응
            price = data.get("PriceInRobux")
            if price is None: price = data.get("price", 0)
            
            return {
                "id": pass_id,
                "name": data.get("Name") or data.get("name", "Unknown"),
                "price": int(price), # 반드시 정수로 변환
                "sellerId": data.get("Creator", {}).get("Id") or data.get("creatorId"),
                "productId": data.get("ProductId")
            }
        
        # 2차 시도: 웹 JSON 파싱 (API 404 대비)
        web_url = f"https://www.roblox.com/game-pass/{pass_id}"
        web_res = session.get(web_url, headers=headers, timeout=5)
        if web_res.status_code == 200:
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', web_res.text)
            if match:
                web_data = json.loads(match.group(1))
                info = web_data.get("props", {}).get("pageProps", {}).get("gamePassInfo") or {}
                return {
                    "id": pass_id,
                    "name": info.get("name") or "Unknown",
                    "price": int(info.get("price") or 0),
                    "sellerId": info.get("creatorId"),
                    "productId": info.get("productId")
                }
    except Exception as e:
        print(f"조회 중 오류 발생: {e}")
    
    return None

# --- [수정] 모달 클래스 (await 오류 해결) ---
class GamepassModal(ui.Modal, title="게임패스 방식"):
    id_input = ui.TextInput(label="게임패스 ID 또는 링크", placeholder="게임패스 ID 또는 링크를 적어주세요", required=True)

    async def on_submit(self, it: discord.Interaction):
        # 타임아웃 방지
        await it.response.defer(ephemeral=True)
        
        raw_val = self.id_input.value.strip()
        pass_id = extract_pass_id(raw_val)
        
        if not pass_id:
            return await it.followup.send(content="❌ 올바른 ID나 링크를 입력해주세요.", ephemeral=True)

        # [해결] fetch_gamepass_details는 일반 함수이므로 await를 붙이지 않습니다!
        info = fetch_gamepass_details(pass_id)
        
        if not info:
            return await it.followup.send(content=f"❌ ID `{pass_id}` 정보를 불러올 수 없습니다. (쿠키/ID 확인 필요)", ephemeral=True)

        # 비율 로드 및 가격 계산
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000)

        # 확인 창 띄우기 (이후 로직 생략)
        await it.followup.send(content=f"🔎 상품: {info['name']}\n💰 가격: {info['price']} Robux\n💳 결제금액: {money}원", ephemeral=True)

