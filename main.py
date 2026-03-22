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
        # 서버별 초대장 사용 횟수를 캐싱할 딕셔너리 (정확한 추적용)
        self.invite_cache = {}

    async def setup_hook(self):
        conn = sqlite3.connect('restore_user.db')
        conn.execute("CREATE TABLE IF NOT EXISTS invites (inviter_id TEXT, invite_code TEXT PRIMARY KEY, server_id TEXT, used_count INTEGER DEFAULT 0)")
        conn.execute("CREATE TABLE IF NOT EXISTS invite_logs (invite_code TEXT, joined_user_id TEXT, PRIMARY KEY(invite_code, joined_user_id))")
        conn.commit()
        conn.close()
        
        # 봇 시작 시 현재 모든 서버의 초대장 상태를 캐시에 저장
        @self.event
        async def on_ready():
            for guild in self.guilds:
                try:
                    self.invite_cache[guild.id] = {i.code: i.uses for i in await guild.invites()}
                except:
                    pass
            print(f"Bot Login: {self.user}")
        
        await self.tree.sync()

    async def on_member_join(self, member):
        """정확한 초대 코드 추적 로직"""
        try:
            guild = member.guild
            old_invites = self.invite_cache.get(guild.id, {})
            new_invites = await guild.invites()
            
            # 캐시 업데이트
            self.invite_cache[guild.id] = {i.code: i.uses for i in new_invites}

            used_invite = None
            for invite in new_invites:
                # 사용 횟수가 이전보다 증가한 코드를 찾음
                if invite.code in old_invites and invite.uses > old_invites[invite.code]:
                    used_invite = invite
                    break
            
            # 만약 사용 횟수 비교로 못 찾았고(새로 생성된 코드 등), 새 코드의 사용 횟수가 1이라면
            if not used_invite:
                for invite in new_invites:
                    if invite.code not in old_invites and invite.uses > 0:
                        used_invite = invite
                        break

            if used_invite:
                conn = sqlite3.connect('restore_user.db')
                cur = conn.cursor()
                
                # DB에 등록된 발급자의 코드인지 확인
                cur.execute("SELECT inviter_id FROM invites WHERE invite_code = ?", (used_invite.code,))
                row = cur.fetchone()
                
                if row:
                    inviter_id = row[0]
                    # 중복 체크
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
        if status == "success":
            con.accent_color = 0x90ee90
            con.add_item(ui.TextDisplay("## ✅ 초대 성공"))
        else:
            con.accent_color = 0xffa500
            con.add_item(ui.TextDisplay("## ⚠️ 중복 초대 감지"))
            
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

# --- 초대 랭킹 초기화 명령어 (유저 선택 옵션 추가) ---

@bot.tree.command(name="랭킹초기화", description="전체 또는 특정 유저의 초대 랭킹을 초기화합니다")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(user="초기화할 유저를 선택하세요 (비워두면 전체 초기화)")
async def reset_ranking(it: discord.Interaction, user: discord.Member = None):
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    
    con = ui.Container()
    con.accent_color = 0xffffff
    
    if user:
        # 특정 유저만 초기화
        cur.execute("UPDATE invites SET used_count = 0 WHERE inviter_id = ? AND server_id = ?", (str(user.id), str(it.guild_id)))
        # 해당 유저의 링크로 들어온 로그도 삭제 (다시 초대 가능하게 하려면)
        cur.execute("SELECT invite_code FROM invites WHERE inviter_id = ? AND server_id = ?", (str(user.id), str(it.guild_id)))
        row = cur.fetchone()
        if row:
            cur.execute("DELETE FROM invite_logs WHERE invite_code = ?", (row[0],))
            
        con.add_item(ui.TextDisplay(f"## 🛠️ 초기화 완료\n<@{user.id}> 님의 초대 점수와 로그가 초기화되었습니다."))
    else:
        # 전체 초기화
        cur.execute("UPDATE invites SET used_count = 0 WHERE server_id = ?", (str(it.guild_id),))
        cur.execute("DELETE FROM invite_logs WHERE invite_code IN (SELECT invite_code FROM invites WHERE server_id = ?)", (str(it.guild_id),))
        con.add_item(ui.TextDisplay("## 🛠️ 전체 초기화 완료\n이 서버의 모든 초대 랭킹 데이터가 초기화되었습니다."))

    conn.commit()
    conn.close()
    
    await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)

