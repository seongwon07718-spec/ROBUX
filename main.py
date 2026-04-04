import requests
import sqlite3

# 1. 로블록스 데이터 및 로그인 상태 확인 함수
def get_roblox_auth_result(cookie):
    """
    쿠키의 유효성을 검사하고 결과를 반환합니다.
    반환값: (성공여부, 로벅스 수량 또는 에러메시지)
    """
    if not cookie:
        return False, "입력된 쿠키가 없습니다."
    
    # 쿠키 포맷 정리
    auth_cookie = cookie.strip().strip('"').strip("'")
    if not auth_cookie.startswith(".ROBLOSECURITY="):
        full_cookie = f".ROBLOSECURITY={auth_cookie}"
    else:
        full_cookie = auth_cookie
    
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": full_cookie,
    }

    try:
        # 유저 인증 API 호출
        res = session.get("https://users.roblox.com/v1/users/authenticated", headers=headers, timeout=7)
        if res.status_code == 200:
            user_id = res.json().get('id')
            # 로벅스 수량 가져오기
            eco_res = session.get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers=headers, timeout=5)
            robux = eco_res.json().get('robux', 0) if eco_res.status_code == 200 else 0
            return True, robux
        return False, "만료되었거나 잘못된 쿠키입니다."
    except:
        return False, "로블록스 서버와 연결할 수 없습니다."

# 2. UI 컨테이너 생성 유틸리티
def create_result_container(is_success, detail):
    """
    성공/실패 여부에 따라 색상과 내용을 다르게 생성합니다.
    """
    con = ui.Container()
    
    if is_success:
        # ✅ 등록 성공 (초록색)
        con.accent_color = 0x57F287 
        con.add_item(ui.TextDisplay("## ✨ 쿠키 등록 성공"))
        con.add_item(ui.Separator(spacing=2))
        con.add_item(ui.TextDisplay(f"정상적으로 인증되었습니다.\n현재 잔액: **{detail:,} R$**"))
    else:
        # ❌ 등록 실패 (빨간색)
        con.accent_color = 0xED4245 
        con.add_item(ui.TextDisplay("## ⚠️ 쿠키 등록 실패"))
        con.add_item(ui.Separator(spacing=2))
        con.add_item(ui.TextDisplay(f"이유: **{detail}**\n다시 확인 후 입력해 주세요."))
        
    return con

# 3. 실제 등록 처리 예시 (모달이나 버튼 이벤트 내부에 작성)
async def process_cookie_registration(interaction, input_cookie):
    # 검증 시도
    success, result = get_roblox_auth_result(input_cookie)
    
    if success:
        # DB에 쿠키 저장 (성공했을 때만)
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('roblox_cookie', ?)", (input_cookie,))
        conn.commit()
        conn.close()
    
    # 결과 컨테이너 생성
    result_ui = create_result_container(success, result)
    
    # 결과 전송 (에페머럴 등을 활용해 본인에게만 보이게 가능)
    await interaction.response.send_message(embeds=[], view=ui.LayoutView().add_item(result_ui), ephemeral=True)
