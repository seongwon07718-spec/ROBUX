import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, asyncio
from datetime import datetime

# --- 설정 ---
TOKEN = "YOUR_BOT_TOKEN"
VERIFY_LOG_WEBHOOK = "https://discord.com/api/webhooks/..."

intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.VERIFY_LOG_URL = VERIFY_LOG_WEBHOOK
        self.invite_cache = {}
        # 동시 접속 시 데이터 혼선을 막기 위한 락(Lock) 생성
        self.invite_lock = asyncio.Lock()

    async def setup_hook(self):
        conn = sqlite3.connect('restore_user.db')
        conn.execute("CREATE TABLE IF NOT EXISTS invites (inviter_id TEXT, invite_code TEXT PRIMARY KEY, server_id TEXT, used_count INTEGER DEFAULT 0)")
        conn.execute("CREATE TABLE IF NOT EXISTS invite_logs (invite_code TEXT, joined_user_id TEXT, PRIMARY KEY(invite_code, joined_user_id))")
        conn.commit()
        conn.close()
        
        @self.event
        async def on_ready():
            for guild in self.guilds:
                try:
                    self.invite_cache[guild.id] = {i.code: i.uses for i in await guild.invites()}
                except: pass
            print(f"Bot Login: {self.user}")
        
        await self.tree.sync()

    async def on_member_join(self, member):
        """동시 접속 대응 초대 코드 추적"""
        # 락을 사용하여 한 번에 한 명씩만 초대 처리를 진행함
        async with self.invite_lock:
            try:
                guild = member.guild
                old_invites = self.invite_cache.get(guild.id, {})
                new_invites = await guild.invites()
                
                # 현재 상태를 즉시 캐시에 저장 (다음 사람 처리를 위해)
                self.invite_cache[guild.id] = {i.code: i.uses for i in new_invites}

                used_invite = None
                # 사용 횟수가 1 증가한 코드를 정확히 찾음
                for invite in new_invites:
                    if invite.code in old_invites:
                        if invite.uses > old_invites[invite.code]:
                            used_invite = invite
                            break
                    elif invite.uses > 0: # 새로 생성된 코드인데 사용된 경우
                        used_invite = invite
                        break

                if used_invite:
                    conn = sqlite3.connect('restore_user.db')
                    cur = conn.cursor()
                    
                    cur.execute("SELECT inviter_id FROM invites WHERE invite_code = ?", (used_invite.code,))
                    row = cur.fetchone()
                    
                    if row:
                        inviter_id = row[0]
                        cur.execute("SELECT 1 FROM invite_logs WHERE invite_code = ? AND joined_user_id = ?", (used_invite.code, str(member.id)))
                        is_duplicate = cur.fetchone()

                        if is_duplicate:
                            await self.send_webhook_log(inviter_id, member, used_invite.code, "duplicate")
                        else:
                            cur.execute("INSERT INTO invite_logs VALUES (?, ?)", (used_invite.code, str(member.id)))
                            cur.execute("UPDATE invites SET used_count = used_count + 1 WHERE invite_code = ?", (used_invite.code,))
                            conn.commit()
                            await self.send_webhook_log(inviter_id, member, used_invite.code, "success")
                    
                    conn.close()
            except Exception as e:
                print(f"초대 추적 오류: {e}")

    async def send_webhook_log(self, inviter_id, member, code, status):
        if not self.VERIFY_LOG_URL: return
        con = ui.Container()
        con.accent_color = 0x90ee90 if status == "success" else 0xffa500
        con.add_item(ui.TextDisplay(f"## {'✅ 초대 성공' if status == 'success' else '⚠️ 중복 초대 감지'}"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay(
            f"**초대자:** <@{inviter_id}>\n"
            f"**입장자:** <@{member.id}>\n"
            f"**코드:** `{code}`" + (f"\n**상태:** 이미 기록된 유저입니다." if status != "success" else "")
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay("-# 서버 들어와주셔서 감사합니다 좋은 하루 보내세요"))
        
        view = ui.LayoutView().add_item(con)
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(self.VERIFY_LOG_URL, session=session)
            await webhook.send(view=view)

bot = RecoveryBot()

# --- 랭킹 초기화 명령어 (특정 유저 옵션 포함) ---
@bot.tree.command(name="랭킹초기화", description="전체 또는 특정 유저의 초대 랭킹을 초기화합니다")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(user="초기화할 유저를 선택하세요 (비워두면 전체 초기화)")
async def reset_ranking(it: discord.Interaction, user: discord.Member = None):
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    con = ui.Container()
    con.accent_color = 0xffffff
    
    if user:
        cur.execute("UPDATE invites SET used_count = 0 WHERE inviter_id = ? AND server_id = ?", (str(user.id), str(it.guild_id)))
        cur.execute("SELECT invite_code FROM invites WHERE inviter_id = ? AND server_id = ?", (str(user.id), str(it.guild_id)))
        row = cur.fetchone()
        if row: cur.execute("DELETE FROM invite_logs WHERE invite_code = ?", (row[0],))
        con.add_item(ui.TextDisplay(f"## 🛠️ 초기화 완료\n<@{user.id}> 님의 초대 점수와 로그가 초기화되었습니다."))
    else:
        cur.execute("UPDATE invites SET used_count = 0 WHERE server_id = ?", (str(it.guild_id),))
        cur.execute("DELETE FROM invite_logs WHERE invite_code IN (SELECT invite_code FROM invites WHERE server_id = ?)", (str(it.guild_id),))
        con.add_item(ui.TextDisplay("## 🛠️ 전체 초기화 완료\n모든 랭킹 데이터가 초기화되었습니다."))

    conn.commit()
    conn.close()
    await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)

