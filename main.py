import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, uvicorn, asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from threading import Thread
from datetime import datetime

# --- 설정 정보 (코드에서 직접 수정) ---
TOKEN = "YOUR_BOT_TOKEN_HERE"
CLIENT_ID = "1482041261111382066"
CLIENT_SECRET = "2IbFgl910fy8yd6WDCAvBGj9Asa-BsQi"
REDIRECT_URI = "https://restore.v0ut.com"
WEBHOOK_URL = "YOUR_WEBHOOK_URL_HERE" # 인증 로그 웹훅

CF_TURNSTILE_SITE_KEY = "0x4AAAAAACt7wUkh4DATyGf_"
CF_TURNSTILE_SECRET_KEY = "0x4AAAAAACt7wYg5nw0sXHF4URhhszJq_EA"

app = FastAPI()
intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        # DB 초기화 및 누락 컬럼 자동 추가 (OperationalError 방지)
        conn = sqlite3.connect('restore_user.db')
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, ip_addr TEXT, PRIMARY KEY(user_id, server_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS settings (server_id TEXT PRIMARY KEY, role_id TEXT, block_alt INTEGER DEFAULT 0, block_vpn INTEGER DEFAULT 0)")
        
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(settings)")
        cols = [c[1] for c in cursor.fetchall()]
        for col in ['block_alt', 'block_vpn']:
            if col not in cols: conn.execute(f"ALTER TABLE settings ADD COLUMN {col} INTEGER DEFAULT 0")
        
        cursor.execute("PRAGMA table_info(users)")
        if 'ip_addr' not in [c[1] for c in cursor.fetchall()]:
            conn.execute("ALTER TABLE users ADD COLUMN ip_addr TEXT")
            
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"Logged in: {self.user}")

    async def send_container_log(self, server_id: str, user_data: dict, ip: str):
        """텍스트 없이 오직 ui.Container만 전송"""
        conn = sqlite3.connect('restore_user.db')
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE server_id = ?", (server_id,))
        total_count = cur.fetchone()[0]
        conn.close()

        if WEBHOOK_URL:
            # 이미지와 동일한 ui.Container 구조 생성
            log_con = ui.Container()
            log_con.accent_color = 0xffffff
            log_con.add_item(ui.TextDisplay("## ✅ 인증 성공"))
            log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_con.add_item(ui.TextDisplay(
                f"**{total_count}명**의 사용자가 인증했습니다.\n"
                f"시간 | {now}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<@{user_data['id']}> 님이 인증에 성공했습니다.\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"-# © 2025 Guild Restore. All rights reserved."
            ))
            
            # LayoutView를 사용하여 페이로드 추출
            view = ui.LayoutView().add_item(log_con)
            
            async with aiohttp.ClientSession() as session:
                payload = {"components": view.to_dict()["components"]}
                await session.post(WEBHOOK_URL, json=payload)

bot = RecoveryBot()

# --- 웹 UI 스타일 ---
BASE_STYLE = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    body { margin: 0; background: #000; color: #fff; font-family: 'Inter', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; overflow: hidden; }
    .card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); padding: 40px 30px; border-radius: 30px; width: 85%; max-width: 320px; text-align: center; }
    .btn-main { background: #fff; color: #000; border: none; width: 100%; border-radius: 12px; font-weight: 700; height: 50px; cursor: pointer; display: flex; align-items: center; justify-content: center; text-decoration: none; margin-top: 15px; }
    .user-pill { background: rgba(255,255,255,0.05); padding: 10px; border-radius: 10px; margin-bottom: 15px; font-size: 13px; color: #aaa; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    sid = request.query_params.get("state")
    code = request.query_params.get("code")
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={sid}"
    
    if not code:
        return f"<html><head>{BASE_STYLE}</head><body><div class='card'><h1>Security</h1><a href='{url}' class='btn-main'>Connect</a></div></body></html>"

    async with aiohttp.ClientSession() as session:
        data = {'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI}
        async with session.post('https://discord.com/api/v10/oauth2/token', data=data) as r:
            token = (await r.json()).get('access_token')
            async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {token}'}) as ur:
                u = await ur.json()
                return f"""<html><head>{BASE_STYLE}</head><body><div class="card">
                    <h1>Verify</h1><div class="user-pill">{u.get('username')}</div>
                    <form action="/verify" method="post">
                        <input type="hidden" name="server_id" value="{sid}"><input type="hidden" name="access_token" value="{token}"><input type="hidden" name="user_id" value="{u.get('id')}">
                        <div class="cf-turnstile" data-sitekey="{CF_TURNSTILE_SITE_KEY}" data-theme="dark"></div>
                        <button type="submit" class="btn-main">Verify Now</button>
                    </form></div></body></html>"""

@app.post("/verify", response_class=HTMLResponse)
async def verify_post(request: Request, server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    ip = request.headers.get("cf-connecting-ip") or request.client.host
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (user_id, server_id, access_token, ip))
    cur.execute("SELECT role_id FROM settings WHERE server_id = ?", (server_id,))
    st = cur.fetchone()
    conn.commit()
    conn.close()
    
    async with aiohttp.ClientSession() as session:
        async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as r:
            if r.status == 200: await bot.send_container_log(server_id, await r.json(), ip)
    
    if st and st[0]: asyncio.run_coroutine_threadsafe(bot.give_role_task(server_id, user_id, int(st[0])), bot.loop)
    return "<html><head>{BASE_STYLE}</head><body><div class='card'><h1>Success</h1></div></body></html>"

# --- 커맨드 영역 (오직 ui.Container만 사용) ---
@bot.tree.command(name="지급역할", description="인증 역할 설정")
@app_commands.checks.has_permissions(administrator=True)
async def set_role(it: discord.Interaction, role: discord.Role):
    conn = sqlite3.connect('restore_user.db')
    conn.execute("INSERT OR REPLACE INTO settings (server_id, role_id) VALUES (?, ?)", (str(it.guild_id), str(role.id)))
    conn.commit()
    conn.close()

    con = ui.Container()
    con.accent_color = 0xffffff
    con.add_item(ui.TextDisplay("## 역할 설정 완료"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(f"인증 완료 시 {role.mention} 역할이 자동 지급됩니다."))
    
    await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

@bot.tree.command(name="인증하기", description="인증 컨테이너 전송")
@app_commands.checks.has_permissions(administrator=True)
async def send_auth(it: discord.Interaction):
    con = ui.Container()
    con.accent_color = 0xffffff
    con.add_item(ui.TextDisplay("## 보안 인증 시스템"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay("서버 이용을 위해 아래 버튼을 눌러 인증을 진행해 주세요."))
    
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={it.guild_id}"
    btn = ui.Button(label="인증하기", url=url, style=discord.ButtonStyle.link)
    
    await it.response.send_message(view=ui.LayoutView().add_item(con).add_item(btn))

def start_web():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="error")

if __name__ == "__main__":
    Thread(target=start_web, daemon=True).start()
    bot.run(TOKEN)

