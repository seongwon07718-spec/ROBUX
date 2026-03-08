class BankModal(ui.Modal, title="계좌이체 충전"):
    name = ui.TextInput(label="입금자명", placeholder="입금하실 성함을 입력해주세요", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전금액", placeholder="금액을 입력해주세요 (숫자만)", min_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        if not re.fullmatch(r'[가-힣]+', self.name.value):
            return await interaction.response.send_message("**입금자명은 한글로만 입력해주세요**", ephemeral=True)
        if not self.amount.value.isdigit():
            return await interaction.response.send_message("**충전금액은 숫자만 입력해주세요**", ephemeral=True)

        db_id = database.insert_request(interaction.user.id, self.amount.value)
        layout = BankInfoLayout(self.name.value, self.amount.value, db_id)
        await interaction.response.send_message(view=layout, ephemeral=True)

        if AUTO_LOG_ENABLED:
            log_chan = bot.get_channel(LOG_CHANNEL_ID)
            if log_chan: 
                await log_chan.send(view=AdminLogView(interaction.user, self.name.value, self.amount.value, db_id))

        name_val = self.name.value
        amount_val = self.amount.value
        key = f"{name_val}_{amount_val}"
        asyncio.create_task(self.watch_deposit(interaction, layout, name_val, amount_val, key))
        asyncio.create_task(layout.start_timer(interaction))

async def watch_deposit(self, interaction, layout, name, amount, key):
    while True:
        await asyncio.sleep(3)
        if pending_deposits.get(key):
            amount_int = int(amount)
            u_id = str(interaction.user.id)
            conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
            cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount_int, amount_int, u_id))
            cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                        (u_id, amount_int, time.strftime('%Y-%m-%d %H:%M'), "자동(계좌)"))
            conn.commit(); conn.close()
            if key in pending_deposits: del pending_deposits[key]
            database.update_status(layout.db_id, "완료")

            layout.container.clear_items()
            layout.container.accent_color = 0x00ff00
            layout.container.add_item(ui.TextDisplay("## 자동충전 완료"))
            layout.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            layout.container.add_item(ui.TextDisplay(f"충전금액: **{amount_int:,}원**\n\n성공적으로 충전이 완료되었습니다"))
                
            await interaction.edit_original_response(view=layout)
            break
