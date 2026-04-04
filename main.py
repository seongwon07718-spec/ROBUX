def get_roblox_data(cookie, proxy=None):
    if not cookie:
        return 0, "쿠키 없음"
        
    auth_cookie = cookie.strip().strip('"').strip("'")
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", auth_cookie, domain=".roblox.com")
    
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com"
    }

    try:
        token_res = session.post("https://auth.roblox.com/v2/logout", headers=headers, proxies=proxies, timeout=7)
        x_token = token_res.headers.get("x-csrf-token")

        if x_token:
            headers["X-CSRF-TOKEN"] = x_token

        economy_url = "https://economy.roblox.com/v1/users/authenticated/currency"
        final_res = session.get(economy_url, headers=headers, proxies=proxies, timeout=7)

        if final_res.status_code == 200:
            robux = final_res.json().get('robux', 0)
            return robux, "정상"
        elif final_res.status_code == 401:
            return 0, "쿠키 무효 IP 불일치"
        elif final_res.status_code == 403:
            return 0, "보안 차단 IP 차단됨"
        else:
            return 0, f"에러 {final_res.status_code}"

    except Exception as e:
        return 0, "연결 실패 Timeout"

def create_container_msg(title, content, color=0x5865F2):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"## {title}"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(content))
    return con
