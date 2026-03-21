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

CF_TURNSTILE_SITE_KEY = "YOUR_SITE_KEY"
CF_TURNSTILE_SECRET_KEY = "YOUR_SECRET_KEY"

app = FastAPI()
intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        conn = sqlite3.connect('restore_user.db')
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, PRIMARY KEY(user_id, server_id))")
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"로그인 완료: {self.user}")

bot = RecoveryBot()

# ================= [ 2. 디자인 (모든 기기 정중앙 배열 + 마침표 제거) ] =================

BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
    
    /* 모든 기기 상하좌우 정중앙 정렬 */
    body {{ 
        background-color: #000; 
        color: #fff; 
        font-family: 'Inter', -apple-system, sans-serif; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        min-height: 100vh; 
        margin: 0; 
        padding: 20px; 
        box-sizing: border-box; 
    }}
    
    .card {{ 
        background: #0a0a0a; 
        border: 1px solid #1a1a1a; 
        padding: 45px 35px; 
        border-radius: 28px; 
        text-align: center; 
        width: 100%; 
        max-width: 380px; 
        box-shadow: 0 25px 50px rgba(0,0,0,0.8); 
        box-sizing: border-box; 
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        justify-content: center; 
    }}
    
    .logo-box {{ width: 75px; height: 75px; border-radius: 22px; background: #111; border: 1px solid #222; margin-bottom: 30px; display: flex; justify-content: center; align-items: center; font-size: 32px; font-weight: 700; color: #fff; flex-shrink: 0; }}
    h1 {{ font-size: 26px; font-weight: 700; margin: 0 0 12px 0; letter-spacing: -1px; text-align: center; width: 100%; }}
    .subtitle {{ color: #666; font-size: 14px; margin-bottom: 35px; line-height: 1.6; text-align: center; width: 100%; }}
    
    .btn-main {{ background: #fff; color: #000; border: none; width: 100%; padding: 16px; border-radius: 16px; font-size: 15px; font-weight: 700; cursor: pointer; transition: 0.2s; text-decoration: none; display: flex; justify-content: center; align-items: center; }}
    .status-alert {{ background: #111; border: 1px solid #222; border-left: 4px solid #fff; padding: 20px; text-align: center; font-size: 13px; color: #ccc; margin-bottom: 25px; border-radius: 14px; width: 100%; box-sizing: border-box; }}
    .user-pill {{ background: #111; border: 1px solid #222; border-radius: 50px; padding: 10px 18px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; font-size: 13px; color: #888; width: 100%; box-sizing: border-box; }}
    
    /* 로딩 바 */
    .progress-wrap {{ width: 100%; margin-bottom: 20px; }}
    .progress-bg {{ background: #1a1a1a; height: 6px; width: 100%; border-radius: 10px; overflow: hidden; margin-bottom: 8px; }}
    .progress-bar {{ background: #fff; height: 100%; width: 0%; transition: width 0.05s linear; }}
    
    .footer {{ color: #333; font-size: 11px; margin-top: 35px; letter-spacing: 1px; text-align: center; }}
    .fade {{ animation: fadeInUp 0.7s cubic-bezier(0.16, 1, 0.3, 1); }}
    @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}

    @media (max-width: 480px) {{
        .card {{ padding: 35px 25px; }}
        h1 {{ font-size: 22px; }}
    }}
</style>
"""

# ================= [ 3. 라우팅 로직 (오류 수정 완료) ] =================

@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code = request.query_params.get("code")
    server_id = request.query_params.get("state")
    discord_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={server_id}"

    if not code:
        return f"<html><head>{BASE_STYLE}</head><body><div class='card fade'><div class='logo-box'>S</div><h1>서버 보안 인증</h1><p class='subtitle'>계정을 연결하고 서버 접근 권한을<br>획득하세요</p><a href='{discord_url}' class='btn-main'>Discord로 시작하기</a><div class='footer'>RESTORE PROTOCOL</div></div></body></html>"

    async with aiohttp.ClientSession() as session:
        # 중복 괄호 {{}} 제거하여 TypeError 수정
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
            if not access_token: return "인증 토큰을 가져오지 못했습니다"
            
            async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as r2:
                u_info = await r2.json()
                return f"""
                <html><head>{BASE_STYLE}</head>
                <body>
                    <div class="card fade">
                        <div class="logo-box">🔒</div>
                        <h1>보안 확인</h1>
                        <p class="subtitle">Cloudflare 보안 시스템이<br>브라우저를 확인 중입니다</p>
                        <div class="user-pill"><span>{u_info.get('username')}</span><a href="{discord_url}" style="color:#fff; text-decoration:none; font-weight:700;">변경</a></div>
                        <form action="/verify" method="post" style="width:100%;">
                            <input type="hidden" name="server_id" value="{server_id}"><input type="hidden" name="access_token" value="{access_token}"><input type="hidden" name="user_id" value="{u_info.get('id')}">
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

    async with aiohttp.ClientSession() as session:
        verify_data = {'secret': CF_TURNSTILE_SECRET_KEY, 'response': turnstile_response}
        async with session.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=verify_data) as resp:
            result = await resp.json()
            if result.get("success"):
                # DB 저장
                conn = sqlite3.connect('restore_user.db')
                conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_id, server_id, access_token))
                conn.commit()
                conn.close()
                
                return f"""
                <html><head>{BASE_STYLE}</head>
                <body>
                    <div class="card fade">
                        <div id="loading-area" style="width:100%;">
                            <div class="logo-box">🔒</div>
                            <h1>보안 승인 중</h1>
                            <p class="subtitle">서버 권한을 할당하고 있습니다<br>잠시만 기다려 주세요</p>
                            <div class="progress-wrap">
                                <div class="progress-bg"><div id="bar" class="progress-bar"></div></div>
                                <div id="pct" style="font-size:14px; font-weight:700;">0%</div>
                            </div>
                        </div>
                        <div id="success-area" style="display:none; width:100%;">
                            <div class="logo-box" style="background:#fff; color:#000;">✓</div>
                            <h1>인증 완료</h1>
                            <p class="subtitle">보안 검사가 성공적으로 끝났습니다</p>
                            <div class="status-alert">성공적으로 승인되었습니다</div>
                            <div class="footer">SERVICE VOUT VERIFIED</div>
                        </div>
                    </div>
                    <script>
                        let p = 0;
                        const b = document.getElementById('bar');
                        const t = document.getElementById('pct');
                        const l = document.getElementById('loading-area');
                        const s = document.getElementById('success-area');
                        const iv = setInterval(() => {{
                            p++;
                            b.style.width = p + '%';
                            t.innerText = p + '%';
                            if (p >= 100) {{
                                clearInterval(iv);
                                l.style.display = 'none';
                                s.style.display = 'block';
                            }}
                        }}, 40);
                    </script>
                </body></html>
                """
            else: return "보안 검증에 실패했습니다"

@bot.tree.command(name="인증하기", description="인증하기 컨테이너를 전송합니다")
async def authenticate(it: discord.Interaction):
    # content와 view를 분리하여 400 에러 해결
    await it.response.send_message(content="인증하기가 전송되었습니다", ephemeral=True)
    
    res_con = ui.Container()
    res_con.accent_color = 0xffffff 
    res_con.add_item(ui.TextDisplay("## 서버 보안 인증"))
    res_con.add_item(ui.TextDisplay("아래 버튼을 눌러 인증하셔야 서버 이용이 가능합니다\\n**`IP, 이메일, 통신사`** 등은 일절 수집하지 않습니다"))
    
    auth_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={it.guild_id}"
    auth_btn = ui.Button(label="인증하기", url=auth_url, style=discord.ButtonStyle.link, emoji="<:emoji_14:1484745886696476702>")
    res_con.add_item(ui.ActionRow(auth_btn))
    
    view = ui.LayoutView().add_item(res_con)
    await it.channel.send(view=view)

def run_fastapi(): uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    bot.run(TOKEN)
