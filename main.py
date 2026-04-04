import requests

def get_roblox_data(cookie, proxy=None):
    if not cookie:
        return 0, "쿠키 없음"
    
    # 쿠키 전처리 (공백 및 불필요한 문자 제거)
    auth_cookie = cookie.strip().strip('"').strip("'")
    if not auth_cookie.startswith("_|WARNING:-DO-NOT-SHARE-"):
        return 0, "형식 오류 (경고문구 포함 전체 입력 필요)"

    session = requests.Session()
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    # 1. 헤더 기본 설정 (쿠키를 직접 헤더에 박는 게 가장 정확함)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Cookie": f".ROBLOSECURITY={auth_cookie}", # 세션 쿠키 대신 헤더 직접 삽입
        "Content-Type": "application/json",
        "Referer": "https://www.roblox.com/"
    }

    try:
        # 2. X-CSRF-TOKEN 획득 (반드시 POST 요청)
        # auth.roblox.com은 IP 차단이 심하므로 공식 API 엔드포인트 사용
        token_res = session.post("https://auth.roblox.com/v2/logout", headers=headers, proxies=proxies, timeout=7)
        
        # 로그아웃 요청은 403이 뜨면서 토큰을 줌 (정상)
        x_token = token_res.headers.get("x-csrf-token")
        if not x_token:
            return 0, "CSRF 토큰 획득 실패 (IP 차단 가능성)"
            
        headers["X-CSRF-TOKEN"] = x_token

        # 3. 실제 로벅스 정보 조회
        economy_url = "https://economy.roblox.com/v1/users/authenticated/currency"
        final_res = session.get(economy_url, headers=headers, proxies=proxies, timeout=7)

        if final_res.status_code == 200:
            robux = final_res.json().get('robux', 0)
            return robux, "정상"
        elif final_res.status_code == 401:
            return 0, "쿠키 만료 또는 무효"
        elif final_res.status_code == 403:
            return 0, "토큰 오류 또는 접근 거부"
        else:
            return 0, f"에러 {final_res.status_code}"

    except requests.exceptions.ProxyError:
        return 0, "프록시 연결 실패"
    except Exception as e:
        return 0, f"연결 실패: {str(e)[:20]}"
