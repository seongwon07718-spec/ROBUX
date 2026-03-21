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
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, ip_addr TEXT, PRIMARY KEY(user_id, server_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS settings (server_id TEXT PRIMARY KEY, role_id TEXT, block_alt INTEGER DEFAULT 0, block_vpn INTEGER DEFAULT 0)")
        try: conn.execute("ALTER TABLE settings ADD COLUMN block_alt INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN ip_addr TEXT")
        except: pass
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"Server is Ready: {self.user}")

    async def give_role_task(self, server_id: str, user_id: str, role_id: int):
        try:
            guild = self.get_guild(int(server_id))
            if guild:
                member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                role = guild.get_role(role_id)
                if member and role: await member.add_roles(role)
        except: pass

bot = RecoveryBot()

# 웹 스타일 (고급 투명 디자인 + 0~100% 로딩 스크립트)
BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    body {{ 
        background: #000; color: #fff; font-family: 'Inter', sans-serif; 
        margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh;
        background-image: radial-gradient(circle at center, #111 0%, #000 100%);
    }}

    .card {{ 
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.1); 
        padding: 40px 32px; border-radius: 28px; text-align: center;
        width: 85%; max-width: 340px; backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
        display: flex; flex-direction: column; gap: 20px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    }}

    .logo-container {{
        width: 64px; height: 64px; background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1); border-radius: 18px;
        margin: 0 auto; display: flex; align-items: center; justify-content: center;
    }}

    .lock-icon {{ width: 28px; height: 28px; fill: #fff; }}

    h1 {{ font-size: 20px; font-weight: 700; margin: 0; letter-spacing: -0.5px; }}
    .desc {{ color: #888; font-size: 14px; margin: 0; line-height: 1.5; word-break: keep-all; }}

    .user-pill {{
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
        padding: 12px 16px; border-radius: 14px; display: flex; justify-content: space-between;
        align-items: center; font-size: 13px;
    }}

    /* 캡챠와 버튼 크기 통일 */
    .cf-turnstile {{ 
        width: 100% !important; 
        display: flex; justify-content: center;
    }}

    .btn-container {{ position: relative; width: 100%; }}

    .btn-main {{
        background: #fff; color: #000; border: none; width: 100%; padding: 16px; border-radius: 14px;
        font-weight: 700; font-size: 15px; cursor: pointer; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        display: flex; justify-content: center; align-items: center; overflow: hidden; position: relative;
    }}

    .btn-main.loading {{
        background: rgba(255,255,255,0.1); color: #fff; pointer-events: none;
    }}

    .progress-fill {{
        position: absolute; left: 0; top: 0; height: 100%; background: #fff; width: 0%;
        transition: width 0.1s linear; z-index: 0;
    }}

    .btn-text {{ position: relative; z-index: 1; }}

    .footer {{ color: #333; font-size: 10px; letter-spacing: 2px; font-weight: 600; text-transform: uppercase; }}

    .fade-in {{ animation: fadeIn 0.5s ease-out forwards; }}
    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
</style>
<script>
    function startLoading(event) {{
        event.preventDefault();
        const btn = document.getElementById('submit-btn');
        const text = document.getElementById('btn-text');
        const form = document.getElementById('verify-form');
        
        btn.classList.add('loading');
        
        let progress = 0;
        const interval = setInterval(() => {{
            progress += Math.floor(Math.random() * 5) + 2;
            if (progress >= 100) {{
                progress = 100;
                clearInterval(interval);
                setTimeout(() => form.submit(), 200);
            }}
            text.innerText = "Processing... " + progress + "%";
            btn.style.background = `linear-gradient(90deg, #fff ${{progress}}%, rgba(255,255,255,0.1) ${{progress}}%)`;
            // 텍스트 색상 반전 처리
            if(progress > 50) btn.style.color = "#000";
        }}, 50);
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
        <div class="card fade-in">
            <div class="logo-container">{LOCK_SVG}</div>
            <h1>서버 보안 인증</h1>
            <p class="desc">커뮤니티 보호를 위해<br>계정 연결이 필요합니다</p>
            <a href="{url}" class="btn-main">Discord 연결하기</a>
            <div class="footer">RESTORE SYSTEM</div>
        </div></body></html>"""

    async with aiohttp.ClientSession() as session:
        p = {{'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI}}
        async with session.post('https://discord.com/api/v10/oauth2/token', data=p) as r:
            res = await r.json()
            atk = res.get('access_token')
            if not atk: return "인증 세션이 만료되었습니다."
            
            async with session.get('https://discord.get/api/v10/users/@me', headers={{'Authorization': f'Bearer {{atk}}'}}) as r2:
                u = await r2.json()
                return f"""<html><head>{BASE_STYLE}</head><body>
                <div class="card fade-in">
                    <div class="logo-container">{LOCK_SVG}</div>
                    <h1>보안 검증</h1>
                    <p class="desc">인증을 완료하여<br>서버 접근 권한을 획득하세요</p>
                    <div class="user-pill">
                        <span>{u.get('username')}</span>
                        <a href="{url}" style="color:#fff; text-decoration:none; font-weight:700;">변경</a>
                    </div>
                    <form id="verify-form" action="/verify" method="post" onsubmit="startLoading(event)" style="display:flex; flex-direction:column; gap:20px;">
                        <input type="hidden" name="server_id" value="{sid}">
                        <input type="hidden" name="access_token" value="{atk}">
                        <input type="hidden" name="user_id" value="{u.get('id')}">
                        <div class="cf-turnstile" data-sitekey="{CF_TURNSTILE_SITE_KEY}" data-theme="dark" data-width="fill"></div>
                        <button type="submit" id="submit-btn" class="btn-main">
                            <span id="btn-text">인증 완료</span>
                        </button>
                    </form>
                </div></body></html>"""

@app.post("/verify", response_class=HTMLResponse)
async def verify_post(request: Request, server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    f = await request.form()
    c = f.get("cf-turnstile-response")
    ip = request.headers.get("cf-connecting-ip") or request.client.host

    async with aiohttp.ClientSession() as session:
        v = {{'secret': CF_TURNSTILE_SECRET_KEY, 'response': c}}
        async with session.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=v) as resp:
            vr = await resp.json()
            if not vr.get("success"): return "보안 검증 실패"

            conn = sqlite3.connect('restore_user.db')
            cur = conn.cursor()
            cur.execute("SELECT role_id, block_alt FROM settings WHERE server_id = ?", (server_id,))
            st = cur.fetchone()
            
            if st and st[1] == 1:
                cur.execute("SELECT user_id FROM users WHERE server_id = ? AND ip_addr = ? AND user_id != ?", (server_id, ip, user_id))
                if cur.fetchone():
                    conn.close()
                    return "🚫 보안 정책: 동일 IP의 중복 계정입니다."

            conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (user_id, server_id, access_token, ip))
            conn.commit()
            if st and st[0]:
                asyncio.run_coroutine_threadsafe(bot.give_role_task(server_id, user_id, int(st[0])), bot.loop)
            conn.close()

            return f"""<html><head>{BASE_STYLE}</head><body>
            <div class="card fade-in">
                <div class="logo-container" style="background:#fff;">
                    <svg style="width:28px; height:28px; fill:#000;" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                </div>
                <h1>인증 성공</h1>
                <p class="desc">모든 검증이 완료되었습니다<br>서버로 돌아가 확인해 주세요</p>
                <div style="background:rgba(255,255,255,0.05); padding:16px; border-radius:14px; font-size:13px; border:1px solid rgba(255,255,255,0.1);">
                    신뢰 등급: Verified
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
    await it.response.send_message(f"✅ 인증 시 **{role.name}** 역할을 지급합니다.", ephemeral=True)

@bot.tree.command(name="인증하기", description="인증 메세지를 전송합니다")
async def send_auth(it: discord.Interaction):
    embed = discord.Embed(title="🔒 보안 인증", description="아래 버튼을 클릭하여 서버 이용 권한을 획득하세요.", color=0xffffff)
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={it.guild_id}"
    view = ui.View()
    view.add_item(ui.Button(label="인증 시작하기", url=url, style=discord.ButtonStyle.link))
    await it.channel.send(embed=embed, view=view)

def start_web():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="error")

if __name__ == "__main__":
    Thread(target=start_web, daemon=True).start()
    bot.run(TOKEN)

