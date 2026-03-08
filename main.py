class BankModal(ui.Modal, title="계좌이체 충전"):
    name = ui.TextInput(label="입금자명", placeholder="입금하실 성함을 입력해주세요", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전금액", placeholder="금액을 입력해주세요 (숫자만)", min_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        if not re.fullmatch(r'[가-힣]+', self.name.value):
            return await interaction.response.send_message("**입금자명은 공백 없이 한글로만 입력해주세요**", ephemeral=True)

        if not self.amount.value.isdigit():
            return await interaction.response.send_message("**충전금액은 숫자만 입력해주세요**", ephemeral=True)

        last_time = database.get_last_request_time(interaction.user.id)
        current_time = time.time()

        if current_time - last_time < 300:
            remaining = int(300 - (current_time - last_time))
            return await interaction.response.send_message(f"**이미 충전 신청한 기록이 있습니다\n{remaining}초 후에 다시 시도해주세요**", ephemeral=True)

        db_id = database.insert_request(interaction.user.id, self.amount.value)
        layout = BankInfoLayout(self.name.value, self.amount.value, db_id)
        
        await interaction.response.edit_message(view=layout)

        log_chan = bot.get_channel(LOG_CHANNEL_ID)
        if log_chan is None:
            try: log_chan = await bot.fetch_channel(LOG_CHANNEL_ID)
            except: pass

        if log_chan:
            await log_chan.send(view=AdminLogView(interaction.user, self.name.value, self.amount.value, db_id))

        asyncio.create_task(layout.start_timer(interaction))
