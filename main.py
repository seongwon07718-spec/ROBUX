import requests

def roblox_login_global(cookie):
    # 1. 초기 설정 (공백/따옴표 제거는 필수)
    auth_cookie = cookie.strip().strip('"').strip("'")
    
    # 해외 봇들이 사용하는 표준 세션 구성
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", auth_cookie, domain=".roblox.com")
    
    # [중요] 해외 서버 우회용 RoProxy 사용 (직접 연결 시 차단될 확률 90%)
    # 만약 본인 PC(한국 IP)에서 직접 돌릴 거라면 roproxy.com을 roblox.com으로 바꾸세요.
    target_domain = "roproxy.com" 

    standard_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": f"https://www.{target_domain}/"
    }

    try:
        # STEP 1: CSRF 토큰 탈취 (해외 개발자들의 '국룰' 방식)
        # 로블록스는 POST 요청 시 토큰이 없으면 403 에러와 함께 헤더에 토큰을 실어 보냅니다.
        token_response = session.post(f"https://auth.{target_domain}/v2/logout", headers=standard_headers)
        x_token = token_response.headers.get("x-csrf-token")

        if not x_token:
            return "토큰 획득 실패: 쿠키가 이미 죽었거나 IP가 블랙리스트입니다."

        # 세션 전체에 토큰 고정
        session.headers.update({"X-CSRF-TOKEN": x_token})

        # STEP 2: 실제 데이터 호출 (잔액 확인)
        economy_url = f"https://economy.{target_domain}/v1/users/authenticated/currency"
        final_res = session.get(economy_url, headers=standard_headers)

        if final_res.status_code == 200:
            data = final_res.json()
            return f"성공! 잔액: {data.get('robux', 0)} Robux"
        elif final_res.status_code == 401:
            return "실패: 쿠키 무효화 (IP 불일치 가능성)"
        else:
            return f"실패: 보안 차단 ({final_res.status_code})"

    except Exception as e:
        return f"연결 오류: {str(e)}"

# --- 실행부 ---
# COOKIE = "여기에 전체 쿠키 입력"
# print(roblox_login_global(COOKIE))
