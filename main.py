import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, uvicorn, asyncio, json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from threading import Thread

# 설정 정보
TOKEN = "YOUR_BOT_TOKEN_HERE" 
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
        try: conn.execute("ALTER TABLE settings ADD COLUMN block_alt INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN ip_addr TEXT")
        except: pass
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"Bot Login: {self.user}")

    async def give_role_task(self, server_id: str, user_id: str, role_id: int):
        try:
            guild = self.get_guild(int(server_id))
            if guild:
                member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                role = guild.get_role(role_id)
                if member and role: await member.add_roles(role)
        except: pass

bot = RecoveryBot()

# 웹 스타일 (스크롤 및 터치 고정 + 정밀 크기 동기화)
BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* 화면 고정 설정 */
    html, body {{ 
        margin: 0; padding: 0; width: 100%; height: 100%; 
        overflow: hidden; /* 스크롤 차단 */
        position: fixed; /* 화면 고정 */
        touch-action: none; /* 터치 드래그 방지 */
        background: #000; color: #fff; font-family: 'Inter', sans-serif; 
    }}

    body {{ 
        display: flex; justify-content: center; align-items: center;
        background: radial-gradient(circle at center, #1c1c1c 0%, #000 100%);
    }}

    .card {{ 
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08); 
        padding: 42px 28px; border-radius: 36px; text-align: center;
        width: 80%; max-width: 300px; backdrop-filter: blur(35px); -webkit-backdrop-filter: blur(35px);
        display: flex; flex-direction: column; gap: 20px;
        box-shadow: 0 50px 150px rgba(0,0,0,0.9);
        animation: fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1);
        z-index: 10;
    }}

    .logo-box {{
        width: 56px; height: 56px; background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08); border-radius: 18px;
        margin: 0 auto; display: flex; align-items: center; justify-content: center;
    }}

    .lock-icon {{ width: 24px; height: 24px; fill: #fff; opacity: 0.8; }}

    h1 {{ font-size: 19px; font-weight: 700; margin: 0; letter-spacing: -0.9px; color: rgba(255,255,255,0.95); }}
    .desc {{ color: #666; font-size: 13px; margin: 0; line-height: 1.6; word-break: keep-all; }}

    .user-pill {{
        background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);
        padding: 11px 16px; border-radius: 14px; display: flex; justify-content: space-between;
        align-items: center; font-size: 12.5px; color: #888;
    }}

    .form-container {{
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 14px;
        align-items: center;
    }}

    /* 캡챠와 버튼의 너비를 정밀하게 일치 */
    .cf-turnstile {{
        width: 100% !important;
        display: block !important;
    }}

    .btn-main {{
        background: rgba(255, 255, 255, 0.03); 
        color: #fff; border: 1px solid rgba(255, 255, 255, 0.1);
        width: 100%; border-radius: 14px;
        font-weight: 600; font-size: 14.5px; cursor: pointer; transition: all 0.4s ease;
        position: relative; overflow: hidden; display: flex; justify-content: center; align-items: center;
        height: 54px; text-decoration: none; box-sizing: border-box;
    }}

    .btn-main:hover {{ background: rgba(255, 255, 255, 0.06); border-color: rgba(255, 255, 255, 0.15); }}

    .progress-bar {{
        position: absolute; left: 0; top: 0; height: 100%; 
        background: rgba(255, 255, 255, 0.1); width: 0%;
        z-index: 1; transition: width 0.1s ease-out;
    }}

    .btn-text {{ position: relative; z-index: 2; letter-spacing: 0.1px; color: rgba(255,255,255,0.9); }}

    .footer {{ color: #1a1a1a; font-size: 9px; letter-spacing: 4px; font-weight: 900; text-transform: uppercase; margin-top: 4px; pointer-events: none; }}

    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(30px); }} to {{ opacity: 1; transform: translateY(0); }} }}
</style>
<script>
    // 모바일에서 터치 무브를 차단하여 고정성 강화
    document.addEventListener('touchmove', function(e) {{ e.preventDefault(); }}, {{ passive: false }});

    function handleVerify(event) {{
        event.preventDefault();
        const btn = document.getElementById('submit-btn');
        const text = document.getElementById('btn-txt');
        const form = document.getElementById('verify-form');
        
        btn.style.pointerEvents = 'none';
        
        const bar = document.createElement('div');
        bar.className = 'progress-bar';
        btn.appendChild(bar);
        
        let progress = 0;
        const interval = setInterval(() => {{
            progress += Math.random() * 3 + 0.5;
            if (progress >= 100) {{
                progress = 100;
                clearInterval(interval);
                text.innerText = "SUCCESS 100%";
                setTimeout(() => form.submit(), 300);
            }}
            bar.style.width = progress + '%';
            text.innerText = "VERIFYING... " + Math.floor(progress) + "%";
        }}, 35);
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
            <div class="logo-box">{LOCK_SVG}</div>
            <h1>보안 시스템 작동</h1>
            <p class="desc">정상적인 사용자 확인을 위해<br>계정 연결 절차를 시작합니다</p>
            <a href="{url}" class="btn-main"><span class="btn-text">계정 연결</span></a>
            <div class="footer">RESTORE SECURE</div>
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
            res = await r.json()
            atk = res.get('access_token')
            if not atk: return "세션 오류. 다시 접속해 주세요."
            
            async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {atk}'}) as r2:
                u = await r2.json()
                return f"""<html><head>{BASE_STYLE}</head><body>
                <div class="card">
                    <div class="logo-box">{LOCK_SVG}</div>
                    <h1>보안 검사</h1>
                    <p class="desc">연결된 계정을 확인하고<br>아래 인증을 마무리해 주세요</p>
                    <div class="user-pill">
                        <span>{u.get('username')}</span>
                        <a href="{url}" style="color:#fff; text-decoration:none; font-weight:700; font-size:10px; opacity:0.5;">변경</a>
                    </div>
                    <form id="verify-form" action="/verify" method="post" onsubmit="handleVerify(event)" class="form-container">
                        <input type="hidden" name="server_id" value="{sid}">
                        <input type="hidden" name="access_token" value="{atk}">
                        <input type="hidden" name="user_id" value="{u.get('id')}">
                        <div class="cf-turnstile" data-sitekey="{CF_TURNSTILE_SITE_KEY}" data-theme="dark" data-width="flexible"></div>
                        <button type="submit" id="submit-btn" class="btn-main">
                            <span id="btn-txt" class="btn-text">인증 완료</span>
                        </button>
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
            if not vr.get("success"): return "인증 응답 오류"

            conn = sqlite3.connect('restore_user.db')
            cur = conn.cursor()
            cur.execute("SELECT role_id, block_alt FROM settings WHERE server_id = ?", (server_id,))
            st = cur.fetchone()
            
            if st and st[1] == 1:
                cur.execute("SELECT user_id FROM users WHERE server_id = ? AND ip_addr = ? AND user_id != ?", (server_id, ip, user_id))
                if cur.fetchone():
                    conn.close()
                    return "🚫 보안 위반: 중복 접속이 제한된 IP입니다."

            conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (user_id, server_id, access_token, ip))
            conn.commit()
            if st and st[0]:
                asyncio.run_coroutine_threadsafe(bot.give_role_task(server_id, user_id, int(st[0])), bot.loop)
            conn.close()

            return f"""<html><head>{BASE_STYLE}</head><body>
            <div class="card">
                <div class="logo-box" style="background:#fff;">
                    <svg style="width:24px; height:24px; fill:#000;" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                </div>
                <h1>승인 완료</h1>
                <p class="desc">사용자 인증에 성공했습니다<br>이제 서버를 이용할 수 있습니다</p>
                <div style="background:rgba(255,255,255,0.03); padding:14px; border-radius:14px; font-size:11px; border:1px solid rgba(255,255,255,0.06);">
                    System: <span style="color:#00ff88;">Verified</span>
                </div>
                <div class="footer">ACCESS GRANTED</div>
            </div></body></html>"""

def start_web():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="error")

if __name__ == "__main__":
    Thread(target=start_web, daemon=True).start()
    bot.run(TOKEN)

