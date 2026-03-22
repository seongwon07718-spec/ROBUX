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

# 입장 로그 및 인증 로그가 전송될 웹훅 URL
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
        # 회원가입 및 설정 테이블
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, ip_addr TEXT, PRIMARY KEY(user_id, server_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS settings (server_id TEXT PRIMARY KEY, role_id TEXT)")
        # 초대 관련 테이블
        conn.execute("CREATE TABLE IF NOT EXISTS invites (inviter_id TEXT, invite_code TEXT PRIMARY KEY, server_id TEXT, used_count INTEGER DEFAULT 0)")
        conn.execute("CREATE TABLE IF NOT EXISTS invite_logs (invite_code TEXT, joined_user_id TEXT, PRIMARY KEY(invite_code, joined_user_id))")
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"Logged in as {self.user}")

    async def on_member_join(self, member):
        """유저 입장 시 어떤 초대 코드로 들어왔는지 판별"""
        try:
            invites_list = await member.guild.invites()
            conn = sqlite3.connect('restore_user.db')
            cur = conn.cursor()
            
            for invite in invites_list:
                cur.execute("SELECT inviter_id FROM invites WHERE invite_code = ?", (invite.code,))
                row = cur.fetchone()
                if row:
                    inviter_id = row[0]
                    # 중복 방지 (이미 로그가 있는지 확인)
                    cur.execute("SELECT 1 FROM invite_logs WHERE invite_code = ? AND joined_user_id = ?", (invite.code, str(member.id)))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO invite_logs VALUES (?, ?)", (invite.code, str(member.id)))
                        cur.execute("UPDATE invites SET used_count = used_count + 1 WHERE invite_code = ?", (invite.code,))
                        conn.commit()
                        
                        # 웹훅으로 초대 로그 전송
                        if WEBHOOK_URL:
                            log_con = ui.Container()
                            log_con.accent_color = 0x00ff88
                            log_con.add_item(ui.TextDisplay("## 📥 초대 입장 성공"))
                            log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                            log_con.add_item(ui.TextDisplay(
                                f"**초대자:** <@{inviter_id}>\n"
                                f"**입장자:** <@{member.id}> (`{member.name}`)\n"
                                f"**초대 코드:** `{invite.code}`"
                            ))
                            view = ui.LayoutView().add_item(log_con)
                            async with aiohttp.ClientSession() as session:
                                await session.post(WEBHOOK_URL, json={"components": view.to_dict()["components"]})
            conn.close()
        except Exception as e:
            print(f"Join Error: {e}")

bot = RecoveryBot()

# --- 초대 링크 발급용 컨테이너 레이아웃 ---
class InvitePanel(ui.LayoutView):
    def __init__(self):
        super().__init__()
        # 컨테이너 생성 및 아이템 추가
        self.container = ui.Container()
        self.container.accent_color = 0xffffff
        self.container.add_item(ui.TextDisplay("## 🔗 초대 링크 발급"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(
            "아래 버튼을 눌러 본인만의 고유 링크를 생성하세요.\n"
            "생성된 링크로 유저가 들어오면 랭킹에 반영됩니다.\n\n"
            "-# 링크는 인당 1개만 발급 가능합니다."
        ))

        # 버튼 생성 및 콜백 설정
        self.issue_btn = ui.Button(label="링크 발급받기", style=discord.ButtonStyle.gray, emoji="✨")
        self.issue_btn.callback = self.issue_callback
        
        # 버튼을 액션로우에 담아 컨테이너에 추가
        self.container.add_item(ui.ActionRow(self.issue_btn))
        self.add_item(self.container)

    async def issue_callback(self, it: discord.Interaction):
        conn = sqlite3.connect('restore_user.db')
        cur = conn.cursor()
        cur.execute("SELECT invite_code FROM invites WHERE inviter_id = ? AND server_id = ?", (str(it.user.id), str(it.guild_id)))
        row = cur.fetchone()
        
        if row:
            # 이미 발급받은 경우
            err_con = ui.Container()
            err_con.accent_color = 0xff4444
            err_con.add_item(ui.TextDisplay("## 발급 실패"))
            err_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            err_con.add_item(ui.TextDisplay(f"이미 링크를 발급받으셨습니다.\n내 링크: `https://discord.gg/{row[0]}`"))
            conn.close()
            return await it.response.send_message(view=ui.LayoutView().add_item(err_con), ephemeral=True)

        # 새로운 초대 링크 생성 (영구, 무제한)
        try:
            invite = await it.channel.create_invite(max_age=0, max_uses=0, unique=True, reason=f"User {it.user.id} individual invite")
            cur.execute("INSERT INTO invites (inviter_id, invite_code, server_id) VALUES (?, ?, ?)", (str(it.user.id), invite.code, str(it.guild_id)))
            conn.commit()
            
            sc_con = ui.Container()
            sc_con.accent_color = 0x5865F2
            sc_con.add_item(ui.TextDisplay("## 발급 완료"))
            sc_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            sc_con.add_item(ui.TextDisplay(f"본인만의 초대 링크가 생성되었습니다.\n\n`https://discord.gg/{invite.code}`"))
            await it.response.send_message(view=ui.LayoutView().add_item(sc_con), ephemeral=True)
        except Exception as e:
            await it.response.send_message(f"오류가 발생했습니다: {e}", ephemeral=True)
        finally:
            conn.close()

# --- 웹 대시보드 스타일 및 로직 (이미지 참고) ---
BASE_STYLE = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    body { margin: 0; padding: 0; background: #000; color: #fff; font-family: 'Inter', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; }
    .card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); padding: 40px 24px; border-radius: 34px; text-align: center; width: 85%; max-width: 320px; backdrop-filter: blur(20px); }
    .btn-main { background: #fff; color: #000; width: 100%; padding: 16px; border-radius: 16px; font-weight: 700; border: none; cursor: pointer; display: block; text-decoration: none; margin-top: 20px; }
    .user-box { background: rgba(255,255,255,0.05); padding: 12px; border-radius: 12px; font-size: 14px; margin: 15px 0; display: flex; justify-content: space-between; align-items: center; }
    .footer { font-size: 10px; color: #444; margin-top: 30px; letter-spacing: 2px; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code, sid = request.query_params.get("code"), request.query_params.get("state")
    if not code:
        url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={sid}"
        return f"<html><head>{BASE_STYLE}</head><body><div class='card'><h1>보안 확인</h1><p style='color:#777; font-size:14px;'>인증을 위해 로그인이 필요합니다</p><a href='{url}' class='btn-main'>Discord 로그인</a></div></body></html>"
    
    # 딕셔너리 처리 오류 방지를 위해 f-string 대신 직접 처리
    async with aiohttp.ClientSession() as session:
        data = {'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI}
        async with session.post('https://discord.com/api/v10/oauth2/token', data=data) as r:
            token_res = await r.json()
            atk = token_res.get('access_token')
            if not atk: return "인증 세션이 만료되었습니다."
            async with session.get('https://discord.get/api/v10/users/@me', headers={'Authorization': f'Bearer {atk}'}) as r2:
                u = await r2.json()
                return f"""
                <html><head>{BASE_STYLE}</head><body>
                <div class="card">
                    <h1 style="margin-bottom:8px;">보안 확인</h1>
                    <p style="color:#777; font-size:13px; margin-bottom:20px;">브라우저를 확인 중입니다</p>
                    <div class="user-box"><span>{u.get('username')}</span><span style="color:#5865F2; font-size:12px;">변경</span></div>
                    <form action="/verify" method="post">
                        <input type="hidden" name="server_id" value="{sid}">
                        <input type="hidden" name="access_token" value="{atk}">
                        <input type="hidden" name="user_id" value="{u.get('id')}">
                        <div class="cf-turnstile" data-sitekey="{CF_TURNSTILE_SITE_KEY}" data-theme="dark"></div>
                        <button type="submit" class="btn-main">인증 완료</button>
                    </form>
                    <div class="footer">RESTORE PROTOCOL</div>
                </div></body></html>
                """

@app.post("/verify", response_class=HTMLResponse)
async def verify_done(request: Request, server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    ip = request.headers.get("cf-connecting-ip") or request.client.host
    conn = sqlite3.connect('restore_user.db')
    conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (user_id, server_id, access_token, ip))
    conn.commit()
    conn.close()
    return "<html><head>{BASE_STYLE}</head><body><div class='card'><h1>인증 성공</h1><p>이제 브라우저를 닫으셔도 됩니다.</p></div></body></html>"

# --- 슬래시 명령어 ---

@bot.tree.command(name="링크발급", description="모든 유저가 사용 가능한 초대 링크 발급 패널을 전송합니다")
@app_commands.checks.has_permissions(administrator=True)
async def send_invite_panel(it: discord.Interaction):
    await it.channel.send(view=InvitePanel())
    await it.response.send_message("초대 패널을 성공적으로 전송했습니다.", ephemeral=True)

@bot.tree.command(name="초대랭킹", description="실시간 초대 랭킹 상위 10명을 확인합니다")
async def invite_ranking(it: discord.Interaction):
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    # 상위 10명 추출
    cur.execute("SELECT inviter_id, used_count FROM invites WHERE server_id = ? ORDER BY used_count DESC LIMIT 10", (str(it.guild_id),))
    rows = cur.fetchall()
    conn.close()
    
    rank_text = "아직 집계된 데이터가 없습니다."
    if rows:
        rank_text = ""
        for i, (uid, count) in enumerate(rows, 1):
            rank_text += f"**{i}위** | <@{uid}> — `{count}명` 초대 성공\n"

    rank_con = ui.Container()
    rank_con.accent_color = 0x00A7FF
    rank_con.add_item(ui.TextDisplay("## 🏆 실시간 초대 랭킹"))
    rank_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    rank_con.add_item(ui.TextDisplay(rank_text))
    rank_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    rank_con.add_item(ui.TextDisplay(f"-# 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
    
    await it.response.send_message(view=ui.LayoutView().add_item(rank_con))

@bot.tree.command(name="인증하기", description="인증 컨테이너를 전송합니다")
async def auth_cmd(it: discord.Interaction):
    con = ui.Container()
    con.accent_color = 0xffffff
    con.add_item(ui.TextDisplay("## 서버 인증"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay("아래 버튼을 눌러 인증을 완료해주세요."))
    
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={it.guild_id}"
    btn = ui.Button(label="인증하기", url=url, style=discord.ButtonStyle.link, emoji="✅")
    
    await it.channel.send(view=ui.LayoutView().add_item(con).add_item(btn))
    await it.response.send_message("전송 완료", ephemeral=True)

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="error")

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    bot.run(TOKEN)

