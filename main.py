import requests
import re
import json

def fetch_gamepass_details(pass_id):
    url = f"https://www.roblox.com/game-pass/{pass_id}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            print(f"❌ 페이지 로드 실패: {res.status_code}")
            return None

        # 🔥 __NEXT_DATA__ JSON 추출
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', res.text)

        if not match:
            print("❌ JSON 데이터 못 찾음")
            return None

        data = json.loads(match.group(1))

        # 🔥 깊은 구조에서 가격 찾기
        props = data.get("props", {})
        pageProps = props.get("pageProps", {})

        gamepass = pageProps.get("gamePass", {}) or pageProps.get("gamepass", {})

        price = (
            gamepass.get("price") or
            gamepass.get("priceInRobux") or
            0
        )

        name = gamepass.get("name", "상품명 없음")

        print(f"DEBUG: {name} / 가격: {price}")

        return {
            "id": pass_id,
            "name": name,
            "price": int(price),
            "sellerId": gamepass.get("creator", {}).get("id"),
            "productId": gamepass.get("productId")
        }

    except Exception as e:
        print("🚨 에러:", e)
        return None
