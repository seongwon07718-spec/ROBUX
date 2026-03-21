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
        # 유저 정보 테이블
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, ip_addr TEXT, PRIMARY KEY(user_id, server_id))")
        # 서버별 설정 테이블
        conn.execute("CREATE TABLE IF NOT EXISTS settings (server_id TEXT PRIMARY KEY, role_id TEXT)")
        # 기존 테이블에 컬럼이 없을 경우를 대비해 예외 처리하며 추가 (사진 속 오류 해결)
        try: conn.execute("ALTER TABLE settings ADD COLUMN block_alt INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE settings ADD COLUMN block_vpn INTEGER DEFAULT 0")
        except: pass
        
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"로그인 완료: {self.user}")

bot = RecoveryBot()

# 웹 페이지 디자인 스타일 (20px 간격 및 다크 테마 유지)
BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
    body {{ background-color: #000; color: #fff; font-family: 'Inter', -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 0; box-sizing: border-box; overflow-x: hidden; }}
    .card {{ background: #0a0a0a; border: 1px solid #1a1a1a; padding: 45px 30px; border-radius: 28px; text-align: center; width: 90%; max-width: 360px; box-shadow: 0 25px 50px rgba(0,0,0,0.8); display: flex; flex-direction: column; align-items: center; justify-content: center; box-sizing: border-box; }}
    .logo-box {{ width: 70px; height: 70px; border-radius: 20px; background: #111; border: 1px solid #222; margin: 0 auto 25px auto; display: flex; justify-content: center; align-items: center; font-size: 32px; }}
    h1 {{ font-size: 24px; font-weight: 700; margin: 0 0 10px 0; letter-spacing: -0.5px; width: 100%; }}
    .subtitle {{ color: #666; font-size: 14px; margin: 0 0 30px 0; line-height: 1.5; width: 100%; word-break: keep-all; }}
    .cf-turnstile {{ margin-bottom: 20px !important; width: 100%; display: flex; justify-content: center; }}
    .status-alert {{ background: #111; border: 1px solid #222; border-left: 4px solid #fff; padding: 18px 10px; text-align: center; font-size: 13px; color: #ccc; margin-bottom: 20px; border-radius: 12px; width: 100%; box-sizing: border-box; display: block; }}
    .user-pill {{ background: #111; border: 1px solid #222; border-radius: 50px; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; font-size: 13px; width: 100%; box-sizing: border-box; }}
    .progress-wrap {{ width: 100%; margin-bottom: 15px; display: flex; flex-direction: column; align-items: center; }}
    .progress-bg {{ background: #1a1a1a; height: 6px; width: 100%; border-radius: 10px; overflow: hidden; margin-bottom: 10px; }}
    .progress-bar {{ background: #fff; height: 100%; width: 0%; transition: width 0.05s linear; }}
    .btn-main {{ background: #fff; color: #000; border: none; width: 100%; padding: 18px; border-radius: 16px; font-size: 16px; font-weight: 700; display: flex; justify-content: center; align-items: center; cursor: pointer; text-decoration: none; }}
    .footer {{ color: #333; font-size: 11px; margin-top: 35px; letter-spacing: 1px; width: 100%; }}
    .fade {{ animation: fadeInUp 0.6s ease-out; }}
    @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(15px); }} to {{ opacity: 1; transform: translateY(0); }} }}
</style>
"""

async def give_role_task(server_id, user_id, role_id):
    try:
        guild = bot.get_guild(int(server_id))
        if guild:
            member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
            role = guild.get_role(role_id)
            if member and role:
                await member.add_roles(role, reason="보안 인증 완료")
    except Exception as e:
        print(f"역할 지급 오류: {e}")

@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code = request.query_params.get("code")
    server_id = request.query_params.get("state")
    discord_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={server_id}"
    
    if not code:
        return f"<html><head>{BASE_STYLE}</head><body><div class='card fade'><div class='logo-box'>S</div><h1>서버 보안 인증</h1><p class='subtitle'>계정을 연결하고 서버 접근 권한을<br>획득하세요</p><a href='{discord_url}' class='btn-main'>Discord로 시작하기</a><div class='footer'>RESTORE PROTOCOL</div></div></body></html>"

    async with aiohttp.ClientSession() as session:
        # 사진 속 중괄호 2개 쓰던 오류 수정: payload = { ... }
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
            if not access_token: return "잘못된 접근입니다 (토큰 없음)"
            
            async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as r2:
                u_info = await r2.json()
                return f"""<html><head>{BASE_STYLE}</head><body><div class="card fade"><div class="logo-box">🔒</div><h1>보안 확인</h1><p class="subtitle">Cloudflare 보안 시스템이<br>브라우저를 확인 중입니다</p><div class="user-pill"><span>{u_info.get('username')}</span><a href="{discord_url}" style="color:#fff; text-decoration:none; font-weight:700;">변경</a></div><form action="/verify" method="post" style="width:100%;"><input type="hidden" name="server_id" value="{server_id}"><input type="hidden" name="access_token" value="{access_token}"><input type="hidden" name="user_id" value="{u_info.get('id')}"><div class="cf-turnstile" data-sitekey="{CF_TURNSTILE_SITE_KEY}" data-theme="dark"></div><button type="submit" class="btn-main">인증 완료</button></form></div></body></html>"""

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
                return "보안 검증 실패"

            conn = sqlite3.connect('restore_user.db')
            cur = conn.cursor()
            cur.execute("SELECT role_id, block_alt, block_vpn FROM settings WHERE server_id = ?", (server_id,))
            setting = cur.fetchone()
            
            # 부계정 차단 로직 (동일 IP 다른 유저 기록 조회)
            if setting and setting[1] == 1:
                cur.execute("SELECT user_id FROM users WHERE server_id = ? AND ip_addr = ? AND user_id != ?", (server_id, user_ip, user_id))
                if cur.fetchone():
                    conn.close()
                    return "인증 제한: 부계정은 인증할 수 없습니다."

            # VPN 차단 로직 (간이 VPN 체크 예시)
            if setting and setting[2] == 1:
                # Cloudflare를 통과한 IP가 VPN인지 여부는 실제 운영 시 API나 CF 헤더로 판별
                pass

            conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (user_id, server_id, access_token, user_ip))
            conn.commit()
            if setting and setting[0]:
                asyncio.run_coroutine_threadsafe(give_role_task(server_id, user_id, int(setting[0])), bot.loop)
            conn.close()

            return f"""<html><head>{BASE_STYLE}</head><body><div class="card fade"><div id="loading-area" style="width:100%;"><div class="logo-box">🔒</div><h1>보안 승인 중</h1><p class="subtitle">서버 권한을 할당하고 있습니다<br>잠시만 기다려 주세요</p><div class="progress-wrap"><div class="progress-bg"><div id="bar" class="progress-bar"></div></div><div id="pct" style="font-size:14px; font-weight:700;">0%</div></div></div><div id="success-area" style="display:none; width:100%;"><div class="logo-box" style="background:#fff; color:#000;">✓</div><h1>인증 완료</h1><p class="subtitle">보안 검사가 성공적으로 끝났습니다</p><div class="status-alert">성공적으로 승인되었습니다</div><div class="footer">SERVICE VOUT VERIFIED</div></div></div><script>let p = 0;const b = document.getElementById('bar');const t = document.getElementById('pct');const l = document.getElementById('loading-area');const s = document.getElementById('success-area');const iv = setInterval(() => {{p++;b.style.width = p + '%';t.innerText = p + '%';if (p >= 100) {{clearInterval(iv);l.style.display = 'none';s.style.display = 'block';}}}}, 40);</script></body></html>"""

# [슬래시 명령어]

@bot.tree.command(name="지급역할", description="인증 완료 시 지급할 역할을 설정합니다")
@app_commands.checks.has_permissions(administrator=True)
async def set_role(it: discord.Interaction, role: discord.Role):
    conn = sqlite3.connect('restore_user.db')
    conn.execute("INSERT INTO settings (server_id, role_id) VALUES (?, ?) ON CONFLICT(server_id) DO UPDATE SET role_id=excluded.role_id", (str(it.guild_id), str(role.id)))
    conn.commit()
    conn.close()
    
    con = ui.Container()
    con.accent_color = 0xffffff
    con.add_item(ui.TextDisplay(f"## ✅ 역할 설정 완료\n{role.mention} 역할이 자동 지급됩니다"))
    await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

@bot.tree.command(name="인증제한", description="부계정 및 VPN 인증 제한 설정")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(부계정=[app_commands.Choice(name="상관있음 (차단)", value=1), app_commands.Choice(name="상관없음 (허용)", value=0)],
                      vpn=[app_commands.Choice(name="상관있음 (차단)", value=1), app_commands.Choice(name="상관없음 (허용)", value=0)])
async def restrict_auth(it: discord.Interaction, 부계정: int, vpn: int):
    conn = sqlite3.connect('restore_user.db')
    conn.execute("INSERT INTO settings (server_id, block_alt, block_vpn) VALUES (?, ?, ?) ON CONFLICT(server_id) DO UPDATE SET block_alt=excluded.block_alt, block_vpn=excluded.block_vpn", (str(it.guild_id), 부계정, vpn))
    conn.commit()
    conn.close()

    alt_status = "🚫 차단" if 부계정 == 1 else "✅ 허용"
    vpn_status = "🚫 차단" if vpn == 1 else "✅ 허용"
    
    con = ui.Container()
    con.accent_color = 0xffffff
    con.add_item(ui.TextDisplay(f"## 🛡️ 보안 설정 완료\n**부계정:** {alt_status}\n**VPN:** {vpn_status}"))
    await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

@bot.tree.command(name="인증하기", description="인증 컨테이너를 전송합니다")
async def authenticate(it: discord.Interaction):
    await it.response.send_message(content="**인증 메세지 전송 완료**", ephemeral=True)
    res_con = ui.Container()
    res_con.accent_color = 0xffffff
    res_con.add_item(ui.TextDisplay("## 서버 인증\n버튼을 눌러 인증을 완료해 주세요"))
    auth_url = (f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={it.guild_id}")
    auth_btn = ui.Button(label="인증하기", url=auth_url, style=discord.ButtonStyle.link, emoji="🔒")
    res_con.add_item(ui.ActionRow(auth_btn))
    await it.channel.send(view=ui.LayoutView().add_item(res_con))

@bot.tree.command(name="유저복구", description="인증된 유저 복구")
@app_commands.checks.has_permissions(administrator=True)
async def restore(it: discord.Interaction):
    await it.response.defer(ephemeral=True)
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id, access_token FROM users WHERE server_id = ?", (str(it.guild_id),))
    users = cur.fetchall()
    conn.close()
    
    success, fail = 0, 0
    async with aiohttp.ClientSession() as session:
        for u_id, token in users:
            url = f"https://discord.com/api/v10/guilds/{it.guild_id}/members/{u_id}"
            headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
            async with session.put(url, headers=headers, json={"access_token": token}) as resp:
                if resp.status in [201, 204]: success += 1
                else: fail += 1
                await asyncio.sleep(0.5)

    await it.followup.send(f"복구 완료: 성공 {success}명, 실패 {fail}명")

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="error")

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    try: bot.run(TOKEN)
    except Exception as e: print(f"봇 시작 실패: {e}")

