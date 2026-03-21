import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, uvicorn, asyncio, json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from threading import Thread

# ================= [ 1. 설정 정보 ] =================
# 본인의 정보로 반드시 교체하세요.
TOKEN = "YOUR_BOT_TOKEN"
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
# 디스코드 포털 OAuth2 -> Redirects에 등록한 주소와 100% 일치 필수
REDIRECT_URI = "https://restore.v0ut.com" 

# 클라우드플레어 Turnstile 키 설정 (실제 키를 입력하세요)
CF_TURNSTILE_SITE_KEY = "YOUR_SITE_KEY"
CF_TURNSTILE_SECRET_KEY = "YOUR_SECRET_KEY"

app = FastAPI()
intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        conn = sqlite3.connect('restore_user.db')
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT, 
                server_id TEXT, 
                access_token TEXT, 
                PRIMARY KEY(user_id, server_id)
            )
        """)
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"로그인 완료: {self.user}")

bot = RecoveryBot()

# ================= [ 2. AI 최적화 & 반응형 레이아웃 디자인 ] =================

# 디자인 포인트: 모든 기기에서 중앙 정렬, 둥근 느낌, 블랙 & 화이트
BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
    
    /* 전체 배경: 모바일/PC 모두 중앙 정렬 최적화 */
    body {{ background-color: #000; color: #fff; font-family: 'Inter', -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; overflow-x: hidden; }}
    
    /* 메인 박스: 28px의 둥근 모서리와 자동 크기 조절 */
    .card {{ background: #0a0a0a; border: 1px solid #1a1a1a; padding: 45px 35px; border-radius: 28px; text-align: center; width: 100%; max-width: 380px; box-shadow: 0 25px 50px rgba(0,0,0,0.8); box-sizing: border-box; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
    
    /* 로고 박스 */
    .logo-box {{ width: 75px; height: 75px; border-radius: 22px; background: #111; border: 1px solid #222; margin: 0 auto 30px; display: flex; justify-content: center; align-items: center; font-size: 32px; font-weight: 700; color: #fff; flex-shrink: 0; }}
    
    /* 제목 및 부제목: 텍스트 배열 똑바로 */
    h1 {{ font-size: 26px; font-weight: 700; margin: 0 0 12px 0; letter-spacing: -1px; text-align: center; width: 100%; }}
    .subtitle {{ color: #666; font-size: 14px; margin-bottom: 35px; line-height: 1.6; text-align: center; width: 100%; max-width: 300px; }}
    
    /* 흰색 라운드 버튼 */
    .btn-main {{ background: #fff; color: #000; border: none; width: 100%; padding: 16px; border-radius: 16px; font-size: 15px; font-weight: 700; cursor: pointer; transition: 0.2s; text-decoration: none; display: flex; justify-content: center; align-items: center; box-sizing: border-box; }}
    .btn-main:hover {{ background: #e5e5e5; transform: translateY(-2px); }}
    
    /* 상태 표시 박스: 배열 똑바로 */
    .status-alert {{ background: #111; border: 1px solid #222; border-left: 4px solid #fff; padding: 20px; text-align: left; font-size: 13px; color: #ccc; margin-bottom: 25px; border-radius: 14px; line-height: 1.5; width: 100%; box-sizing: border-box; }}
    
    .user-pill {{ background: #111; border: 1px solid #222; border-radius: 50px; padding: 10px 18px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; font-size: 13px; color: #888; width: 100%; box-sizing: border-box; gap: 10px; }}
    
    /* 클라우드플레어 Turnstile 위젯 중앙 정렬 */
    .cf-turnstile {{ margin-bottom: 25px; width: 100%; display: flex; justify-content: center; }}
    
    .footer {{ color: #333; font-size: 11px; margin-top: 35px; letter-spacing: 1px; width: 100%; text-align: center; }}
    
    /* 애니메이션 효과 */
    @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    .fade {{ animation: fadeInUp 0.7s cubic-bezier(0.16, 1, 0.3, 1); }}
    
    /* 모바일용 추가 배열 최적화 */
    @media (max-width: 480px) {{
        .card {{ padding: 35px 25px; border-radius: 24px; }}
        h1 {{ font-size: 22px; }}
        .subtitle {{ font-size: 13px; }}
        .logo-box {{ width: 65px; height: 65px; font-size: 28px; }}
    }}
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code = request.query_params.get("code")
    server_id = request.query_params.get("state")
    discord_login_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={server_id}"

    # 단계 1: 초기 로그인 화면
    if not code:
        return f"""
        <html><head>{BASE_STYLE}</head>
        <body>
            <div class="card fade">
                <div class="logo-box">S</div>
                <h1>서버 보안 인증</h1>
                <p class="subtitle">계정을 연결하고 서버 접근 권한을<br>획득하세요.</p>
                <div class="status-alert">디스코드 로그인이 필요합니다.<br>인증 후 자동으로 역할이 부여됩니다.</div>
                <a href="{discord_login_url}" class="btn-main">Discord로 시작하기</a>
                <div class="footer">RESTORE PROTOCOL</div>
            </div>
        </body></html>
        """

    async with aiohttp.ClientSession() as session:
        # 로그인 정보 가져오기 (이전 오류 수정 완료)
        payload = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        }
        async with session.post('https://discord.com/api/v10/oauth2/token', data=payload) as r:
            t_data = await r.json()
            access_token = t_data.get('access_token')
            if not access_token: return "Error: Token Missing"
            
            async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as r2:
                u_info = await r2.json()
                
                # 단계 2: 로그인 후 Turnstile 화면
                return f"""
                <html><head>{BASE_STYLE}</head>
                <body>
                    <div class="card fade">
                        <div class="logo-box">🔒</div>
                        <h1>보안 확인</h1>
                        <p class="subtitle">Cloudflare 보안 시스템이<br>브라우저를 확인 중입니다.</p>
                        <div class="user-pill">
                            <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{u_info.get('username', 'Unknown')}</span>
                            <a href="{discord_login_url}" style="color:#fff; text-decoration:none; font-weight:700; flex-shrink: 0;">변경</a>
                        </div>
                        <form action="/verify" method="post" style="width: 100%;">
                            <input type="hidden" name="server_id" value="{server_id}">
                            <input type="hidden" name="access_token" value="{access_token}">
                            <input type="hidden" name="user_id" value="{u_info.get('id')}">
                            <div class="cf-turnstile" data-sitekey="{CF_TURNSTILE_SITE_KEY}" data-theme="dark"></div>
                            <button type="submit" class="btn-main">인증 완료</button>
                        </form>
                    </div>
                </body></html>
                """

@app.post("/verify", response_class=HTMLResponse)
async def verify_turnstile(request: Request, server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    form_data = await request.form()
    turnstile_response = form_data.get("cf-turnstile-response")

    # Cloudflare Turnstile 서버 검증 로직
    async with aiohttp.ClientSession() as session:
        verify_data = {'secret': CF_TURNSTILE_SECRET_KEY, 'response': turnstile_response}
        async with session.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=verify_data) as resp:
            result = await resp.json()
            
            if result.get("success"):
                conn = sqlite3.connect('restore_user.db')
                conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_id, server_id, access_token))
                conn.commit()
                conn.close()
                
                # 단계 3: 완료 화면
                return f"""
                <html><head>{BASE_STYLE}</head>
                <body>
                    <div class="card fade">
                        <div class="logo-box" style="background:#fff; color:#000;">✓</div>
                        <h1>인증 완료</h1>
                        <p class="subtitle">보안 검사가 성공적으로 끝났습니다.</p>
                        <div class="status-alert" style="border-left-color:#fff; text-align:center;">성공적으로 승인되었습니다.</div>
                        <div class="footer">SUCCESSFULLY VERIFIED</div>
                    </div>
                </body></html>
                """
            else:
                return "보안 검증 실패. 다시 시도해 주세요."

@bot.tree.command(name="인증하기")
async def authenticate(it: discord.Interaction):
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={it.guild_id}"
    await it.response.send_message(view=ui.View().add_item(ui.Button(label="인증 시작", url=url, style=discord.ButtonStyle.link)))

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    bot.run(TOKEN)
