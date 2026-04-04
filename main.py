def get_roblox_data(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    
    url = "https://economy.roblox.com/v1/users/authenticated/currency"
    headers = {
        "Cookie": f".ROBLOSECURITY={cookie}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json().get("robux", 0), "정상"
        elif response.status_code == 401:
            return 0, "쿠키 만료"
        else:
            return 0, f"에러 {response.status_code}"
    except:
        return 0, "연결 실패"

class CookieModal(ui.Modal, title="로블록스 쿠키 입력"):
    cookie_input = ui.TextInput(
        label="로블록스 쿠키 (.ROBLOSECURITY)",
        placeholder="이곳에 쿠키를 입력하세요",
        style=discord.TextStyle.long,
        required=True
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
            await it.response.send_message(f"✅ 로그인 성공! 현재 재고: `{robux:,}` R$", ephemeral=True)
        else:
            await it.response.send_message(f"❌ 로그인 실패: {status}", ephemeral=True)
