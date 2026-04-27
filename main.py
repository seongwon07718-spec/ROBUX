class DepositModal(discord.ui.Modal, title="계좌이체 충전"):
    name = discord.ui.TextInput(
        label="입금자명",
        placeholder="입금자명을 입력하세요",
        required=True
    )
    amount = discord.ui.TextInput(
        label="충전할 금액",
        placeholder="예) 10000",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        expires_timestamp = int(time.time()) + (5 * 60)

        class BankContainer(discord.ui.Container):
            text = discord.ui.TextDisplay(
                f"## 계좌 정보"
            )
            sep = discord.ui.Separator()
            text2 = discord.ui.TextDisplay(
                f"**입금자명:** {self.name.value}\n"
                f"**충전 금액:** {self.amount.value}원\n"
            )
            sep2 = discord.ui.Separator()
            text3 = discord.ui.TextDisplay(
                f"**은행명:** `{BANK_NAME}`\n"
                f"**계좌번호:** `{BANK_ACCOUNT}`\n"
                f"**예금주:** `{BANK_OWNER}`\n\n"
                f"**입금 마감: <t:{expires_timestamp}:R>**"
            )

        class BankLayout(discord.ui.LayoutView):
            container = BankContainer(accent_color=0xffffff)

        await interaction.response.send_message(view=BankLayout(), ephemeral=True)
