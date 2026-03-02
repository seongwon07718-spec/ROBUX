class BankInfoLayout(ui.LayoutView):
    def __init__(self, name, amount):
        super().__init__()
        self.name = name
        self.amount = amount
        self.container = ui.Container(ui.TextDisplay(f"## 입금 정보"), accent_color=0x00ff00)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**은행명:** 카카오뱅크\n**계좌:** 123-456-7890\n**예금주:** 정성원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**입금자명:** {self.name}\n**충전금액:** {self.amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("-# 5분 이내로 입금해주셔야 충전이 완료됩니다"))
        self.add_item(self.container)

    async def start_timer(self, interaction: discord.Interaction):
        await asyncio.sleep(300)

        self.container.clear_items()
        self.container.style = discord.ButtonStyle.red
        self.container.add_item(ui.TextDisplay("## 충전 시간 초과"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("자동충전 시간이 초과되었습니다"))
        await interaction.edit_original_response(view=self)
