import requests
import sqlite3

# [주의] DATABASE 변수는 기존 코드의 경로에 맞게 설정하세요.
DATABASE = "your_database_path.db" 

def get_roblox_data(cookie):
    """
    쿠키를 통해 로그인 상태와 로벅스 수량만 반환합니다.
    반환값: (성공여부, 로벅스 수량 또는 에러메시지)
    """
    if not cookie:
        return False, "쿠키 없음"
    
    auth_cookie = cookie.strip().strip('"').strip("'")
    if not auth_cookie.startswith(".ROBLOSECURITY="):
        full_cookie = f".ROBLOSECURITY={auth_cookie}"
    else:
        full_cookie = auth_cookie
    
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Cookie": full_cookie,
    }

    try:
        # 1. 유저 인증 확인
        user_info_url = "https://users.roblox.com/v1/users/authenticated"
        response = session.get(user_info_url, headers=headers, timeout=10)

        if response.status_code == 200:
            user_id = response.json().get('id')
            
            # 2. 로벅스 수량 확인
            economy_url = f"https://economy.roblox.com/v1/users/{user_id}/currency"
            economy_res = session.get(economy_url, headers=headers, timeout=5)
            
            if economy_res.status_code == 200:
                robux_amount = economy_res.json().get('robux', 0)
                # 성공 시: True와 숫자 반환
                return True, robux_amount
            return False, "로벅스 확인 실패"
        
        return False, "인증 실패"

    except Exception:
        return False, "연결 오류"

def create_container_msg(title, content, color=0x5865F2):
    """컨테이너 생성 유틸리티"""
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"## {title}"))
    # discord.SeparatorSpacing 등 라이브러리 사양에 맞춰 호출
    con.add_item(ui.Separator(spacing=2)) 
    con.add_item(ui.TextDisplay(content))
    return con

class RobuxVending(ui.LayoutView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def build_main_menu(self):
        # 1. DB에서 쿠키 가져오기
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
        conn.close()

        cookie = row[0] if row else None
        
        # 2. 로블록스 데이터 가져오기
        is_success, result = get_roblox_data(cookie)

        if is_success:
            # ✅ 로그인 성공: 초록색 컨테이너 (0x57F287)
            title = "✅ 시스템 정상"
            display_text = f"현재 가용한 로벅스 재고: **{result:,} R$**"
            container_color = 0x57F287 
        else:
            # ❌ 로그인 실패: 빨간색 컨테이너 (0xED4245)
            title = "⚠️ 시스템 점검 필요"
            display_text = f"상태: **{result}**\n관리자에게 문의하거나 쿠키를 갱신하세요."
            container_color = 0xED4245

        # 3. 컨테이너 생성 및 반환
        msg_container = create_container_msg(title, display_text, color=container_color)
        
        # 이후 로직 (self.add_item 등) 수행
        self.add_item(msg_container)
        return self
