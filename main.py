import re
import charge_client  # 작성하신 charge_client.py를 임포트합니다.

class BankModal(ui.Modal, title="계좌이체 충전"):
    name = ui.TextInput(label="입금자명", placeholder="입금하실 성함을 입력해주세요", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전금액", placeholder="금액을 입력해주세요 (숫자만)", min_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        # 1. 입력값 유효성 검사 (한글/숫자)
        if not re.fullmatch(r'[가-힣]+', self.name.value):
            return await interaction.response.send_message("**입금자명은 공백 없이 한글로만 입력해주세요**", ephemeral=True)

        if not self.amount.value.isdigit():
            return await interaction.response.send_message("**충전금액은 숫자만 입력해주세요**", ephemeral=True)

        # 2. 도배 방지 체크 (최근 5분 이내 신청 확인)
        last_time = database.get_last_request_time(interaction.user.id)
        current_time = time.time()

        if current_time - last_time < 300:
            remaining = int(300 - (current_time - last_time))
            return await interaction.response.send_message(f"**이미 충전 신청한 기록이 있습니다\n{remaining}초 후에 다시 시도해주세요**", ephemeral=True)

        # 3. 자동 충전 API 서버에 확인 요청
        # 전송 메시지 형식: "입금자명 금액"
        charge_msg = f"{self.name.value} {self.amount.value}"
        result = charge_client.send_charge_message(charge_msg)

        if result.get("ok"):
            # [성공] API 서버에서 입금이 확인된 경우 -> 즉시 DB 업데이트
            amount_int = int(self.amount.value)
            u_id = str(interaction.user.id)
            
            conn = sqlite3.connect('vending1.db')
            cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
            cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount_int, amount_int, u_id))
            conn.commit()
            conn.close()

            # 즉시 성공 메시지 전송
            await interaction.response.send_message(f"✅ **자동 충전 완료!**\n{amount_int:,}원이 즉시 반영되었습니다.", ephemeral=True)
            
            # 로그 채널 알림
            log_chan = bot.get_channel(LOG_CHANNEL_ID)
            if log_chan:
                await log_chan.send(f"💳 **[자동 충전]** {interaction.user.mention} | 입금자: {self.name.value} | 금액: {amount_int:,}원")
        
        else:
            # [실패/대기] 입금 내역이 없거나 API 오류 시 -> 기존 수동 승인 모드
            db_id = database.insert_request(interaction.user.id, self.amount.value)
            layout = BankInfoLayout(self.name.value, self.amount.value, db_id)
            
            # 사유에 따른 안내 멘트
            reason = "이미 처리된 내역이거나 " if result.get("duplicate") else ""
            await interaction.response.send_message(
                f"ℹ️ **{reason}입금 확인 전입니다.**\n아래 계좌로 입금하시면 잠시 후 관리자가 확인해 드립니다.", 
                view=layout, 
                ephemeral=True
            )

            # 관리자용 로그 전송 (수동 승인 버튼 포함)
            log_chan = bot.get_channel(LOG_CHANNEL_ID)
            if log_chan is None:
                try: log_chan = await bot.fetch_channel(LOG_CHANNEL_ID)
                except: pass

            if log_chan:
                await log_chan.send(view=AdminLogView(interaction.user, self.name.value, self.amount.value, db_id))

            # 5분 타이머 시작
            asyncio.create_task(layout.start_timer(interaction))
