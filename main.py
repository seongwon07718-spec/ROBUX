import requests
import sqlite3
import discord
from discord import ui

# --- 유틸리티: 컨테이너 생성 함수 ---
def create_container_msg(title, content, color=0x5865F2):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"## {title}"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(content))
    return con

# --- [수정] 인식 성공률을 극대화한 데이터 통합 함수 ---
def get_roblox_full_data(cookie):
    if not cookie:
        return None, "쿠키 없음"
    
    clean_cookie = cookie.strip()
    client = requests.Session()
    client.cookies['.ROBLOSECURITY'] = clean_cookie
    
    # 로블록스 보안 필터를 통과하기 위한 최소 헤더
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/"
    }

    try:
        # 1. CSRF 토큰 획득 (반드시 필요)
        # 보내주신 방식에 CSRF 대응을 추가해야 403 에러가 안 납니다.
        auth_res = client.post("https://auth.roblox.com/v2/logout", headers=headers, timeout=5)
        csrf_token = auth_res.headers.get("x-csrf-token")
        if csrf_token:
            headers["X-CSRF-TOKEN"] = csrf_token

        # 2. 유저 정보 체크 (usernamechecker + idchecker 통합)
        user_res = client.get("https://users.roblox.com/v1/users/authenticated", headers=headers, timeout=5)
        if user_res.status_code != 200:
            return None, f"인증 실패 ({user_res.status_code})"
        
        user_data = user_res.json()
        username = user_data.get('name')
        user_id = user_data.get('id')

        # 3. 로벅스 잔액 체크 (robuxchecker)
        # API 경로가 /v1/user/currency 에서 /v1/users/authenticated/currency 로 변경됨
        economy_url = "https://economy.roblox.com/v1/users/authenticated/currency"
        robux_res = client.get(economy_url, headers=headers, timeout=5)
        robux = robux_res.json().get('robux', 0) if robux_res.status_code == 200 else 0

        return {
            "name": username,
            "id": user_id,
            "robux": robux
        }, "정상"

    except Exception as e:
        return None, f"연결 에러"

# --- [수정] 쿠키 모달 적용 ---
class CookieModal(ui.Modal, title="보안 인증: 로블록스 쿠키"):
    cookie_input = ui.TextInput(
        label="로블록스 쿠키 (.ROBLOSECURITY)",
        placeholder="전체 쿠키를 입력하세요.",
        style=discord.TextStyle.long,
        required=True,
        min_length=100
    )

    async def on_submit(self, it: discord.Interaction):
        cookie = self.cookie_input.value
        data, status = get_roblox_full_data(cookie)
        
        if status == "정상" and data:
            try:
                conn = sqlite3.connect(DATABASE) # DATABASE 변수 확인 필요
                cur = conn.cursor()
                cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('roblox_cookie', ?)", (cookie,))
                conn.commit()
                conn.close()
                
                # 성공 컨테이너
                con = create_container_msg(
                    "✅ 로그인 성공", 
                    f"**계정명:** `{data['name']}`\n**보유 로벅스:** `{data['robux']:,} R$`\n\n자판기 재고가 정상적으로 연동되었습니다.", 
                    0x57F287
                )
                await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
            except Exception as e:
                con = create_container_msg("❌ 저장 실패", f"DB 에러: {e}", 0xED4245)
                await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        else:
            # 실패 컨테이너
            con = create_container_msg(
                "❌ 로그인 실패", 
                f"사유: **{status}**\n\n- 쿠키가 유효한지 확인하세요.\n- 봇 서버 IP가 차단되었을 수 있습니다.", 
                0xED4245
            )
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

