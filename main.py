import requests

def get_roblox_data_final(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    
    # 1. 쿠키 정리 (공백 제거 및 필수 문구 포함 확인)
    clean_cookie = cookie.strip()
    
    session = requests.Session()
    # 도메인은 .roblox.com 그대로 설정 (쿠키는 원래 도메인 기준)
    session.cookies.set(".ROBLOSECURITY", clean_cookie, domain=".roblox.com")
    
    # RoProxy는 roblox.com 대신 roproxy.com을 사용합니다.
    # 이를 통해 지역 제한(Region Lock)과 기본적인 보안 차단을 우회합니다.
    BASE_URL = "roproxy.com" 
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": f"https://www.{BASE_URL}",
        "Referer": f"https://www.{BASE_URL}/"
    }

    try:
        # [STEP 1] CSRF 토큰 획득 (가장 중요)
        # 로블록스는 보안상 빈 POST 요청을 보낼 때 헤더에 토큰을 담아 에러를 뱉습니다.
        auth_url = f"https://auth.{BASE_URL}/v2/logout"
        auth_res = session.post(auth_url, headers=headers, timeout=10)
        
        csrf_token = auth_res.headers.get("x-csrf-token")
        
        if not csrf_token:
            # 토큰이 안 오면 쿠키가 이미 만료되었거나 IP가 강하게 차단된 것
            return 0, "CSRF 토큰 획득 실패 (쿠키 만료 의심)"

        # 획득한 토큰을 헤더에 추가
        headers["X-CSRF-TOKEN"] = csrf_token
        
        # [STEP 2] 실제 로벅스 잔액 요청
        economy_url = f"https://economy.{BASE_URL}/v1/users/authenticated/currency"
        response = session.get(economy_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            robux_amount = response.json().get("robux", 0)
            return robux_amount, "정상"
        elif response.status_code == 401:
            return 0, "쿠키 만료"
        elif response.status_code == 403:
            return 0, "보안 차단 (Token/IP Issue)"
        else:
            return 0, f"에러 발생: {response.status_code}"

    except Exception as e:
        return 0, f"연결 실패: {str(e)}"

# --- 실행 예시 ---
# user_cookie = "_|WARNING:-DO-NOT-SHARE-THIS..." # 여기에 쿠키 입력
# robux, msg = get_roblox_data_final(user_cookie)
# print(f"결과: {robux} Robux / 상태: {msg}")
