class BankModal(ui.Modal, title="계좌이체 충전"):
    name = ui.TextInput(label="입금자명", placeholder="입금하실 성함을 입력해주세요", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전금액", placeholder="금액을 입력해주세요 (숫자만)", min_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        db_id = database.insert_request(interaction.user.id, self.amount.value)
        layout = BankInfoLayout(self.name.value, self.amount.value, db_id)
        await interaction.response.edit_message(view=layout)

        log_chan = bot.get_channel(LOG_CHANNEL_ID)
        if log_chan is None:
            try:
                log_chan = await bot.fetch_channel(LOG_CHANNEL_ID)
            except:
                print("로그 채널을 찾을 수 없습니다. ID를 확인하세요.")

        if log_chan:
            await log_chan.send(view=AdminLogView(interaction.user, self.name.value, self.amount.value, db_id))

        asyncio.create_task(layout.start_timer(interaction))
