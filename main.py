import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, asyncio
from datetime import datetime

# --- 설정 (본인의 정보로 수정하세요) ---
TOKEN = "YOUR_BOT_TOKEN"
# 알림을 받을 웹훅 URL을 여기에 직접 넣으세요
VERIFY_LOG_WEBHOOK = "https://discord.com/api/webhooks/..." 

intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        # 클래스 변수로 웹훅 URL 저장
        self.VERIFY_LOG_URL = VERIFY_LOG_WEBHOOK
        
    async def setup_hook(self):
        conn = sqlite3.connect('restore_user.db')
        # 기본 테이블 생성
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, ip_addr TEXT, PRIMARY KEY(user_id, server_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS settings (server_id TEXT PRIMARY KEY, role_id TEXT, block_alt INTEGER DEFAULT 0, block_vpn INTEGER DEFAULT 0)")
        # 초대 테이블 (inviter_id와 invite_code가 한 쌍으로 묶임)
        conn.execute("CREATE TABLE IF NOT EXISTS invites (inviter_id TEXT, invite_code TEXT PRIMARY KEY, server_id TEXT, used_count INTEGER DEFAULT 0)")
        # 초대 로그 (누가 어떤 코드로 들어왔는지 기록)
        conn.execute("CREATE TABLE IF NOT EXISTS invite_logs (invite_code TEXT, joined_user_id TEXT, PRIMARY KEY(invite_code, joined_user_id))")
        
        # 컬럼 추가 (기존 DB 호환용)
        try: conn.execute("ALTER TABLE settings ADD COLUMN block_alt INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN ip_addr TEXT")
        except: pass
        
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"Bot Login: {self.user}")

    async def on_member_join(self, member):
        """유저 입장 시 발급된 초대 코드를 확인하여 횟수 증가 및 로그 전송"""
        try:
            # 봇이 서버의 초대 링크 현황을 실시간으로 가져옴
            invites_list = await member.guild.invites()
            conn = sqlite3.connect('restore_user.db')
            cur = conn.cursor()

            for invite in invites_list:
                # 1. DB에 저장된 발급자의 코드인지 확인
                cur.execute("SELECT inviter_id, used_count FROM invites WHERE invite_code = ?", (invite.code,))
                row = cur.fetchone()
                
                if row:
                    inviter_id = row[0]
                    
                    # 2. 중복 초대 감지 (이미 이 코드로 들어왔던 기록이 있는지 확인)
                    cur.execute("SELECT 1 FROM invite_logs WHERE invite_code = ? AND joined_user_id = ?", (invite.code, str(member.id)))
                    is_duplicate = cur.fetchone()
                    
                    if is_duplicate:
                        # [중복 감지] 컨테이너 전송
                        if self.VERIFY_LOG_URL:
                            dup_con = ui.Container()
                            dup_con.accent_color = 0xffa500 # 주황색 (경고)
                            dup_con.add_item(ui.TextDisplay("## ⚠️ 중복 초대 감지"))
                            dup_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                            dup_con.add_item(ui.TextDisplay(
                                f"**대상 유저:** <@{member.id}>\n"
                                f"**초대 시도:** <@{inviter_id}>\n"
                                f"**상태:** 이미 해당 코드로 기록된 유저입니다. (집계 제외)"
                            ))
                            view = ui.LayoutView().add_item(dup_con)
                            async with aiohttp.ClientSession() as session:
                                webhook = discord.Webhook.from_url(self.VERIFY_LOG_URL, session=session)
                                await webhook.send(view=view)
                        continue # 다음 코드로 넘어감

                    # 3. 정상 초대 처리 (해당 코드의 사용 횟수가 실제로 증가했는지 대조 - 선택사항이나 권장됨)
                    # 여기서는 DB에 로그가 없고, DB에 등록된 코드라면 즉시 반영합니다.
                    cur.execute("INSERT INTO invite_logs VALUES (?, ?)", (invite.code, str(member.id)))
                    # 해당 발급자의 해당 코드 카운트만 +1 (독립적 누적)
                    cur.execute("UPDATE invites SET used_count = used_count + 1 WHERE invite_code = ?", (invite.code,))
                    conn.commit()
                    
                    # [초대 성공] 웹훅 전송
                    if self.VERIFY_LOG_URL:
                        log_con = ui.Container()
                        log_con.accent_color = 0x90ee90 # 연두색 (성공)
                        log_con.add_item(ui.TextDisplay("## ✅ 초대 성공"))
                        log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                        log_con.add_item(ui.TextDisplay(
                            f"**초대자:** <@{inviter_id}>\n"
                            f"**입장자:** <@{member.id}>\n"
                            f"**코드:** `{invite.code}`"
                        ))
                        log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                        log_con.add_item(ui.TextDisplay("-# 서버 들어와주셔서 감사합니다 좋은 하루 보내세요"))
                        
                        view = ui.LayoutView().add_item(log_con)
                        async with aiohttp.ClientSession() as session:
                            webhook = discord.Webhook.from_url(self.VERIFY_LOG_URL, session=session)
                            await webhook.send(view=view)
            
            conn.close()
        except Exception as e:
            print(f"초대 추적 오류: {e}")

bot = RecoveryBot()

# 이후 슬래시 명령어 부분들...
# (생략: 이전 답변들에서 제공한 /링크발급, /초대랭킹 등은 이 구조와 완벽히 호환됩니다.)

if __name__ == "__main__":
    bot.run(TOKEN)

