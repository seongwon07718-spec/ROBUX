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
        # invites 테이블: 링크를 발급받은 사람만 존재함
        conn.execute("CREATE TABLE IF NOT EXISTS invites (inviter_id TEXT, invite_code TEXT PRIMARY KEY, server_id TEXT, used_count INTEGER DEFAULT 0)")
        conn.execute("CREATE TABLE IF NOT EXISTS invite_logs (invite_code TEXT, joined_user_id TEXT, PRIMARY KEY(invite_code, joined_user_id))")
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"Logged in as {self.user}")

    async def on_member_join(self, member):
        """유저 입장 시 발급된 초대 코드를 확인하여 횟수 증가 및 로그 전송"""
        try:
            invites_list = await member.guild.invites()
            conn = sqlite3.connect('restore_user.db')
            cur = conn.cursor()
            for invite in invites_list:
                # DB에 등록된(링크발급받은 유저의) 코드인지 확인
                cur.execute("SELECT inviter_id FROM invites WHERE invite_code = ?", (invite.code,))
                row = cur.fetchone()
                if row:
                    inviter_id = row[0]
                    # 입장한 유저가 이미 이 코드로 기록된 적이 있는지 확인 (중복 입장 방지)
                    cur.execute("SELECT 1 FROM invite_logs WHERE invite_code = ? AND joined_user_id = ?", (invite.code, str(member.id)))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO invite_logs VALUES (?, ?)", (invite.code, str(member.id)))
                        # 링크 발급자의 초대 성공 횟수 1 증가
                        cur.execute("UPDATE invites SET used_count = used_count + 1 WHERE invite_code = ?", (invite.code,))
                        conn.commit()
                        
                        if WEBHOOK_URL:
                            log_con = ui.Container()
                            log_con.accent_color = 0x00ff88
                            log_con.add_item(ui.TextDisplay("## 📥 초대 성공 로그"))
                            log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                            log_con.add_item(ui.TextDisplay(f"**초대자:** <@{inviter_id}>\n**입장자:** <@{member.id}> (`{member.name}`)\n**사용된 코드:** `{invite.code}`"))
                            view = ui.LayoutView().add_item(log_con)
                            async with aiohttp.ClientSession() as session:
                                await session.post(WEBHOOK_URL, json={"components": view.to_dict()["components"]})
            conn.close()
        except Exception as e:
            print(f"Join Tracking Error: {e}")

    async def on_member_remove(self, member):
        """서버를 나가면 링크 데이터 및 랭킹 데이터 삭제"""
        conn = sqlite3.connect('restore_user.db')
        cur = conn.cursor()
        # 해당 유저가 발급받은 링크가 있는지 확인
        cur.execute("SELECT invite_code FROM invites WHERE inviter_id = ? AND server_id = ?", (str(member.id), str(member.guild.id)))
        row = cur.fetchone()
        if row:
            invite_code = row[0]
            # 1. 초대 랭킹 데이터 삭제
            cur.execute("DELETE FROM invites WHERE inviter_id = ? AND server_id = ?", (str(member.id), str(member.guild.id)))
            # 2. 해당 링크로 들어왔던 로그 삭제 (선택 사항, 통계 정합성을 위해 유지할 수도 있음)
            cur.execute("DELETE FROM invite_logs WHERE invite_code = ?", (invite_code,))
            conn.commit()
            print(f"Removed Ranking Data for: {member.id} (User Left)")
        conn.close()

bot = RecoveryBot()

# --- 초대 링크 발급 패널 디자인 ---
class InvitePanel(ui.LayoutView):
    def __init__(self):
        super().__init__()
        self.container = ui.Container()
        self.container.accent_color = 0xffffff
        self.container.add_item(ui.TextDisplay("## 🔗 개인 초대 링크 생성"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("아래 버튼을 눌러 링크를 발급받아야 랭킹에 등록됩니다.\n나가면 데이터가 삭제되니 주의하세요."))
        
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
            con.add_item(ui.TextDisplay(f"## 이미 발급되었습니다\n내 초대 링크: `https://discord.gg/{row[0]}`"))
            conn.close()
            return await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

        # 영구 링크 생성
        try:
            invite = await it.channel.create_invite(max_age=0, max_uses=0, unique=True)
            cur.execute("INSERT INTO invites (inviter_id, invite_code, server_id) VALUES (?, ?, ?)", (str(it.user.id), invite.code, str(it.guild_id)))
            conn.commit()
            
            sc_con = ui.Container()
            sc_con.accent_color = 0x5865F2
            sc_con.add_item(ui.TextDisplay(f"## 링크 발급 성공\n이제 랭킹에 집계됩니다!\n\n`https://discord.gg/{invite.code}`"))
            await it.response.send_message(view=ui.LayoutView().add_item(sc_con), ephemeral=True)
        except:
            await it.response.send_message("링크 생성 권한이 없거나 오류가 발생했습니다.", ephemeral=True)
        finally:
            conn.close()

# --- 실시간 랭킹 컨테이너 빌더 (각 유저 개별 분리) ---
def build_rank_container(guild_id):
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    # 링크를 발급받은 사람 중 초대수가 많은 상위 10명만 조회
    cur.execute("SELECT inviter_id, used_count FROM invites WHERE server_id = ? ORDER BY used_count DESC LIMIT 10", (str(guild_id),))
    rows = cur.fetchall()
    conn.close()

    con = ui.Container()
    con.accent_color = 0xffffff
    con.add_item(ui.TextDisplay("## 🏆 실시간 초대 랭킹"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

    if not rows:
        con.add_item(ui.TextDisplay("현재 링크를 발급받은 유저가 없거나\n초대 데이터가 존재하지 않습니다."))
    else:
        for i, (uid, count) in enumerate(rows, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
            # 개별 유저 표시
            con.add_item(ui.TextDisplay(f"{emoji} **{i}위** | <@{uid}>\n> 초대 성공: `{count}명`"))
            # 유저마다 구분선 추가 (마지막 유저 제외)
            if i < len(rows):
                con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.medium))
    con.add_item(ui.TextDisplay(f"-# 업데이트: {datetime.now().strftime('%H:%M:%S')} (120초마다 갱신)"))
    return con

# --- 커맨드 영역 ---

@bot.tree.command(name="링크발급", description="초대 링크 발급 패널을 전송합니다")
@app_commands.checks.has_permissions(administrator=True)
async def cmd_invite_panel(it: discord.Interaction):
    await it.channel.send(view=InvitePanel())
    await it.response.send_message("패널 전송 완료.", ephemeral=True)

@bot.tree.command(name="초대랭킹", description="120초마다 자동 갱신되는 랭킹을 표시합니다")
async def cmd_invite_ranking(it: discord.Interaction):
    con = build_rank_container(it.guild_id)
    await it.response.send_message(view=ui.LayoutView().add_item(con))
    
    msg = await it.original_response()
    
    # 갱신 루프
    async def update_loop():
        while True:
            await asyncio.sleep(120)
            try:
                # 메시지 수정 시 새로운 컨테이너 빌드
                updated_con = build_rank_container(it.guild_id)
                await msg.edit(view=ui.LayoutView().add_item(updated_con))
            except:
                break 

    asyncio.create_task(update_loop())

# --- FastAPI 인증 웹페이지 (생략된 스타일 및 로직 포함) ---
@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    return "..." # 이전 답변의 웹 소스 코드를 그대로 유지하여 사용하세요.

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="error")

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    bot.run(TOKEN)

