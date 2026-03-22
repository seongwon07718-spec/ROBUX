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
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, ip_addr TEXT, PRIMARY KEY(user_id, server_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS settings (server_id TEXT PRIMARY KEY, role_id TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS invites (inviter_id TEXT, invite_code TEXT PRIMARY KEY, server_id TEXT, used_count INTEGER DEFAULT 0)")
        conn.execute("CREATE TABLE IF NOT EXISTS invite_logs (invite_code TEXT, joined_user_id TEXT, PRIMARY KEY(invite_code, joined_user_id))")
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"Logged in as {self.user}")

    async def on_member_join(self, member):
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
                            log_con.add_item(ui.TextDisplay(f"**초대자:** <@{inviter_id}>\n**입장자:** <@{member.id}> (`{member.name}`)\n**코드:** `{invite.code}`"))
                            view = ui.LayoutView().add_item(log_con)
                            async with aiohttp.ClientSession() as session:
                                await session.post(WEBHOOK_URL, json={"components": view.to_dict()["components"]})
            conn.close()
        except: pass

bot = RecoveryBot()

# --- 초대 링크 발급 패널 (컨테이너 내 버튼 배치) ---
class InvitePanel(ui.LayoutView):
    def __init__(self):
        super().__init__()
        self.container = ui.Container()
        self.container.accent_color = 0xffffff
        self.container.add_item(ui.TextDisplay("## 🔗 초대 링크 발급"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("아래 버튼을 눌러 본인만의 링크를 생성하세요.\n링크로 유저 유입 시 랭킹에 자동 반영됩니다."))
        
        btn = ui.Button(label="링크 발급받기", style=discord.ButtonStyle.gray, emoji="✨")
        btn.callback = self.issue_callback
        self.container.add_item(ui.ActionRow(btn))
        self.add_item(self.container)

    async def issue_callback(self, it: discord.Interaction):
        conn = sqlite3.connect('restore_user.db')
        cur = conn.cursor()
        cur.execute("SELECT invite_code FROM invites WHERE inviter_id = ? AND server_id = ?", (str(it.user.id), str(it.guild_id)))
        row = cur.fetchone()
        if row:
            con = ui.Container()
            con.accent_color = 0xff4444
            con.add_item(ui.TextDisplay(f"## 이미 발급됨\n내 링크: `https://discord.gg/{row[0]}`"))
            conn.close()
            return await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

        invite = await it.channel.create_invite(max_age=0, max_uses=0, unique=True)
        cur.execute("INSERT INTO invites (inviter_id, invite_code, server_id) VALUES (?, ?, ?)", (str(it.user.id), invite.code, str(it.guild_id)))
        conn.commit()
        conn.close()

        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(f"## 발급 성공\n\n`https://discord.gg/{invite.code}`"))
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

# --- 실시간 랭킹 생성 함수 ---
def build_rank_container(guild_id):
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    cur.execute("SELECT inviter_id, used_count FROM invites WHERE server_id = ? ORDER BY used_count DESC LIMIT 10", (str(guild_id),))
    rows = cur.fetchall()
    conn.close()

    con = ui.Container()
    con.accent_color = 0x00A7FF
    con.add_item(ui.TextDisplay("## 🏆 실시간 초대 랭킹 (Top 10)"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.medium))

    if not rows:
        con.add_item(ui.TextDisplay("아직 집계된 데이터가 없습니다."))
    else:
        for i, (uid, count) in enumerate(rows, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
            con.add_item(ui.TextDisplay(f"{emoji} **{i}위** | <@{uid}>\n> 초대 성공: `{count}명`"))
            # 마지막 항목 뒤에는 구분선을 넣지 않음
            if i < len(rows):
                con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.medium))
    con.add_item(ui.TextDisplay(f"-# 최종 업데이트: {datetime.now().strftime('%H:%M:%S')} (120초마다 자동 갱신)"))
    return con

# --- 커맨드 영역 ---

@bot.tree.command(name="링크발급", description="모든 유저가 사용 가능한 초대 링크 발급 패널을 전송합니다")
@app_commands.checks.has_permissions(administrator=True)
async def cmd_invite_panel(it: discord.Interaction):
    await it.channel.send(view=InvitePanel())
    await it.response.send_message("초대 패널을 전송했습니다.", ephemeral=True)

@bot.tree.command(name="초대랭킹", description="실시간으로 갱신되는 초대 랭킹 상위 10명을 표시합니다")
async def cmd_invite_ranking(it: discord.Interaction):
    # 첫 전송
    con = build_rank_container(it.guild_id)
    await it.response.send_message(view=ui.LayoutView().add_item(con))
    
    # 메시지 객체 가져오기
    msg = await it.original_response()
    
    # 120초마다 갱신 루프 (백그라운드 태스크)
    async def update_ranking():
        for _ in range(30): # 예시로 1시간 동안만 자동 갱신 (30번 * 120초)
            await asyncio.sleep(120)
            try:
                updated_con = build_rank_container(it.guild_id)
                await msg.edit(view=ui.LayoutView().add_item(updated_con))
            except:
                break # 메시지가 삭제되거나 권한 오류 시 루프 종료

    asyncio.create_task(update_ranking())

@bot.tree.command(name="인증하기", description="인증 컨테이너를 전송합니다")
async def auth_cmd(it: discord.Interaction):
    con = ui.Container()
    con.accent_color = 0xffffff
    con.add_item(ui.TextDisplay("## 서버 인증\n아래 버튼을 눌러 인증을 완료해주세요."))
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={it.guild_id}"
    btn = ui.Button(label="인증하기", url=url, style=discord.ButtonStyle.link, emoji="✅")
    await it.channel.send(view=ui.LayoutView().add_item(con).add_item(btn))
    await it.response.send_message("전송 완료", ephemeral=True)

# --- 웹 서버 (FastAPI) ---
@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    # 웹 페이지 레이아웃은 이전과 동일하게 유지 (인증 로직 포함)
    return "..." # (전체 코드는 지면상 생략, 이전 답변의 웹 소스 유지)

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="error")

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    bot.run(TOKEN)

