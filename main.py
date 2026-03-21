import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, uvicorn, asyncio, json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from threading import Thread

# 설정 정보
TOKEN = "YOUR_BOT_TOKEN_HERE" # 여기에 봇 토큰을 입력하세요
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
        # 테이블 생성 시 필요한 모든 컬럼 정의
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT, 
                server_id TEXT, 
                access_token TEXT, 
                ip_addr TEXT, 
                PRIMARY KEY(user_id, server_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                server_id TEXT PRIMARY KEY, 
                role_id TEXT, 
                block_alt INTEGER DEFAULT 0, 
                block_vpn INTEGER DEFAULT 0
            )
        """)
        
        # 기존 테이블이 있을 경우 컬럼 추가 (Migration)
        try: conn.execute("ALTER TABLE settings ADD COLUMN block_alt INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE settings ADD COLUMN block_vpn INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN ip_addr TEXT")
        except: pass
        
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"로그인 완료: {self.user}")

    async def give_role_task(self, server_id: str, user_id: str, role_id: int):
        try:
            guild = self.get_guild(int(server_id))
            if guild:
                member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                role = guild.get_role(role_id)
                if member and role: await member.add_roles(role)
        except Exception as e:
            print(f"역할 지급 실패: {e}")

bot = RecoveryBot()

# 웹 스타일 (고급형 0-100% 로딩 애니메이션 포함)
BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    body {{ 
        background: #000; color: #fff; font-family: 'Inter', sans-serif; 
        margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh;
        background: radial-gradient(circle at center, #121212 0%, #000 100%);
    }}

    .card {{ 
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08); 
        padding: 40px 28px; border-radius: 30px; text-align: center;
        width: 88%; max-width: 320px; backdrop-filter: blur(25px); -webkit-backdrop-filter: blur(25px);
        display: flex; flex-direction: column; gap: 20px;
        box-shadow: 0 30px 60px rgba(0,0,0,0.6);
        animation: fadeIn 0.5s ease-out;
    }}

    .logo-container {{
        width: 60px; height: 60px; background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1); border-radius: 18px;
        margin: 0 auto; display: flex; align-items: center; justify-content: center;
        margin-bottom: 5px;
    }}

    .lock-icon {{ width: 26px; height: 26px; fill: #fff; }}

    h1 {{ font-size: 20px; font-weight: 700; margin: 0; letter-spacing: -0.5px; }}
    .desc {{ color: #777; font-size: 14px; margin: 0; line-height: 1.5; word-break: keep-all; }}

    .user-pill {{
        background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
        padding: 12px 16px; border-radius: 14px; display: flex; justify-content: space-between;
        align-items: center; font-size: 13px; font-weight: 500; margin-top: 5px;
    }}

    .btn-main {{
        background: #fff; color: #000; border: none; width: 100%; padding: 16px; border-radius: 14px;
        font-weight: 700; font-size: 15px; cursor: pointer; transition: all 0.3s ease;
        position: relative; overflow: hidden; display: flex; justify-content: center; align-items: center;
        height: 52px; text-decoration: none;
    }}

    .btn-main.loading {{
        background: rgba(255,255,255,0.1) !important; color: transparent !important; pointer-events: none;
    }}

    .progress-text {{
        position: absolute; width: 100%; height: 100%; display: flex;
        align-items: center; justify-content: center; color: #fff; font-size: 14px; z-index: 2;
    }}

    .progress-bar {{
        position: absolute; left: 0; top: 0; height: 100%; background: #fff; width: 0%;
        z-index: 1; transition: width 0.05s linear;
    }}

    .footer {{ color: #333; font-size: 9px; letter-spacing: 3px; font-weight: 700; text-transform: uppercase; margin-top: 5px; }}

    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    
    .cf-turnstile {{ 
        width: 100% !important; 
        max-width: 100%;
        overflow: hidden;
    }}
</style>
<script>
    function handleVerify(event) {{
        event.preventDefault();
        const btn = document.getElementById('submit-btn');
        const form = document.getElementById('verify-form');
        
        btn.classList.add('loading');
        
        let progress = 0;
        const bar = document.createElement('div');
        bar.className = 'progress-bar';
        btn.appendChild(bar);
        
        const text = document.createElement('div');
        text.className = 'progress-text';
        btn.appendChild(text);

        const interval = setInterval(() => {{
            progress += Math.floor(Math.random() * 4) + 1;
            if (progress >= 100) {{
                progress = 100;
                clearInterval(interval);
                setTimeout(() => form.submit(), 300);
            }}
            bar.style.width = progress + '%';
            text.innerText = progress + '% 인증 처리 중...';
        }}, 40);
    }}
</script>
"""

LOCK_SVG = '<svg class="lock-icon" viewBox="0 0 24 24"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zM9 6c0-1.66 1.34-3 3-3s3 1.34 3 3v2H9V6zm9 14H6V10h12v10zm-6-3c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2z"/></svg>'

@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code = request.query_params.get("code")
    sid = request.query_params.get("state")
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={sid}"
    
    if not code:
        return f"""<html><head>{BASE_STYLE}</head><body>
        <div class="card">
            <div class="logo-container">{LOCK_SVG}</div>
            <h1>보안 확인</h1>
            <p class="desc">커뮤니티 가이드라인 준수 및<br>보안을 위해 계정을 연결해 주세요</p>
            <a href="{url}" class="btn-main">Discord 연결</a>
            <div class="footer">RESTORE PROTOCOL</div>
        </div></body></html>"""

    # 딕셔너리 생성 시 중괄호 하나만 사용하도록 수정
    async with aiohttp.ClientSession() as session:
        payload = {
            'client_id': CLIENT_ID, 
            'client_secret': CLIENT_SECRET, 
            'grant_type': 'authorization_code', 
            'code': code, 
            'redirect_uri': REDIRECT_URI
        }
        async with session.post('https://discord.com/api/v10/oauth2/token', data=payload) as r:
            res = await r.json()
            atk = res.get('access_token')
            if not atk: return "세션 오류: 다시 시도해 주세요."
            
            async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {atk}'}) as r2:
                u = await r2.json()
                return f"""<html><head>{BASE_STYLE}</head><body>
                <div class="card">
                    <div class="logo-container">{LOCK_SVG}</div>
                    <h1>보안 검사</h1>
                    <p class="desc">브라우저 무결성 및<br>부계정 여부를 확인 중입니다</p>
                    <div class="user-pill">
                        <span>{u.get('username')}</span>
                        <a href="{url}" style="color:#fff; text-decoration:none; font-weight:700;">변경</a>
                    </div>
                    <form id="verify-form" action="/verify" method="post" onsubmit="handleVerify(event)" style="display:flex; flex-direction:column; gap:20px;">
                        <input type="hidden" name="server_id" value="{sid}">
                        <input type="hidden" name="access_token" value="{atk}">
                        <input type="hidden" name="user_id" value="{u.get('id')}">
                        <div class="cf-turnstile" data-sitekey="{CF_TURNSTILE_SITE_KEY}" data-theme="dark"></div>
                        <button type="submit" id="submit-btn" class="btn-main">인증 완료</button>
                    </form>
                </div></body></html>"""

@app.post("/verify", response_class=HTMLResponse)
async def verify_post(request: Request, server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    f = await request.form()
    c = f.get("cf-turnstile-response")
    ip = request.headers.get("cf-connecting-ip") or request.client.host

    async with aiohttp.ClientSession() as session:
        v = {'secret': CF_TURNSTILE_SECRET_KEY, 'response': c}
        async with session.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=v) as resp:
            vr = await resp.json()
            if not vr.get("success"): return "캡차 인증에 실패했습니다."

            conn = sqlite3.connect('restore_user.db')
            cur = conn.cursor()
            cur.execute("SELECT role_id, block_alt FROM settings WHERE server_id = ?", (server_id,))
            st = cur.fetchone()
            
            if st and st[1] == 1:
                cur.execute("SELECT user_id FROM users WHERE server_id = ? AND ip_addr = ? AND user_id != ?", (server_id, ip, user_id))
                if cur.fetchone():
                    conn.close()
                    return "🚫 정책 위반: 동일 IP에서 다른 계정의 인증 내역이 존재합니다."

            conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (user_id, server_id, access_token, ip))
            conn.commit()
            if st and st[0]:
                asyncio.run_coroutine_threadsafe(bot.give_role_task(server_id, user_id, int(st[0])), bot.loop)
            conn.close()

            return f"""<html><head>{BASE_STYLE}</head><body>
            <div class="card">
                <div class="logo-container" style="background:#fff;">
                    <svg style="width:26px; height:26px; fill:#000;" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                </div>
                <h1>인증 성공</h1>
                <p class="desc">안전한 사용자로 확인되었습니다<br>이제 서버를 이용하실 수 있습니다</p>
                <div style="background:rgba(255,255,255,0.05); padding:16px; border-radius:14px; font-size:13px; border:1px solid rgba(255,255,255,0.1);">
                    Security Level: Trusted
                </div>
                <div class="footer">ACCESS GRANTED</div>
            </div></body></html>"""

@bot.tree.command(name="지급역할", description="인증 완료 시 지급할 역할을 설정합니다")
@app_commands.checks.has_permissions(administrator=True)
async def set_role(it: discord.Interaction, role: discord.Role):
    conn = sqlite3.connect('restore_user.db')
    conn.execute("INSERT OR REPLACE INTO settings (server_id, role_id) VALUES (?, ?)", (str(it.guild_id), str(role.id)))
    conn.commit()
    conn.close()
    await it.response.send_message(f"✅ 인증 완료 시 **{role.name}** 역할을 지급하도록 설정되었습니다.", ephemeral=True)

@bot.tree.command(name="인증제한", description="부계정 및 VPN 차단 설정을 관리합니다")
@app_commands.checks.has_permissions(administrator=True)
async def restrict_auth(it: discord.Interaction, 부계정_차단: bool, vpn_차단: bool):
    conn = sqlite3.connect('restore_user.db')
    conn.execute("""
        INSERT INTO settings (server_id, block_alt, block_vpn) VALUES (?, ?, ?)
        ON CONFLICT(server_id) DO UPDATE SET block_alt=excluded.block_alt, block_vpn=excluded.block_vpn
    """, (str(it.guild_id), 1 if 부계정_차단 else 0, 1 if vpn_차단 else 0))
    conn.commit()
    conn.close()
    await it.response.send_message(f"✅ 보안 설정 완료: 부계정 차단({부계정_차단}), VPN 차단({vpn_차단})", ephemeral=True)

def start_web():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="error")

if __name__ == "__main__":
    Thread(target=start_web, daemon=True).start()
    bot.run(TOKEN)

