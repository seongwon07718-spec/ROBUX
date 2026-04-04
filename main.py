import requests
import json

def get_roblox_data(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    
    # 1. 쿠키 전처리 (앞뒤 공백 제거)
    auth_cookie = cookie.strip().strip('"').strip("'")
    
    # 세션 객체 생성
    session = requests.Session()
    
    # 2. 필수 헤더 설정 (Referer와 Origin에 www를 꼭 붙여야 함)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Cookie": f".ROBLOSECURITY={auth_cookie}",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://roblox.com",
        "Origin": "https://www.roblox.com",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        # 3. CSRF 토큰 획득 (반드시 auth.roblox.com 사용)
        # 이 요청은 403 Forbidden이 뜨는 게 정상이며, 헤더에서 토큰을 추출합니다.
        token_url = "https://roblox.com"
        token_res = session.post(token_url, headers=headers, timeout=10)
        
        x_token = token_res.headers.get("x-csrf-token")
        
        if not x_token:
            # 토큰이 안 나오면 쿠키가 만료되었거나 IP가 차단된 상태입니다.
            if "text/html" in token_res.headers.get("Content-Type", ""):
                return 0, "보안 차단됨 (브라우저에서 쿠키 재추출 필요)"
            return 0, f"토큰 획득 실패 (상태: {token_res.status_code})"

        # 4. 획득한 토큰을 헤더에 삽입
        headers["X-CSRF-TOKEN"] = x_token

        # 5. 로벅스 정보 조회 (반드시 economy.roblox.com 사용)
        economy_url = "https://roblox.com"
        final_res = session.get(economy_url, headers=headers, timeout=10)

        # 6. 결과 반환
        if final_res.status_code == 200:
            try:
                data = final_res.json()
                robux = data.get('robux', 0)
                return robux, "정상"
            except (json.JSONDecodeError, AttributeError):
                return 0, "데이터 분석 실패"
        
        elif final_res.status_code == 401:
            return 0, "쿠키 만료 또는 무효"
        else:
            return 0, f"서버 응답 에러 ({final_res.status_code})"

    except Exception as e:
        return 0, f"오류 발생: {str(e)[:15]}"

# --- VS Code 실행 테스트 ---
# if __name__ == "__main__":
#     test_cookie = "여기에_|WARNING:로 시작하는 쿠키 입력"
#     print(get_roblox_data(test_cookie))
