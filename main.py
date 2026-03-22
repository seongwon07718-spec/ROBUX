    async def on_member_join(self, member):
        """유저 입장 시 발급된 초대 코드를 확인하여 횟수 증가 및 로그 전송"""
        try:
            # 서버의 모든 초대 링크 목록 가져오기
            invites_list = await member.guild.invites()
            conn = sqlite3.connect('restore_user.db')
            cur = conn.cursor()

            for invite in invites_list:
                # DB에 등록된 초대 코드인지 확인
                cur.execute("SELECT inviter_id FROM invites WHERE invite_code = ?", (invite.code,))
                row = cur.fetchone()
                
                if row:
                    inviter_id = row[0]
                    # 중복 입장 체크 (동일 코드로 이미 기록된 유저인지)
                    cur.execute("SELECT 1 FROM invite_logs WHERE invite_code = ? AND joined_user_id = ?", (invite.code, str(member.id)))
                    
                    if not cur.fetchone():
                        # 로그 기록 및 카운트 증가
                        cur.execute("INSERT INTO invite_logs VALUES (?, ?)", (invite.code, str(member.id)))
                        cur.execute("UPDATE invites SET used_count = used_count + 1 WHERE invite_code = ?", (invite.code,))
                        conn.commit()
                        
                        # 웹훅 로그 전송 (VERIFY_LOG_URL이 설정되어 있을 때)
                        if hasattr(self, 'VERIFY_LOG_URL') and self.VERIFY_LOG_URL:
                            log_con = ui.Container()
                            log_con.accent_color = 0x90ee90 # 이미지와 유사한 연두색
                            log_con.add_item(ui.TextDisplay("## ✅ 초대 성공"))
                            log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                            log_con.add_item(ui.TextDisplay(f"**초대자:** <@{inviter_id}>\n**입장자:** <@{member.id}>\n**코드:** `{invite.code}`"))
                            log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                            log_con.add_item(ui.TextDisplay("-# 서버 들어와주셔서 감사합니다 좋은 하루 보내세요"))
                            
                            view = ui.LayoutView().add_item(log_con)
                            async with aiohttp.ClientSession() as session:
                                webhook = discord.Webhook.from_url(self.VERIFY_LOG_URL, session=session)
                                await webhook.send(view=view)
            conn.close()
        except Exception as e:
            print(f"초대 추적 중 오류 발생: {e}")

