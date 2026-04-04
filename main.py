def get_roblox_data(cookie):
    if not cookie:
        return False, "쿠키 없음"
    
    # 1. 쿠키 전처리 (공백 및 따옴표 제거)
    auth_cookie = cookie.strip().strip('"').strip("'")
    
    # .ROBLOSECURITY= 문구가 이미 포함되어 있는지 확인 후 처리
    if not auth_cookie.startswith(".ROBLOSECURITY="):
        full_cookie = f".ROBLOSECURITY={auth_cookie}"
    else:
        full_cookie = auth_cookie
    
    session = requests.Session()
    
    # 2. 브라우저 헤더 설정
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Cookie": full_cookie,
        "Accept": "application/json",
    }

    try:
        # 3. 실제 유저 인증 정보를 반환하는 API 주소로 수정
        user_info_url = "https://users.roblox.com/v1/users/authenticated"
        response = session.get(user_info_url, headers=headers, timeout=10)

        if response.status_code == 200:
            user_data = response.json()
            user_name = user_data.get('name', 'Unknown')
            user_id = user_data.get('id', 'Unknown')
            
            # 4. 로그인 성공 시 로벅스 정보까지 가져오기 (선택 사항)
            economy_url = f"https://economy.roblox.com/v1/users/{user_id}/currency"
            economy_res = session.get(economy_url, headers=headers, timeout=5)
            robux = economy_res.json().get('robux', 0) if economy_res.status_code == 200 else "정보 없음"
            
            return True, f"로그인 성공! (계정명: {user_name}, ID: {user_id}, 로벅스: {robux})"
        
        elif response.status_code == 401:
            return False, "쿠키가 만료되었거나 틀림 (Unauthorized)"
        
        else:
            return False, f"서버 거부 (HTTP {response.status_code})"

    except Exception as e:
        # 에러 메시지를 조금 더 상세히 출력하도록 수정
        return False, f"연결 오류: {str(e)}"

def create_container_msg(title, content, color=0x5865F2):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"## {title}"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(content))
    return con

class RobuxVending(ui.LayoutView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def build_main_menu(self):
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
        conn.close()

        cookie = row[0] if row else None
        robux, status = get_roblox_data(cookie)
        stock_display = f"{robux:,} R$" if status == "정상" else f"({status})"
