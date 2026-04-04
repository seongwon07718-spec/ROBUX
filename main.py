import requests
import json

def get_roblox_data(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    
    auth_cookie = cookie.strip().strip('"').strip("'")
    session = requests.Session()
    
    # [핵심] 브라우저가 보내는 최신 보안 헤더들을 그대로 추가
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Cookie": f".ROBLOSECURITY={auth_cookie}",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://roblox.com",
        "Origin": "https://roblox.com",
        "Sec-Ch-Ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site"
    }

    try:
        # 1. CSRF 토큰 획득 (v2/logout 엔드포인트)
        # 403 에러가 나야 정상이며, 그 응답 헤더에서 토큰을 가져옵니다.
        token_res = session.post("https://roblox.com", headers=headers, timeout=10)
        x_token = token_res.headers.get("x-csrf-token")
        
        if not x_token:
            # 여기서 HTML이 오는지 확인하기 위해 상태 코드 체크
            if "text/html" in token_res.headers.get("Content-Type", ""):
                return 0, "로블록스 보안망에 걸림 (IP 차단/검증 필요)"
            return 0, f"토큰 획득 실패 (HTTP {token_res.status_code})"

        # 2. 획득한 토큰 삽입
        headers["X-CSRF-TOKEN"] = x_token

        # 3. 로벅스 정보 조회
        economy_url = "https://roblox.com"
        final_res = session.get(economy_url, headers=headers, timeout=10)

        if final_res.status_code == 200:
            return final_res.json().get('robux', 0), "정상"
        else:
            # 200이 아닌데 HTML이 오면 여기서 잡힘
            if "<!DOCTYPE html>" in final_res.text:
                return 0, "보안 페이지로 리다이렉트됨 (쿠키 재추출 필요)"
            return 0, f"최종 에러 ({final_res.status_code})"

    except Exception as e:
        return 0, f"오류: {str(e)[:20]}"
