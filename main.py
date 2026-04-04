import requests
import sqlite3
import json

DATABASE = 'robux_shop.db'

def purchase_gamepass(product_id, expected_price):
    """
    DB의 쿠키를 사용하여 특정 상품(productId)을 구매합니다.
    """
    # 1. DB에서 관리자 쿠키 로드
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        return {"success": False, "message": "관리자 쿠키가 설정되지 않았습니다."}

    admin_cookie = row[0]
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", admin_cookie, domain=".roblox.com")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json; charset=utf-8",
        "Origin": "https://www.roblox.com",
        "Referer": "https://www.roblox.com/"
    }

    try:
        # 2. [필수] CSRF 토큰 획득
        # 로블록스는 보안을 위해 POST 요청 시 무조건 이 토큰이 필요합니다.
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        csrf_token = auth_res.headers.get("x-csrf-token")
        
        if not csrf_token:
            return {"success": False, "message": "보안 토큰(CSRF)을 가져오지 못했습니다. 쿠키를 확인하세요."}
        
        headers["X-CSRF-TOKEN"] = csrf_token

        # 3. 구매 요청 보내기
        # 주의: 게임패스 ID가 아니라 'productId'를 사용해야 합니다. (fetch_gamepass_details에서 가져온 값)
        purchase_url = f"https://economy.roblox.com/v1/purchases/products/{product_id}"
        
        # 유저가 올린 가격과 실제 가격이 맞는지 서버에서 검증하기 위해 expectedPrice를 보냅니다.
        payload = {
            "expectedCurrency": 1,        # 1은 로벅스(Robux)를 의미
            "expectedPrice": expected_price,
            "expectedSellerId": 1         # 임의의 값(보통 시스템이 알아서 처리함)
        }

        res = session.post(purchase_url, headers=headers, json=payload, timeout=10)

        if res.status_code == 200:
            data = res.json()
            
            # 구매 성공 여부 판단 (purchased 필드가 True여야 함)
            if data.get("purchased"):
                return {"success": True, "message": "구매 성공!", "data": data}
            else:
                # 잔액 부족이나 이미 소유한 경우 등
                reason = data.get("reason", "알 수 없는 이유")
                return {"success": False, "message": f"구매 실패: {reason}"}
        else:
            return {"success": False, "message": f"서버 응답 에러: {res.status_code}"}

    except Exception as e:
        return {"success": False, "message": f"시스템 오류: {str(e)}"}

# --- [확정 버튼 클릭 시 적용 예시] ---
# async def on_confirm_button_click(it: discord.Interaction):
#     # info는 이전에 조회했던 데이터 { "productId": ..., "price": ... }
#     result = purchase_gamepass(info['productId'], info['price'])
#     if result['success']:
#         await it.followup.send(content="✅ 구매가 완료되었습니다!")
#     else:
#         await it.followup.send(content=f"❌ {result['message']}")

