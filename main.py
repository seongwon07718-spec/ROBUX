# --- [ BankModal 및 관련 로직 수정 ] ---

class BankModal(ui.Modal, title="계좌이체 충전"):
    name = ui.TextInput(label="입금자명", placeholder="입금하실 성함을 입력해주세요", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전금액", placeholder="금액을 입력해주세요 (숫자만)", min_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        if not re.fullmatch(r'[가-힣]+', self.name.value):
            return await interaction.response.send_message("**입금자명은 한글로만 입력해주세요**", ephemeral=True)
        if not self.amount.value.isdigit():
            return await interaction.response.send_message("**충전금액은 숫자만 입력해주세요**", ephemeral=True)

        db_id = database.insert_request(interaction.user.id, self.amount.value)
        # 1. 처음엔 계좌 정보를 띄움
        layout = BankInfoLayout(self.name.value, self.amount.value, db_id)
        await interaction.response.send_message(view=layout, ephemeral=True)

        log_chan = bot.get_channel(LOG_CHANNEL_ID)
        if log_chan: 
            await log_chan.send(view=AdminLogView(interaction.user, self.name.value, self.amount.value, db_id))

        name_val = self.name.value
        amount_val = self.amount.value
        key = f"{name_val}_{amount_val}"

        # 2. 실시간 감시 시작 (입금 확인 시 layout을 직접 수정함)
        asyncio.create_task(self.watch_deposit(interaction, layout, name_val, amount_val, key))
        # 3. 만료 타이머 (기존 기능 유지)
        asyncio.create_task(layout.start_timer(interaction))

    async def watch_deposit(self, interaction, layout, name, amount, key):
        """입금을 감시하여 확인되면 기존 컨테이너 내용을 '충전 완료'로 교체"""
        for _ in range(30): # 약 1분간 감시 (2초 * 30회)
            await asyncio.sleep(2)
            if pending_deposits.get(key):
                # 데이터베이스 업데이트
                amount_int = int(amount)
                u_id = str(interaction.user.id)
                conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
                cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
                cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount_int, amount_int, u_id))
                conn.commit(); conn.close()
                
                # 대기열 삭제
                if key in pending_deposits: del pending_deposits[key]
                database.update_status(layout.db_id, "완료") # DB 상태도 업데이트

                # ✅ 컨테이너 내용 수정 (BankInfoLayout 내부의 요소를 바꿈)
                layout.container.clear_items()
                layout.container.accent_color = 0x00ff00 # 초록색으로 변경
                layout.container.add_item(ui.TextDisplay("## ✅ 자동충전 완료"))
                layout.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                layout.container.add_item(ui.TextDisplay(f"**입금자명:** {name}\n**충전금액:** {amount_int:,}원\n\n잔액이 정상적으로 합산되었습니다!"))
                
                # 메시지 수정 반영
                await interaction.edit_original_response(view=layout)
                break
