import requests
import json

def get_roblox_data(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    
    auth_cookie = cookie.strip().strip('"').strip("'")
    session = requests.Session()
    
    # 헤더를 브라우저와 99% 동일하게 맞춰서 차단 회피
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Cookie": f".ROBLOSECURITY={auth_cookie}",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com",
        "Accept": "application/json, text/plain, */*"
    }

    try:
        # 1. CSRF 토큰 획득
        token_res = session.post("https://roblox.com", headers=headers, timeout=10)
        x_token = token_res.headers.get("x-csrf-token")
        
        if not x_token:
            return 0, f"토큰 획득 실패 (상태코드: {token_res.status_code})"

        headers["X-CSRF-TOKEN"] = x_token

        # 2. 로벅스 정보 조회
        economy_url = "https://roblox.com"
        final_res = session.get(economy_url, headers=headers, timeout=10)

        # [디버깅] 서버가 실제로 보낸 내용을 확인 (분석 오류 시 출력용)
        raw_text = final_res.text 

        if final_res.status_code == 200:
            try:
                data = final_res.json()
                return data.get('robux', 0), "정상"
            except json.JSONDecodeError:
                # JSON이 아닐 경우 서버가 보낸 앞부분 50자 출력해서 원인 파악
                return 0, f"서버 응답 오류: {raw_text[:50]}" 
        
        elif final_res.status_code == 401:
            return 0, "쿠키 만료/로그아웃됨"
        else:
            return 0, f"서버 거부 (HTTP {final_res.status_code})"

    except Exception as e:
        return 0, f"오류: {str(e)[:15]}"
