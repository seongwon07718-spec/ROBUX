import requests
import json

def get_roblox_data(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    
    # 1. 쿠키 전처리 (경고 문구 포함 전체 문자열)
    auth_cookie = cookie.strip().strip('"').strip("'")
    
    session = requests.Session()
    
    # 2. 로블록스 필수 헤더 설정 (로컬 실행 시 필수)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Cookie": f".ROBLOSECURITY={auth_cookie}",
        "Referer": "https://roblox.com",
        "Origin": "https://roblox.com",
        "Accept": "application/json"
    }

    try:
        # 3. CSRF 토큰 획득 (정확한 auth 서버 주소 사용)
        # 이 요청은 403 Forbidden이 뜨는 것이 정상이며, 헤더에서 토큰만 추출합니다.
        token_url = "https://roblox.com"
        token_res = session.post(token_url, headers=headers, timeout=10)
        
        x_token = token_res.headers.get("x-csrf-token")
        
        if not x_token:
            # 토큰이 안 나오면 쿠키 자체가 죽었거나 IP가 일시적 차단된 상태
            if token_res.status_code == 401:
                return 0, "쿠키 만료됨 (다시 추출 필요)"
            return 0, f"토큰 획득 실패 ({token_res.status_code})"

        # 4. 획득한 토큰을 헤더에 추가
        headers["X-CSRF-TOKEN"] = x_token

        # 5. 로벅스 정보 조회 (정확한 economy 서버 주소 사용)
        economy_url = "https://roblox.com"
        final_res = session.get(economy_url, headers=headers, timeout=10)

        if final_res.status_code == 200:
            try:
                data = final_res.json()
                robux = data.get('robux', 0)
                return robux, "정상"
            except json.JSONDecodeError:
                return 0, "JSON 분석 오류"
        
        elif final_res.status_code == 401:
            return 0, "인증 실패 (쿠키 무효)"
        elif final_res.status_code == 403:
            return 0, "접근 거부 (IP 차단 의심)"
        else:
            return 0, f"HTTP 에러 ({final_res.status_code})"

    except requests.exceptions.RequestException as e:
        return 0, f"연결 오류: {str(e)[:15]}"

# --- 사용 예시 ---
# my_cookie = "_|WARNING:-DO-NOT-SHARE-..."
# robux_count, status_msg = get_roblox_data(my_cookie)
# print(f"결과: {robux_count}, 메시지: {status_msg}")
