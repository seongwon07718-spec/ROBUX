def get_roblox_data(cookie):
    auth_cookie = cookie.strip().strip('"').strip("'")
    
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", auth_cookie, domain=".roblox.com")
    
    target_domain = "roblox.com" 

    standard_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": f"https://www.{target_domain}/"
    }

    try:
        token_response = session.post(f"https://auth.{target_domain}/v2/logout", headers=standard_headers)
        x_token = token_response.headers.get("x-csrf-token")

        if not x_token:
            return "점검 중"

        session.headers.update({"X-CSRF-TOKEN": x_token})

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
