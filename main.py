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
        # 테이블 및 컬럼 자동 생성/수정 로직
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, ip_addr TEXT, PRIMARY KEY(user_id, server_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS settings (server_id TEXT PRIMARY KEY, role_id TEXT, block_alt INTEGER DEFAULT 0, block_vpn INTEGER DEFAULT 0)")
        
        # 누락된 컬럼 추가 (OperationalError 방지)
        try: conn.execute("ALTER TABLE settings ADD COLUMN block_alt INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE settings ADD COLUMN block_vpn INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN ip_addr TEXT")
        except: pass
        
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"Logged in as: {self.user}")

    # 노란 줄 해결을 위해 클래스 내부 메서드로 정의
    async def give_role_task(self, server_id: str, user_id: str, role_id: int):
        try:
            guild = self.get_guild(int(server_id))
            if guild:
                member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                role = guild.get_role(role_id)
                if member and role:
                    await member.add_roles(role, reason="보안 인증 완료")
        except Exception as e:
            print(f"Role Error: {e}")

bot = RecoveryBot()

# 웹 페이지 디자인: 투명 박스 스타일 (Glassmorphism) 및 20px 간격
BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
    body {{ 
        background-color: #000; 
        color: #fff; 
        font-family: 'Inter', sans-serif; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        min-height: 100vh; 
        margin: 0; 
    }}
    .card {{ 
        background: rgba(255, 255, 255, 0); /* 완전 투명 */
        border: 1px solid rgba(255, 255, 255, 0.15); 
        padding: 40px; 
        border-radius: 30px; 
        text-align: center; 
        width: 90%; 
        max-width: 360px;
        backdrop-filter: blur(20px); 
        -webkit-backdrop-filter: blur(20px);
        display: flex; 
        flex-direction: column; 
        gap: 20px; /* 모든 요소 간격 20px 고정 */
    }}
    .logo-box {{ 
        width: 60px; height: 60px; 
        background: rgba(255,255,255,0.05); 
        border-radius: 18px; 
        margin: 0 auto; 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        font-size: 24px; 
        border: 1px solid rgba(255,255,255,0.1);
    }}
    h1 {{ font-size: 22px; margin: 0; font-weight: 700; }}
    .subtitle {{ color: #888; font-size: 14px; margin: 0; line-height: 1.6; word-break: keep-all; }}
    .user-box {{ 
        background: rgba(255,255,255,0.05); 
        padding: 12px 16px; 
        border-radius: 14px; 
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        font-size: 13px; 
        border: 1px solid rgba(255,255,255,0.08);
    }}
    .btn-main {{ 
        background: #fff; 
        color: #000; 
        border: none; 
        padding: 16px; 
        border-radius: 14px; 
        font-weight: 700; 
        cursor: pointer; 
        text-decoration: none; 
        font-size: 15px;
        transition: 0.2s;
    }}
    .btn-main:active {{ transform: scale(0.98); opacity: 0.9; }}
    .footer {{ color: #333; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; }}
    .fade {{ animation: fadeInUp 0.5s ease-out; }}
    @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code = request.query_params.get("code")
    server_id = request.query_params.get("state")
    discord_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={server_id}"
    
    if not code:
        return f"<html><head>{BASE_STYLE}</head><body><div class='card fade'><div class='logo-box'>S</div><h1>서버 보안 인증</h1><p class='subtitle'>계정을 연결하고 서버 접근 권한을<br>획득하세요</p><a href='{discord_url}' class='btn-main'>Discord로 시작하기</a><div class='footer'>RESTORE PROTOCOL</div></div></body></html>"

    async with aiohttp.ClientSession() as session:
        payload = {'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI}
        async with session.post('https://discord.com/api/v10/oauth2/token', data=payload) as r:
            token_data = await r.json()
            access_token = token_data.get('access_token')
            if not access_token: return "Error: Invalid Access Token"
            
            async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as r2:
                user_info = await r2.json()
                return f"""<html><head>{BASE_STYLE}</head><body><div class='card fade'><div class='logo-box'>🔒</div><h1>보안 확인</h1><p class='subtitle'>Cloudflare 시스템이<br>브라우저를 확인 중입니다</p><div class='user-box'><span>{user_info.get('username')}</span><a href='{discord_url}' style='color:#fff; font-weight:700; text-decoration:none;'>변경</a></div><form action='/verify' method='post' style='display:flex; flex-direction:column; gap:20px;'><input type='hidden' name='server_id' value='{server_id}'><input type='hidden' name='access_token' value='{access_token}'><input type='hidden' name='user_id' value='{user_info.get('id')}'><div class='cf-turnstile' data-sitekey='{CF_TURNSTILE_SITE_KEY}' data-theme='dark'></div><button type='submit' class='btn-main'>인증 완료</button></form></div></body></html>"""

@app.post("/verify", response_class=HTMLResponse)
async def verify_post(request: Request, server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    form = await request.form()
    cf_res = form.get("cf-turnstile-response")
    user_ip = request.headers.get("cf-connecting-ip") or request.client.host

    async with aiohttp.ClientSession() as session:
        v_data = {'secret': CF_TURNSTILE_SECRET_KEY, 'response': cf_res}
        async with session.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=v_data) as resp:
            v_res = await resp.json()
            if not v_res.get("success"): return "Captcha Verification Failed"

            conn = sqlite3.connect('restore_user.db')
            cur = conn.cursor()
            cur.execute("SELECT role_id, block_alt FROM settings WHERE server_id = ?", (server_id,))
            setting = cur.fetchone()
            
            if setting and setting[1] == 1:
                cur.execute("SELECT user_id FROM users WHERE server_id = ? AND ip_addr = ? AND user_id != ?", (server_id, user_ip, user_id))
                if cur.fetchone():
                    conn.close()
                    return "보안 제한: 부계정 인증이 감지되었습니다."

            conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (user_id, server_id, access_token, user_ip))
            conn.commit()
            
            # 역할 지급 로직 호출 (클래스 메서드 사용)
            if setting and setting[0]:
                asyncio.run_coroutine_threadsafe(bot.give_role_task(server_id, user_id, int(setting[0])), bot.loop)
            
            conn.close()
            return f"<html><head>{BASE_STYLE}</head><body><div class='card fade'><div class='logo-box' style='background:#fff; color:#000;'>✓</div><h1>인증 완료</h1><p class='subtitle'>보안 검사가 성공적으로 끝났습니다.<br>서버를 이용하실 수 있습니다.</p><div class='footer'>VERIFIED BY RESTORE</div></div></body></html>"

# --- 디스코드 슬래시 명령어 ---

@bot.tree.command(name="지급역할", description="인증 완료 시 지급할 역할을 설정합니다")
@app_commands.checks.has_permissions(administrator=True)
async def set_role(it: discord.Interaction, role: discord.Role):
    conn = sqlite3.connect('restore_user.db')
    conn.execute("INSERT OR REPLACE INTO settings (server_id, role_id) VALUES (?, ?)", (str(it.guild_id), str(role.id)))
    conn.commit()
    conn.close()
    embed = discord.Embed(title="✅ 역할 설정 완료", description=f"인증 시 {role.mention} 역할을 지급합니다.", color=0xffffff)
    await it.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="인증하기", description="인증 메세지를 전송합니다")
async def send_auth(it: discord.Interaction):
    embed = discord.Embed(title="🔒 보안 인증", description="아래 버튼을 클릭하여 본인 인증을 완료해 주세요.", color=0xffffff)
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={it.guild_id}"
    view = ui.View()
    view.add_item(ui.Button(label="인증하기", url=url, style=discord.ButtonStyle.link))
    await it.channel.send(embed=embed, view=view)

@bot.tree.command(name="인증제한", description="부계정 차단 여부를 설정합니다")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(부계정=[app_commands.Choice(name="상관있음 (차단)", value=1), app_commands.Choice(name="상관없음 (허용)", value=0)])
async def restrict(it: discord.Interaction, 부계정: int):
    conn = sqlite3.connect('restore_user.db')
    conn.execute("UPDATE settings SET block_alt = ? WHERE server_id = ?", (부계정, str(it.guild_id)))
    conn.commit()
    conn.close()
    status = "🚫 차단" if 부계정 == 1 else "✅ 허용"
    await it.response.send_message(f"보안 설정: 부계정 {status}", ephemeral=True)

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="error")

if __name__ == "__main__":
    Thread(target=run_api, daemon=True).start()
    bot.run(TOKEN)

