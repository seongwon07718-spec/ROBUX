import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, uvicorn, asyncio, json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from threading import Thread
from datetime import datetime

# --- 설정 정보 (직접 수정) ---
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
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, ip_addr TEXT, PRIMARY KEY(user_id, server_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS settings (server_id TEXT PRIMARY KEY, role_id TEXT, block_alt INTEGER DEFAULT 0, block_vpn INTEGER DEFAULT 0)")
        conn.execute("CREATE TABLE IF NOT EXISTS invites (inviter_id TEXT, invite_code TEXT PRIMARY KEY, server_id TEXT, used_count INTEGER DEFAULT 0)")
        conn.execute("CREATE TABLE IF NOT EXISTS invite_logs (invite_code TEXT, joined_user_id TEXT, PRIMARY KEY(invite_code, joined_user_id))")
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"Bot Login: {self.user}")

    async def on_member_join(self, member):
        """입장 시 초대 코드 추적 및 로그 전송"""
        try:
            invites_list = await member.guild.invites()
            conn = sqlite3.connect('restore_user.db')
            cur = conn.cursor()
            
            for invite in invites_list:
                cur.execute("SELECT inviter_id FROM invites WHERE invite_code = ?", (invite.code,))
                row = cur.fetchone()
                if row:
                    inviter_id = row[0]
                    cur.execute("SELECT 1 FROM invite_logs WHERE invite_code = ? AND joined_user_id = ?", (invite.code, str(member.id)))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO invite_logs VALUES (?, ?)", (invite.code, str(member.id)))
                        cur.execute("UPDATE invites SET used_count = used_count + 1 WHERE invite_code = ?", (invite.code,))
                        conn.commit()
                        
                        if WEBHOOK_URL:
                            log_con = ui.Container()
                            log_con.accent_color = 0x00ff88
                            log_con.add_item(ui.TextDisplay("## 📥 초대 입장 성공"))
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

# --- 초대 링크 발급용 버튼 클래스 ---
class InviteButtonView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="링크 발급받기", style=discord.ButtonStyle.gray, custom_id="btn_get_invite", emoji="🔗")
    async def get_invite(self, it: discord.Interaction, button: ui.Button):
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

        invite = await it.channel.create_invite(max_age=0, max_uses=0, unique=True)
        cur.execute("INSERT INTO invites (inviter_id, invite_code, server_id) VALUES (?, ?, ?)", (str(it.user.id), invite.code, str(it.guild_id)))
        conn.commit()
        conn.close()

        con = ui.Container()
        con.accent_color = 0xffffff
        con.add_item(ui.TextDisplay("## 초대 링크 발급 완료"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay(f"본인만의 고유 초대 링크가 생성되었습니다.\n이 링크로 입장한 인원은 랭킹에 집계됩니다.\n\n`https://discord.gg/{invite.code}`"))
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

# --- 웹 UI 스타일 ---
BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; position: fixed; touch-action: none; background: #000; color: #fff; font-family: 'Inter', sans-serif; }}
    body {{ display: flex; justify-content: center; align-items: center; background: radial-gradient(circle at center, #1c1c1c 0%, #000 100%); }}
    .card {{ background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.08); padding: 40px 24px; border-radius: 34px; text-align: center; width: 82%; max-width: 310px; backdrop-filter: blur(30px); -webkit-backdrop-filter: blur(30px); display: flex; flex-direction: column; gap: 20px; box-shadow: 0 40px 120px rgba(0,0,0,0.85); }}
    .btn-main {{ background: rgba(255, 255, 255, 0.05); color: #fff; border: 1px solid rgba(255, 255, 255, 0.12); width: 100%; padding: 15px 0; border-radius: 14px; font-weight: 600; text-decoration: none; display: block; }}
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code, sid = request.query_params.get("code"), request.query_params.get("state")
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={sid}"
    if not code: return f"<html><head>{BASE_STYLE}</head><body><div class='card'><h1>Auth</h1><a href='{url}' class='btn-main'>Login</a></div></body></html>"
    async with aiohttp.ClientSession() as session:
        payload = {'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI}
        async with session.post('https://discord.com/api/v10/oauth2/token', data=payload) as r:
            atk = (await r.json()).get('access_token')
            async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {atk}'}) as r2:
                u = await r2.json()
                return f"""<html><head>{BASE_STYLE}</head><body><div class="card"><h1>Verify</h1><form action="/verify" method="post"><input type="hidden" name="server_id" value="{sid}"><input type="hidden" name="access_token" value="{atk}"><input type="hidden" name="user_id" value="{u.get('id')}"><div class="cf-turnstile" data-sitekey="{CF_TURNSTILE_SITE_KEY}" data-theme="dark"></div><button type="submit" class="btn-main">Verify</button></form></div></body></html>"""

@app.post("/verify", response_class=HTMLResponse)
async def verify_post(request: Request, server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    ip = request.headers.get("cf-connecting-ip") or request.client.host
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (user_id, server_id, access_token, ip))
    conn.commit()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as r:
            if r.status == 200: await bot.send_container_log(server_id, await r.json(), ip)
    conn.close()
    return "<html><head>{BASE_STYLE}</head><body><div class='card'><h1>Success</h1></div></body></html>"

# --- 커맨드 영역 ---

@bot.tree.command(name="링크발급", description="모든 유저가 사용할 수 있는 초대 링크 발급 컨테이너를 전송합니다")
@app_commands.checks.has_permissions(administrator=True)
async def send_invite_panel(it: discord.Interaction):
    con = ui.Container()
    con.accent_color = 0xffffff
    con.add_item(ui.TextDisplay("## 🔗 초대 링크 시스템"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(
        "아래 버튼을 눌러 본인만의 **고유 초대 링크**를 발급받으세요.\n"
        "이 링크로 유저를 초대하면 실시간 랭킹에 반영됩니다.\n\n"
        "-# 발급은 계정당 1회만 가능합니다."
    ))
    
    view = ui.LayoutView().add_item(con)
    # 버튼 추가
    await it.channel.send(view=view.add_item(InviteButtonView()))
    await it.response.send_message("초대 패널이 전송되었습니다.", ephemeral=True)

@bot.tree.command(name="초대랭킹", description="실시간 초대 랭킹 상위 10명을 확인합니다")
async def invite_ranking(it: discord.Interaction):
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    cur.execute("SELECT inviter_id, used_count FROM invites WHERE server_id = ? ORDER BY used_count DESC LIMIT 10", (str(it.guild_id),))
    rows = cur.fetchall()
    conn.close()
    
    rank_text = "아직 초대 데이터가 없습니다."
    if rows:
        rank_text = ""
        for i, (uid, count) in enumerate(rows, 1):
            rank_text += f"**{i}위** | <@{uid}> — `{count}명` 초대\n"

    con = ui.Container()
    con.accent_color = 0xffffff
    con.add_item(ui.TextDisplay("## 🏆 실시간 초대 랭킹"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(rank_text))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(f"-# 업데이트: {datetime.now().strftime('%H:%M:%S')}"))
    await it.response.send_message(view=ui.LayoutView().add_item(con))

@bot.tree.command(name="인증하기", description="인증하기 컨테이너를 전송합니다")
async def authenticate(it: discord.Interaction):
    res_con = ui.Container()
    res_con.accent_color = 0xffffff
    res_con.add_item(ui.TextDisplay("## 서버 인증"))
    res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    res_con.add_item(ui.TextDisplay("아래 버튼을 눌러 인증하셔야 이용이 가능합니다."))
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={it.guild_id}"
    auth_btn = ui.Button(label="인증하기", url=url, style=discord.ButtonStyle.link, emoji="✅")
    await it.channel.send(view=ui.LayoutView().add_item(res_con).add_item(auth_btn))
    await it.response.send_message("인증 버튼이 전송되었습니다.", ephemeral=True)

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="error")

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    bot.run(TOKEN)

