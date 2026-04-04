import requests
import sqlite3
import discord
from discord import ui

# --- 유틸리티: 모든 메시지를 컨테이너로 만드는 함수 ---
def create_container_msg(title, content, color=0xffffff):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"## {title}"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(content))
    return con

# --- [수정] 보안 강화 및 CSRF 우회 로직 (외국 오픈소스 방식 적용) ---
def get_roblox_data(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    
    clean_cookie = cookie.strip()
    session = requests.Session()
    
    # 쿠키 설정 (도메인 범위 명시)
    session.cookies.set(".ROBLOSECURITY", clean_cookie, domain=".roblox.com")
    
    # 실제 브라우저와 동일한 헤더 구성
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.roblox.com/home",
        "Origin": "https://www.roblox.com",
        "Content-Type": "application/json"
    }

    try:
        # 1. CSRF 토큰 갱신 (Refresh CSRF Token)
        # 로그아웃 API에 POST 요청을 보내 403 에러와 함께 반환되는 x-csrf-token을 가로챕니다.
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers, timeout=5)
        csrf_token = auth_res.headers.get("x-csrf-token")
        
        if csrf_token:
            headers["X-CSRF-TOKEN"] = csrf_token
        else:
            # 토큰이 안 올 경우 다른 인증 엔드포인트 시도
            login_res = session.post("https://auth.roblox.com/v2/login", headers=headers, timeout=5)
            csrf_token = login_res.headers.get("x-csrf-token")
            if csrf_token:
                headers["X-CSRF-TOKEN"] = csrf_token

        # 2. 실제 잔액 조회 (획득한 토큰과 함께 전송)
        url = "https://economy.roblox.com/v1/users/authenticated/currency"
        response = session.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            return response.json().get("robux", 0), "정상"
        elif response.status_code == 401:
            return 0, "쿠키 만료"
        elif response.status_code == 403:
            return 0, "보안 차단 (CSRF/IP)"
        else:
            return 0, f"HTTP {response.status_code}"
    except Exception as e:
        return 0, f"연결 실패 ({str(e)[:15]})"

# --- [수정] 컨테이너 응답 방식의 쿠키 입력 모달 ---
class CookieModal(ui.Modal, title="보안 인증: 로블록스 쿠키"):
    cookie_input = ui.TextInput(
        label="로블록스 쿠키 (.ROBLOSECURITY)",
        placeholder="_|WARNING:-DO-NOT-SHARE-THIS 문구를 포함해 전체 입력",
        style=discord.TextStyle.long,
        required=True,
        min_length=100
    )

    async def on_submit(self, it: discord.Interaction):
        cookie = self.cookie_input.value
        
        # 데이터 조회를 시작함을 알리는 임시 처리 (필요 시)
        robux, status = get_roblox_data(cookie)
        
        if status == "정상":
            try:
                # DATABASE 변수는 전역으로 선언되어 있어야 합니다.
                conn = sqlite3.connect(DATABASE)
                cur = conn.cursor()
                cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('roblox_cookie', ?)", (cookie,))
                conn.commit()
                conn.close()
                
                # 인증 성공 컨테이너 생성
                con = create_container_msg(
                    "✅ 인증 성공", 
                    f"로블록스 계정이 성공적으로 연결되었습니다\n현재 재고: **{robux:,} R$**", 
                    0x57F287
                )
                await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
            except Exception as e:
                con = create_container_msg("❌ DB 오류", f"데이터 저장 중 오류가 발생했습니다: {e}", 0xED4245)
                await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        else:
            # 인증 실패 컨테이너 생성
            con = create_container_msg(
                "❌ 인증 실패", 
                f"입력하신 쿠키를 인식할 수 없습니다\n사유: **{status}**\n\n- 쿠키가 올바른지 다시 확인해주세요\n- 봇 서버의 IP가 차단된 경우 프록시 사용을 권장합니다", 
                0xED4245
            )
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

