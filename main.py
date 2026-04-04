def get_roblox_data(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    
    clean_cookie = cookie.strip()
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", clean_cookie, domain=".roblox.com")
    
    # 실제 브라우저와 유사한 헤더 설정 (IP/CSRF 차단 우회용)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.roblox.com/home",
        "Origin": "https://www.roblox.com"
    }

    try:
        # 1. CSRF 토큰을 얻기 위한 초기 요청
        auth_url = "https://auth.roblox.com/v2/logout" # 로그아웃 API는 403 에러와 함께 X-CSRF-TOKEN을 반환함
        auth_res = session.post(auth_url, headers=headers, timeout=5)
        csrf_token = auth_res.headers.get("x-csrf-token")
        
        if csrf_token:
            headers["X-CSRF-TOKEN"] = csrf_token

        # 2. 실제 잔액 조회 요청
        url = "https://economy.roblox.com/v1/users/authenticated/currency"
        response = session.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            return response.json().get("robux", 0), "정상"
        elif response.status_code == 401:
            return 0, "쿠키 만료"
        elif response.status_code == 403:
            return 0, "보안 차단 (CSRF 미일치)"
        else:
            return 0, f"에러 {response.status_code}"
    except Exception as e:
        return 0, f"연결 실패 ({str(e)[:10]})"

class CookieModal(ui.Modal, title="보안 인증: 로블록스 쿠키"):
    cookie_input = ui.TextInput(
        label="로블록스 쿠키 (.ROBLOSECURITY)",
        placeholder="경고 문구가 포함된 전체 쿠키를 입력하세요.",
        style=discord.TextStyle.long,
        required=True,
        min_length=100
    )

    async def on_submit(self, it: discord.Interaction):
        cookie = self.cookie_input.value
        robux, status = get_roblox_data(cookie)
        
        if status == "정상":
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('roblox_cookie', ?)", (cookie,))
            conn.commit()
            conn.close()
            
            con = create_container_msg("✅ 인증 성공", f"성공적으로 연결되었습니다\n현재 재고: `{robux:,}` R$")
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        else:
            con = create_container_msg("❌ 인증 실패", f"쿠키 인식에 실패했습니다\n사유: `{status}`")
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
