import re
import charge_client  # 위에서 만든 파일 임포트

class BankModal(ui.Modal, title="계좌이체 충전"):
    name = ui.TextInput(label="입금자명", placeholder="입금하실 성함(한글)을 입력해주세요", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전금액", placeholder="금액을 입력해주세요 (숫자만)", min_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        # 1. 유효성 검사
        if not re.fullmatch(r'[가-힣]+', self.name.value):
            return await interaction.response.send_message("❌ **입금자명은 한글로만 입력해주세요.**", ephemeral=True)
        if not self.amount.value.isdigit():
            return await interaction.response.send_message("❌ **충전금액은 숫자만 입력해주세요.**", ephemeral=True)

        await interaction.response.send_message("⏳ **입금 확인 중입니다. 잠시만 기다려 주세요...**", ephemeral=True)

        # 2. 자동충전 API 요청 (형식: 입금자명 금액)
        charge_msg = f"{self.name.value} {self.amount.value}"
        result = charge_client.send_charge_message(charge_msg)

        if result.get("ok"):
            # [성공] 자동 승인 처리
            amount_int = int(self.amount.value)
            u_id = str(interaction.user.id)
            
            conn = sqlite3.connect('vending1.db')
            cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
            cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount_int, amount_int, u_id))
            conn.commit()
            conn.close()

            await interaction.edit_original_response(content=f"✅ **자동 충전 완료!**\n{amount_int:,}원이 즉시 반영되었습니다.")
        
        else:
            # [실패/대기] 입금 내역이 없거나 중복인 경우 기존 수동 모드로 전환
            db_id = database.insert_request(interaction.user.id, self.amount.value)
            layout = BankInfoLayout(self.name.value, self.amount.value, db_id)
            
            error_reason = "이미 처리되었거나 입금 내역을 찾을 수 없습니다." if result.get("duplicate") else "입금 확인 전입니다."
            await interaction.edit_original_response(
                content=f"ℹ️ **자동 확인 불가 ({error_reason})**\n입금 후 대기하시면 관리자가 확인해 드립니다.", 
                view=layout
            )

            # 로그 채널에 알림
            log_chan = bot.get_channel(LOG_CHANNEL_ID)
            if log_chan:
                await log_chan.send(view=AdminLogView(interaction.user, self.name.value, self.amount.value, db_id))
