import requests

def get_roblox_data(cookie, proxy=None):
    if not cookie:
        return 0, "쿠키 없음"
    
    # 1. 쿠키 전처리 (경고 문구 포함 전체가 들어와야 함)
    auth_cookie = cookie.strip().strip('"').strip("'")
    if not auth_cookie.startswith("_|WARNING:"):
        return 0, "쿠키 형식 오류"

    session = requests.Session()
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    # 2. 브라우저와 최대한 동일한 헤더 구성 (이게 핵심)
    # Sec-CH-UA 등 최신 브라우저 헤더를 추가해야 403을 피할 수 있음
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Cookie": f".ROBLOSECURITY={auth_cookie}",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://roblox.com",
        "Origin": "https://roblox.com",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site"
    }

    try:
        # 3. CSRF 토큰 획득 (반드시 POST 요청)
        # 팁: logout 대신 login 엔드포인트가 로컬에서 더 잘 먹힐 때가 있음
        token_res = session.post(
            "https://roblox.com", 
            headers=headers, 
            proxies=proxies, 
            timeout=10
        )
        
        # 403 Forbidden 응답에서 x-csrf-token을 추출
        x_token = token_res.headers.get("x-csrf-token")
        
        if not x_token:
            # 토큰 자체가 안 나오면 쿠키가 이미 만료된 것 (브라우저에서 로그아웃 했는지 확인)
            status = token_res.status_code
            if status == 401: return 0, "쿠키 만료됨"
            return 0, f"토큰 획득 실패 ({status})"

        # 4. 획득한 토큰 삽입 후 정보 조회
        headers["X-CSRF-TOKEN"] = x_token
        
        economy_url = "https://roblox.com"
        final_res = session.get(
            economy_url, 
            headers=headers, 
            proxies=proxies, 
            timeout=10
        )

        if final_res.status_code == 200:
            robux = final_res.json().get('robux', 0)
            return robux, "정상"
        elif final_res.status_code == 401:
            return 0, "인증 실패 (쿠키 무효)"
        elif final_res.status_code == 403:
            return 0, "권한 없음 (IP/토큰 차단)"
        else:
            return 0, f"기타 에러 ({final_res.status_code})"

    except Exception as e:
        return 0, f"연결 실패: {str(e)[:15]}"
