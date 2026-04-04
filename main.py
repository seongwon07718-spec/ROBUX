import requests
import sqlite3
import json

DATABASE = 'robux_shop.db'

def purchase_gamepass(product_id, expected_price, seller_id):
    """
    최신 로블록스 구매 API 사양에 맞춰 수정한 구매 함수입니다.
    InvalidArguments 에러 방지를 위해 페이로드 구조를 최정밀화했습니다.
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

    # 브라우저 환경과 동일하게 헤더 구성 (Content-Type 필수)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com"
    }

    try:
        # 2. CSRF 토큰 갱신
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        csrf_token = auth_res.headers.get("x-csrf-token")
        
        if not csrf_token:
            return {"success": False, "message": "CSRF 토큰 획득 실패 (쿠키 만료 가능성)"}
        
        headers["X-CSRF-TOKEN"] = csrf_token

        # 3. 구매 요청 주소 및 데이터 (v1 purchase endpoint)
        purchase_url = f"https://economy.roblox.com/v1/purchases/products/{product_id}"
        
        # [중요] InvalidArguments 방지를 위해 데이터 타입을 정확히 맞춥니다.
        payload = {
            "expectedCurrency": 1,         # 1: Robux
            "expectedPrice": int(expected_price),
            "expectedSellerId": int(seller_id) if seller_id else 1
        }

        # 데이터 전송 (json.dumps로 확실하게 직렬화)
        res = session.post(purchase_url, headers=headers, data=json.dumps(payload), timeout=10)

        if res.status_code == 200:
            data = res.json()
            
            # purchased 필드가 존재하고 True인지 확인
            if data.get("purchased") is True:
                return {"success": True, "message": "구매 성공!", "data": data}
            else:
                # 에러 이유 상세 분석
                reason = data.get("reason") or data.get("errorMsg") or "알 수 없는 오류"
                return {"success": False, "message": f"구매 실패: {reason}"}
        else:
            # 400 에러 발생 시 응답 내용 확인용
            error_data = res.json() if res.text else {}
            error_msg = error_data.get("errors", [{}])[0].get("message", res.text)
            return {"success": False, "message": f"서버 오류 ({res.status_code}): {error_msg}"}

    except Exception as e:
        return {"success": False, "message": f"시스템 오류: {str(e)}"}

eof
✅ InvalidArguments 해결 포인트
 * seller_id 추가: 구매 시 판매자 ID(expectedSellerId)가 누락되거나 잘못된 형식이면 인자 오류가 납니다. fetch_gamepass_details에서 가져온 sellerId를 반드시 인자로 넘겨주세요.
 * 데이터 타입 강제: expectedPrice와 expectedSellerId를 int()로 감싸서 문자열이 섞여 들어가지 않게 차단했습니다.
 * json.dumps 사용: json=payload 대신 data=json.dumps(payload)를 사용하여 데이터 전송 포맷을 더 엄격하게 맞췄습니다.
 * 헤더 보강: Accept 헤더와 정확한 Content-Type을 추가하여 서버가 요청을 명확히 이해하도록 했습니다.
🛠️ 호출 예시 (알렉스님 코드에 적용할 때)
이전에 만든 info 딕셔너리에 담긴 값들을 그대로 사용하세요.
# info = fetch_gamepass_details(pass_id) 결과값 활용
result = purchase_gamepass(
    product_id=info['productId'], 
    expected_price=info['price'], 
    seller_id=info['sellerId']
)

