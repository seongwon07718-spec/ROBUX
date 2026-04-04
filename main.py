def get_roblox_data(cookie, proxy=None):
    if not cookie:
        return 0, "쿠키 없음"
    
    auth_cookie = cookie.strip().strip('"').strip("'")
    session = requests.Session()
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Cookie": f".ROBLOSECURITY={auth_cookie}",
        "Referer": "https://roblox.com",
        "Origin": "https://roblox.com",
        "Accept": "application/json"
    }

    try:
        # 1. CSRF 토큰 획득 시도
        # ://roblox.com 대신 직접 economy 쪽으로 찔러서 토큰 유도 (더 안정적)
        token_res = session.post("https://://roblox.com/v2/logout", headers=headers, proxies=proxies, timeout=10)
        x_token = token_res.headers.get("x-csrf-token")
        
        if not x_token:
            # 토큰이 없으면 이미 차단된 IP거나 만료된 쿠키
            return 0, f"토큰 획득 실패 (HTTP {token_res.status_code})"

        headers["X-CSRF-TOKEN"] = x_token

        # 2. 로벅스 정보 조회
        economy_url = "https://roblox.com"
        final_res = session.get(economy_url, headers=headers, proxies=proxies, timeout=10)

        # 3. JSON 파싱 전 상태 코드 확인 및 예외 처리
        if final_res.status_code == 200:
            try:
                data = final_res.json()
                robux = data.get('robux', 0)
                return robux, "정상"
            except json.JSONDecodeError:
                return 0, "JSON 파싱 실패 (로블록스 응답 이상)"
        
        elif final_res.status_code == 401:
            return 0, "쿠키 만료/로그아웃됨"
        elif final_res.status_code == 403:
            return 0, "IP 차단 또는 토큰 만료"
        elif final_res.status_code == 429:
            return 0, "요청 과다 (잠시 후 시도)"
        else:
            return 0, f"에러 발생 ({final_res.status_code})"

    except requests.exceptions.Timeout:
        return 0, "연결 시간 초과 (네트워크 불안정)"
    except Exception as e:
        return 0, f"오류: {str(e)[:15]}"
