import requests

def check_roblox_login(cookie):
    if not cookie:
        return False, "쿠키 없음"
    
    # 1. 쿠키 전처리
    auth_cookie = cookie.strip().strip('"').strip("'")
    
    session = requests.Session()
    
    # 2. 브라우저 헤더 설정
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Cookie": f".ROBLOSECURITY={auth_cookie}",
        "Accept": "application/json",
        "Referer": "https://roblox.com"
    }

    try:
        # 3. 내 계정 정보 가져오는 API (가장 가볍고 보안이 덜함)
        # 이 API는 CSRF 토큰(X-CSRF-TOKEN)이 필요 없어서 로그인 체크용으로 최고임
        user_info_url = "https://roblox.com"
        response = session.get(user_info_url, headers=headers, timeout=10)

        if response.status_code == 200:
            user_data = response.json()
            user_name = user_data.get('name', 'Unknown')
            user_id = user_data.get('id', 'Unknown')
            return True, f"로그인 성공! (계정명: {user_name}, ID: {user_id})"
        
        elif response.status_code == 401:
            return False, "쿠키가 만료되었거나 틀림 (Unauthorized)"
        
        else:
            return False, f"서버 거부 (HTTP {response.status_code})"

    except Exception as e:
        return False, f"연결 오류: {str(e)[:20]}"

# --- VS Code 실행부 ---
if __name__ == "__main__":
    # 여기에 복사한 쿠키를 넣으세요
    my_cookie = "_|WARNING:-DO-NOT-SHARE-..." 
    
    success, message = check_roblox_login(my_cookie)
    
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
