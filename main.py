import requests
import re

def get_roblox_data_ultimate(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    
    # [필수] 쿠키에서 불필요한 따옴표나 공백 완벽 제거
    clean_cookie = cookie.strip().strip('"').strip("'")
    
    # .ROBLOSECURITY 문구가 누락되었다면 붙여주기 (가끔 실수하는 부분)
    if not clean_cookie.startswith("_|WARNING:-DO-NOT-SHARE-THIS"):
        return 0, "쿠키 형식 오류 (Warning 문구 포함 전체 복사 필요)"

    session = requests.Session()
    
    # 쿠키 설정 (도메인 설정 시 .roblox.com과 roblox.com 둘 다 커버)
    session.cookies.set(".ROBLOSECURITY", clean_cookie, domain=".roblox.com")
    
    # RoProxy 도메인 사용
    BASE_URL = "roproxy.com"
    
    # 실제 브라우저와 거의 동일한 헤더 (이게 핵심)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": f"https://www.{BASE_URL}",
        "Referer": f"https://www.{BASE_URL}/",
        "Sec-Ch-Ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }

    try:
        # [1단계] 쿠키 생존 확인 (가장 가벼운 API 호출)
        # 여기서 401이 뜨면 진짜로 쿠키가 죽은 겁니다.
        test_url = f"https://users.{BASE_URL}/v1/users/authenticated"
        test_res = session.get(test_url, headers=headers, timeout=10)
        
        if test_res.status_code == 401:
            return 0, "쿠키 사망 (IP 차단 혹은 실제 만료)"
        
        # [2단계] CSRF 토큰 갱신
        auth_url = f"https://auth.{BASE_URL}/v2/logout"
        auth_res = session.post(auth_url, headers=headers, timeout=10)
        csrf_token = auth_res.headers.get("x-csrf-token")
        
        if not csrf_token:
            return 0, "CSRF 획득 실패 (프록시 서버 문제 가능성)"

        headers["X-CSRF-TOKEN"] = csrf_token
        
        # [3단계] 잔액 확인
        economy_url = f"https://economy.{BASE_URL}/v1/users/authenticated/currency"
        response = session.get(economy_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json().get("robux", 0), "성공"
        else:
            return 0, f"최종 실패 ({response.status_code})"

    except Exception as e:
        return 0, f"연결 에러: {str(e)}"
