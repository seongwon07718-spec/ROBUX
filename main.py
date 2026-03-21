import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, uvicorn, asyncio, json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from threading import Thread

# 설정 정보
TOKEN = "" # 봇 토큰 입력
CLIENT_ID = "1482041261111382066"
CLIENT_SECRET = "2IbFgl910fy8yd6WDCAvBGj9Asa-BsQi"
REDIRECT_URI = "https://restore.v0ut.com" 

CF_TURNSTILE_SITE_KEY = "0x4AAAAAACt7wUkh4DATyGf_"
CF_TURNSTILE_SECRET_KEY = "0x4AAAAAACt7wYg5nw0sXHF4URhhszJq_EA"

app = FastAPI()
intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        conn = sqlite3.connect('restore_user.db')
        # 테이블 생성
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, ip_addr TEXT, PRIMARY KEY(user_id, server_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS settings (server_id TEXT PRIMARY KEY, role_id TEXT, block_alt INTEGER DEFAULT 0, block_vpn INTEGER DEFAULT 0)")
        
        # 기존 테이블에 누락된 컬럼 자동 추가 (사진 속 오류 해결)
        columns_to_check = {
            "users": ["ip_addr"],
            "settings": ["block_alt", "block_vpn"]
        }
        
        for table, cols in columns_to_check.items():
            for col in cols:
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER DEFAULT 0")
                except:
                    pass # 이미 컬럼이 존재함
        
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"로그인 완료: {self.user}")

bot = RecoveryBot()

# 웹 페이지 디자인 스타일 (투명 박스 및 간격 최적화)
BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
    
    body {{ 
        background-color: #000; 
        color: #fff; 
        font-family: 'Inter', -apple-system, sans-serif; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        min-height: 100vh; 
        margin: 0; 
        padding: 0; 
        background-image: radial-gradient(circle at center, #111 0%, #000 100%);
    }}

    .card {{ 
        background: transparent; /* 박스 투명화 */
        border: 1px solid rgba(255, 255, 255, 0.1); 
        padding: 40px; 
        border-radius: 32px; 
        text-align: center; 
        width: 90%; 
        max-width: 380px; 
        backdrop-filter: blur(10px); /* 배경 흐림 효과로 고급스러움 추가 */
        display: flex;
        flex-direction: column;
        gap: 20px; /* 모든 요소 간격을 20px로 일정하게 고정 */
    }}

    .logo-box {{ 
        width: 64px; 
        height: 64px; 
        border-radius: 18px; 
        background: rgba(255, 255, 255, 0.05); 
        border: 1px solid rgba(255, 255, 255, 0.1); 
        margin: 0 auto; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        font-size: 28px;
    }}

    h1 {{ font-size: 22px; font-weight: 700; margin: 0; letter-spacing: -0.5px; }}
    
    .subtitle {{ 
        color: #888; 
        font-size: 14px; 
        margin: 0; 
        line-height: 1.5; 
        word-break: keep-all; 
    }}

    .user-pill {{ 
        background: rgba(255, 255, 255, 0.05); 
        border: 1px solid rgba(255, 255, 255, 0.1); 
        border-radius: 14px; 
        padding: 12px 16px; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        font-size: 13px; 
    }}

    .cf-turnstile {{ 
        display: flex; 
        justify-content: center; 
        min-height: 65px;
    }}

    .btn-main {{ 
        background: #fff; 
        color: #000; 
        border: none; 
        width: 100%; 
        padding: 16px; 
        border-radius: 14px; 
        font-size: 15px; 
        font-weight: 700; 
        cursor: pointer; 
        text-decoration: none;
        transition: transform 0.2s;
    }}
    
    .btn-main:active {{ transform: scale(0.98); }}

    .footer {{ color: #444; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; margin-top: 10px; }}

    /* 애니메이션 */
    .fade {{ animation: fadeInUp 0.5s ease-out forwards; }}
    @keyframes fadeInUp {{ 
        from {{ opacity: 0; transform: translateY(10px); }} 
        to {{ opacity: 1; transform: translateY(0); }} 
    }}
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code = request.query_params.get("code")
    server_id = request.query_params.get("state")
    discord_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={server_id}"
    
    if not code:
        return f"""<html><head>{BASE_STYLE}</head><body>
        <div class='card fade'>
            <div class='logo-box'>S</div>
            <h1>서버 보안 인증</h1>
            <p class='subtitle'>계정을 연결하고 서버 접근 권한을<br>획득하세요</p>
            <a href='{discord_url}' class='btn-main'>Discord로 시작하기</a>
            <div class='footer'>RESTORE PROTOCOL</div>
        </div></body></html>"""

    async with aiohttp.ClientSession() as session:
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
            if not access_token: return "오류: 액세스 토큰을 받아오지 못했습니다."
            
            async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as r2:
                u_info = await r2.json()
                return f"""<html><head>{BASE_STYLE}</head><body>
                <div class="card fade">
                    <div class="logo-box">🔒</div>
                    <h1>보안 확인</h1>
                    <p class="subtitle">Cloudflare 보안 시스템이<br>브라우저를 확인 중입니다</p>
                    <div class="user-pill">
                        <span>{u_info.get('username')}</span>
                        <a href="{discord_url}" style="color:#fff; text-decoration:none; font-weight:700;">변경</a>
                    </div>
                    <form action="/verify" method="post" style="display:flex; flex-direction:column; gap:20px; width:100%;">
                        <input type="hidden" name="server_id" value="{server_id}">
                        <input type="hidden" name="access_token" value="{access_token}">
                        <input type="hidden" name="user_id" value="{u_info.get('id')}">
                        <div class="cf-turnstile" data-sitekey="{CF_TURNSTILE_SITE_KEY}" data-theme="dark"></div>
                        <button type="submit" class="btn-main">인증 완료</button>
                    </form>
                    <div class="footer">RESTORE PROTOCOL</div>
                </div></body></html>"""

@app.post("/verify", response_class=HTMLResponse)
async def verify_turnstile(request: Request, server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    form_data = await request.form()
    turnstile_response = form_data.get("cf-turnstile-response")
    user_ip = request.headers.get("cf-connecting-ip") or request.client.host

    async with aiohttp.ClientSession() as session:
        verify_data = {'secret': CF_TURNSTILE_SECRET_KEY, 'response': turnstile_response}
        async with session.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=verify_data) as resp:
            result = await resp.json()
            if not result.get("success"):
                return "보안 검증에 실패했습니다. 다시 시도해 주세요."

            conn = sqlite3.connect('restore_user.db')
            cur = conn.cursor()
            cur.execute("SELECT role_id, block_alt FROM settings WHERE server_id = ?", (server_id,))
            setting = cur.fetchone()
            
            if setting and setting[1] == 1:
                cur.execute("SELECT user_id FROM users WHERE server_id = ? AND ip_addr = ? AND user_id != ?", (server_id, user_ip, user_id))
                if cur.fetchone():
                    conn.close()
                    return "인증 제한: 동일한 IP에서 다른 계정으로 인증된 기록이 있습니다."

            conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (user_id, server_id, access_token, user_ip))
            conn.commit()
            if setting and setting[0]:
                asyncio.run_coroutine_threadsafe(give_role_task(server_id, user_id, int(setting[0])), bot.loop)
            conn.close()

            return f"""<html><head>{BASE_STYLE}</head><body>
            <div class="card fade">
                <div class="logo-box" style="background:#fff; color:#000;">✓</div>
                <h1>인증 완료</h1>
                <p class="subtitle">보안 검사가 성공적으로 끝났습니다</p>
                <div style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 20px; border-radius: 16px; font-size: 14px;">
                    성공적으로 승인되었습니다
                </div>
                <div class="footer">SERVICE VOUT VERIFIED</div>
            </div></body></html>"""

# [슬래시 명령어들은 기존과 동일하게 유지]
@bot.tree.command(name="지급역할", description="인증 완료 시 지급할 역할을 설정합니다")
@app_commands.checks.has_permissions(administrator=True)
async def set_role(it: discord.Interaction, role: discord.Role):
    conn = sqlite3.connect('restore_user.db')
    conn.execute("INSERT INTO settings (server_id, role_id) VALUES (?, ?) ON CONFLICT(server_id) DO UPDATE SET role_id=excluded.role_id", (str(it.guild_id), str(role.id)))
    conn.commit()
    conn.close()
    await it.response.send_message(f"✅ 인증 시 **{role.name}** 역할을 지급하도록 설정했습니다.", ephemeral=True)

@bot.tree.command(name="인증하기", description="인증 컨테이너를 전송합니다")
async def authenticate(it: discord.Interaction):
    await it.response.send_message(content="**인증 메세지 전송 완료**", ephemeral=True)
    res_con = ui.Container()
    res_con.accent_color = 0xffffff
    res_con.add_item(ui.TextDisplay("## 서버 보안 인증\n아래 버튼을 눌러 본인 인증을 완료하고 서버 접근 권한을 획득하세요."))
    auth_url = (f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&token_access_type=offline&response_type=code&scope=identify%20guilds.join&state={it.guild_id}")
    auth_btn = ui.Button(label="보안 인증 시작하기", url=auth_url, style=discord.ButtonStyle.link, emoji="🔒")
    res_con.add_item(ui.ActionRow(auth_btn))
    await it.channel.send(view=ui.LayoutView().add_item(res_con))

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="error")

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    try: bot.run(TOKEN)
    except Exception as e: print(f"봇 시작 실패: {e}")

