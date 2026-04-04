import requests
import re
import json
import sqlite3

DATABASE = 'robux_shop.db'

# -----------------------------------
# 1️⃣ GamePass 상세 가져오기 (DB 쿠키 + 3단 우회)
# -----------------------------------
def fetch_gamepass_details(pass_id):
    # DB에서 쿠키 가져오기
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

    # --- 1차: 공식 Economy API (가장 권장) ---
    try:
        api_url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = session.get(api_url, headers=headers, timeout=5)

        if res.status_code == 200:
            data = res.json()
            # [수정] 필드명 대소문자 정확히 매칭 (PriceInRobux)
            price = data.get("PriceInRobux")
            if price is None: price = data.get("price", 0)
            
            return {
                "id": pass_id,
                "name": data.get("Name") or data.get("name"),
                "price": int(price),
                "sellerId": data.get("Creator", {}).get("Id") or data.get("creatorId"),
                "productId": data.get("ProductId"),
                "source": "API"
            }
    except: pass

    # --- 2차: 웹 페이지 JSON 데이터 (__NEXT_DATA__) ---
    try:
        url = f"https://www.roblox.com/game-pass/{pass_id}"
        res = session.get(url, headers=headers, timeout=10)

        if res.status_code == 200:
            # HTML 내부의 JSON 데이터 추출
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', res.text)
            if match:
                data = json.loads(match.group(1))
                # 로블록스 웹 구조에 맞춘 경로 수정
                props = data.get("props", {}).get("pageProps", {})
                gamepass = props.get("gamePassInfo") or props.get("gamePass") or {}

                price = gamepass.get("price") or gamepass.get("PriceInRobux") or 0
                return {
                    "id": pass_id,
                    "name": gamepass.get("name") or gamepass.get("Name"),
                    "price": int(price),
                    "sellerId": gamepass.get("creatorId"),
                    "productId": gamepass.get("productId"),
                    "source": "WEB_JSON"
                }
    except: pass

    # --- 3차: HTML 텍스트 강제 파싱 (최후의 수단) ---
    try:
        res = session.get(f"https://www.roblox.com/game-pass/{pass_id}", headers=headers, timeout=10)
        if res.status_code == 200:
            # [수정] 가격 텍스트 패턴 정밀화
            # <div class="text-robux-lg">100</div> 혹은 유사 패턴 찾기
            price_match = re.search(r'data-expected-price="(\d+)"', res.text)
            if not price_match:
                price_match = re.search(r'(\d[\d,]*)\s*Robux', res.text)

            price = 0
            if price_match:
                price = int(price_match.group(1).replace(",", ""))

            name_match = re.search(r'<title>(.*?)</title>', res.text)
            name = name_match.group(1).replace(" - Roblox", "") if name_match else "Unknown"

            return {
                "id": pass_id,
                "name": name,
                "price": price,
                "sellerId": None,
                "productId": None,
                "source": "HTML_PARSING"
            }
    except: pass

    return None
