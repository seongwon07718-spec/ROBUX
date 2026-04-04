import requests
import sqlite3

def fetch_gamepass_details(pass_id):
    session = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    try:
        url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = session.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            print(f"❌ 조회 실패: {res.status_code}")
            print(res.text)  # ← 디버깅 핵심
            return None

        data = res.json()

        # ✅ 올바른 필드명 사용
        raw_price = data.get("priceInRobux")
        if raw_price is None:
            raw_price = data.get("price")

        final_price = int(raw_price) if raw_price is not None else 0

        print(f"DEBUG: 가격 -> {final_price}")

        return {
            "id": pass_id,
            "name": data.get("name", "상품명 없음"),
            "price": final_price,
            "sellerId": data.get("creator", {}).get("id"),
            "productId": data.get("productId")
        }

    except Exception as e:
        print(f"🚨 에러: {e}")
        return None
