class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        conn = sqlite3.connect('restore_user.db')
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, ip_addr TEXT, PRIMARY KEY(user_id, server_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS settings (server_id TEXT PRIMARY KEY, role_id TEXT, block_alt INTEGER DEFAULT 0, block_vpn INTEGER DEFAULT 0)")
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
        """유저 입장 시 발급된 초대 코드를 확인하여 횟수 증가 및 로그 전송"""
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
                        
                        if hasattr(self, 'VERIFY_LOG_URL') and self.VERIFY_LOG_URL:
                            log_con = ui.Container()
                            log_con.accent_color = 0x90ee90
                            log_con.add_item(ui.TextDisplay("## 초대 성공"))
                            log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                            log_con.add_item(ui.TextDisplay(f"초대자: <@{inviter_id}>\n입장자: <@{member.id}>\n코드: `{invite.code}`"))
                            log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                            log_con.add_item(ui.TextDisplay("-# 서버 들어와주셔서 감사합니다 좋은 하루 보내세요"))
                            
                            view = ui.LayoutView().add_item(log_con)
                            async with aiohttp.ClientSession() as session:
                                webhook = discord.Webhook.from_url(self.VERIFY_LOG_URL, session=session)
                                await webhook.send(view=view)
            conn.close()
        except Exception as e:
            print(f"초대 추적 중 오류 발생: {e}")
