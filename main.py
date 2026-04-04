import requests
import re
import json

session = requests.Session()

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# -----------------------------------
# 1️⃣ GamePass 상세 가져오기 (풀 우회)
# -----------------------------------
def fetch_gamepass_details(pass_id):
    # -------------------------------
    # 1차: 공식 API
    # -------------------------------
    try:
        api_url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = session.get(api_url, headers=HEADERS, timeout=5)

        if res.status_code == 200:
            data = res.json()
            return {
                "id": pass_id,
                "name": data.get("name"),
                "price": data.get("priceInRobux") or 0,
                "sellerId": data.get("creator", {}).get("id"),
                "productId": data.get("productId"),
                "source": "API"
            }
    except:
        pass

    # -------------------------------
    # 2차: 웹 페이지 (__NEXT_DATA__)
    # -------------------------------
    try:
        url = f"https://www.roblox.com/game-pass/{pass_id}"
        res = session.get(url, headers=HEADERS, allow_redirects=True, timeout=10)

        final_url = res.url

        res = session.get(final_url, headers=HEADERS, timeout=10)

        if res.status_code == 200:
            match = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                res.text
            )

            if match:
                data = json.loads(match.group(1))
                gamepass = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("gamePass")
                    or {}
                )

                return {
                    "id": pass_id,
                    "name": gamepass.get("name"),
                    "price": gamepass.get("price") or 0,
                    "sellerId": gamepass.get("creator", {}).get("id"),
                    "productId": gamepass.get("productId"),
                    "source": "WEB_JSON"
                }
    except:
        pass

    # -------------------------------
    # 3차: HTML 강제 파싱 (최후)
    # -------------------------------
    try:
        res = session.get(f"https://www.roblox.com/game-pass/{pass_id}", headers=HEADERS)

        if res.status_code == 200:
            # 가격 추출 (Robux 숫자)
            price_match = re.search(r'(\d[\d,]*)\s*Robux', res.text)
            name_match = re.search(r'<title>(.*?)</title>', res.text)

            price = 0
            if price_match:
                price = int(price_match.group(1).replace(",", ""))

            name = name_match.group(1) if name_match else "Unknown"

            return {
                "id": pass_id,
                "name": name,
                "price": price,
                "sellerId": None,
                "productId": None,
                "source": "HTML"
            }
    except:
        pass

    print(f"❌ 완전 실패: {pass_id}")
    return None


# -----------------------------------
# 2️⃣ 게임의 모든 GamePass 가져오기
# -----------------------------------
def fetch_all_gamepasses(universe_id):
    url = f"https://games.roblox.com/v1/games/{universe_id}/game-passes"

    gamepasses = []
    cursor = None

    while True:
        try:
            params = {"limit": 50}
            if cursor:
                params["cursor"] = cursor

            res = session.get(url, headers=HEADERS, params=params)

            if res.status_code != 200:
                print("❌ 목록 조회 실패")
                break

            data = res.json()

            for item in data.get("data", []):
                gamepasses.append({
                    "id": item["id"],
                    "name": item["name"]
                })

            cursor = data.get("nextPageCursor")

            if not cursor:
                break

        except Exception as e:
            print("🚨 에러:", e)
            break

    return gamepasses


# -----------------------------------
# 3️⃣ 전체 크롤링 실행
# -----------------------------------
def crawl_gamepasses(universe_id):
    passes = fetch_all_gamepasses(universe_id)

    results = []

    for p in passes:
        detail = fetch_gamepass_details(p["id"])
        if detail:
            results.append(detail)

    return results


# -----------------------------------
# 사용 예시
# -----------------------------------
if __name__ == "__main__":
    test_id = 1646011508
    print(fetch_gamepass_details(test_id))

    # universe_id 넣으면 전체 가져옴
    # print(crawl_gamepasses(123456789))
