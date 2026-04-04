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

# --- [수정] 보안 및 CSRF 로직이 강화된 데이터 함수 ---
def get_roblox_data(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    
    clean_cookie = cookie.strip()
    session = requests.Session()
    # 쿠키 설정
    session.cookies.set(".ROBLOSECURITY", clean_cookie, domain=".roblox.com")
    
    # 실제 브라우저 헤더 모방 (차단 우회 핵심)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.roblox.com/home",
        "Origin": "https://www.roblox.com",
        "Content-Type": "application/json"
    }

    try:
        # 1. CSRF 토큰 강제 획득 (로블록스 인증 API 특성 활용)
        # 로그아웃 요청은 토큰이 없으면 403과 함께 헤더에 토큰을 담아 보냅니다.
        csrf_res = session.post("https://auth.roblox.com/v2/logout", headers=headers, timeout=5)
        csrf_token = csrf_res.headers.get("x-csrf-token")
        
        if csrf_token:
            headers["X-CSRF-TOKEN"] = csrf_token

        # 2. 실제 잔액 조회 (획득한 토큰 포함)
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

# --- [수정] 모든 응답이 컨테이너인 쿠키 모달 ---
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
        # 처리 중 알림 (생략 가능하나 사용자 경험을 위해 권장)
        robux, status = get_roblox_data(cookie)
        
        if status == "정상":
            try:
                conn = sqlite3.connect(DATABASE)
                cur = conn.cursor()
                cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('roblox_cookie', ?)", (cookie,))
                conn.commit()
                conn.close()
                
                # 성공 시 컨테이너 UI 생성
                con = create_container_msg(
                    "✅ 인증 성공", 
                    f"로블록스 계정이 성공적으로 연결되었습니다.\n현재 재고: **{robux:,} R$**", 
                    0x57F287
                )
                await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
            except Exception as e:
                con = create_container_msg("❌ DB 오류", f"데이터 저장 중 오류가 발생했습니다: {e}", 0xED4245)
                await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        else:
            # 실패 시 컨테이너 UI 생성
            con = create_container_msg(
                "❌ 인증 실패", 
                f"입력하신 쿠키를 인식할 수 없습니다.\n사유: **{status}**\n\n- 쿠키가 올바른지 확인해주세요.\n- 봇 서버의 IP가 차단되었을 수 있습니다.", 
                0xED4245
            )
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

