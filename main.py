import requests

def get_roblox_balance(cookie):
    # 1. 세션 생성 및 초기 설정
    session = requests.Session()
    
    # 쿠키에서 불필요한 따옴표나 공백 완벽 제거
    clean_cookie = cookie.strip().strip('"').strip("'")
    
    # 세션에 쿠키 탑재 (공식 방식)
    session.cookies.set(".ROBLOSECURITY", clean_cookie, domain=".roblox.com")
    
    # RoProxy를 사용해 보안 차단 우회 (도메인만 변경)
    BASE_URL = "roproxy.com"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        # 2. X-CSRF-TOKEN 획득 (공식 가이드 Step 2)
        # 로그아웃 API에 빈 POST를 날려 403 에러와 함께 토큰을 낚아챕니다.
        auth_url = f"https://auth.{BASE_URL}/v2/logout"
        auth_res = session.post(auth_url, headers=headers)
        
        # 헤더에서 토큰 추출
        csrf_token = auth_res.headers.get("x-csrf-token")
        
        if not csrf_token:
            # 토큰이 안 오면 쿠키가 이미 유효하지 않은 상태일 확률이 매우 높음
            return 0, "CSRF 토큰 획득 실패 (쿠키 유효성 확인 필요)"

        # 세션 헤더에 토큰 고정 (이후 모든 요청에 자동 포함)
        session.headers.update({"X-CSRF-TOKEN": csrf_token})
        
        # 3. 인증된 사용자 정보 확인 (공식 가이드 예시)
        # 먼저 로그인이 잘 되었는지(내 계정 정보가 뜨는지) 확인
        user_url = f"https://users.{BASE_URL}/v1/users/authenticated"
        user_res = session.get(user_url, headers=headers)
        
        if user_res.status_code != 200:
            return 0, f"인증 실패 (상태 코드: {user_res.status_code})"

        # 4. 최종 로벅스 잔액 가져오기
        economy_url = f"https://economy.{BASE_URL}/v1/users/authenticated/currency"
        response = session.get(economy_url, headers=headers)
        
        if response.status_code == 200:
            return response.json().get("robux", 0), "성공"
        else:
            return 0, f"잔액 조회 실패 ({response.status_code})"

    except Exception as e:
        return 0, f"오류 발생: {str(e)}"

# 사용법
# my_cookie = "여기에 쿠키 전체 복사"
# robux, status = get_roblox_balance(my_cookie)
# print(f"결과: {robux} 로벅스 / 상태: {status}")
