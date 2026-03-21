import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, uvicorn, asyncio, json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from threading import Thread

# ================= [ 1. 설정 정보 ] =================
TOKEN = "YOUR_BOT_TOKEN"
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
REDIRECT_URI = "https://restore.v0ut.com" 

# hCaptcha 키 설정 (발급받은 키로 교체하세요)
HCAPTCHA_SITE_KEY = "YOUR_SITE_KEY"
HCAPTCHA_SECRET_KEY = "YOUR_SECRET_KEY"

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

# ================= [ 2. 디자인 & hCaptcha 로직 ] =================

BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://js.hcaptcha.com/1/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;500;700&display=swap');
    body {{ background-color: #000; color: #fff; font-family: 'Inter', sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }}
    .card {{ background: #0a0a0a; border: 1px solid #1a1a1a; padding: 45px 35px; border-radius: 28px; text-align: center; width: 100%; max-width: 380px; box-shadow: 0 25px 50px rgba(0,0,0,0.8); }}
    .logo-box {{ width: 75px; height: 75px; border-radius: 22px; background: #111; border: 1px solid #222; margin: 0 auto 30px; display: flex; justify-content: center; align-items: center; font-size: 32px; font-weight: 700; color: #fff; }}
    h1 {{ font-size: 26px; font-weight: 700; margin: 0 0 12px 0; letter-spacing: -1px; }}
    .subtitle {{ color: #666; font-size: 14px; margin-bottom: 35px; line-height: 1.6; }}
    .btn-main {{ background: #fff; color: #000; border: none; width: 100%; padding: 16px; border-radius: 16px; font-size: 15px; font-weight: 700; cursor: pointer; transition: 0.2s; text-decoration: none; display: flex; justify-content: center; align-items: center; gap: 8px; }}
    .btn-main:hover {{ background: #e5e5e5; transform: translateY(-2px); }}
    .user-pill {{ background: #111; border: 1px solid #222; border-radius: 50px; padding: 10px 18px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; font-size: 13px; color: #888; }}
    .h-captcha {{ margin-bottom: 25px; display: flex; justify-content: center; }}
    .fade {{ animation: fadeInUp 0.7s cubic-bezier(0.16, 1, 0.3, 1); }}
    @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
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
                <p class="subtitle">계정을 연결하고 서버 접근 권한을<br>안전하게 획득하세요.</p>
                <a href="{discord_login_url}" class="btn-main">Discord로 시작하기</a>
            </div>
        </body></html>
        """

    # 단계 2: 로그인 후 hCaptcha 화면
    async with aiohttp.ClientSession() as session:
        # 유저 정보 미리 가져오기 (디자인용)
        payload = {{'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI}}
        async with session.post('https://discord.com/api/v10/oauth2/token', data=payload) as r:
            t_data = await r.json()
            access_token = t_data.get('access_token')
            if not access_token: return "OAuth Error"
            
            async with session.get('https://discord.com/api/v10/users/@me', headers={{'Authorization': f'Bearer {{access_token}}'}}) as r2:
                u_info = await r2.json()
                
                return f"""
                <html><head>{BASE_STYLE}</head>
                <body>
                    <div class="card fade">
                        <div class="logo-box">🔒</div>
                        <h1>본인 확인</h1>
                        <p class="subtitle">자동화 프로그램 방지를 위해<br>캡차를 완료해 주세요.</p>
                        <div class="user-pill">
                            <span>{u_info['username']}</span>
                            <a href="{discord_login_url}" style="color:#fff; text-decoration:none; font-weight:700;">변경</a>
                        </div>
                        <form action="/verify" method="post">
                            <input type="hidden" name="code" value="{code}">
                            <input type="hidden" name="server_id" value="{server_id}">
                            <input type="hidden" name="access_token" value="{access_token}">
                            <input type="hidden" name="user_id" value="{u_info['id']}">
                            <div class="h-captcha" data-sitekey="{HCAPTCHA_SITE_KEY}" data-theme="dark"></div>
                            <button type="submit" class="btn-main">인증 완료</button>
                        </form>
                    </div>
                </body></html>
                """

@app.post("/verify", response_class=HTMLResponse)
async def verify_captcha(request: Request, code: str = Form(...), server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    form_data = await request.form()
    captcha_response = form_data.get("h-captcha-response")

    # hCaptcha 서버 측 검증 로직
    async with aiohttp.ClientSession() as session:
        async with session.post('https://hcaptcha.com/siteverify', data={{'secret': HCAPTCHA_SECRET_KEY, 'response': captcha_response}}) as resp:
            result = await resp.json()
            
            if result.get("success"):
                # 검증 성공 시에만 DB 저장
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
                        <p class="subtitle">보안 검사가 성공적으로 끝났습니다.<br>이제 창을 닫으셔도 좋습니다.</p>
                        <div class="footer">SUCCESSFULLY VERIFIED</div>
                    </div>
                </body></html>
                """
            else:
                return "캡차 인증에 실패했습니다. 이전 페이지로 돌아가 다시 시도하세요."

# ================= [ 3. Discord: 명령어 ] =================

@bot.tree.command(name="인증하기", description="인증 메뉴 출력")
async def authenticate(it: discord.Interaction):
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={it.guild_id}"
    view = ui.View().add_item(ui.Button(label="인증 시작", url=url, style=discord.ButtonStyle.link))
    await it.response.send_message(embed=discord.Embed(title="RESTORE SYSTEM", description="서버 입장을 위해 아래 버튼을 눌러주세요.", color=0x000000), view=view)

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    bot.run(TOKEN)
