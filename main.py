class AdminLogView(ui.LayoutView):
    def __init__(self, user, name, amount, db_id):
        super().__init__(); self.user, self.name, self.amount, self.db_id = user, name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 충전 신청"), accent_color=0xffff00)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**신청자:** {user.mention}\n**입금자명:** {name}\n**신청금액:** {amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        approve_btn = ui.Button(label="완료", style=discord.ButtonStyle.green); approve_btn.callback = self.approve_callback
        cancel_btn = ui.Button(label="취소", style=discord.ButtonStyle.red); cancel_btn.callback = self.cancel_callback
        self.container.add_item(ui.ActionRow(approve_btn, cancel_btn)); self.add_item(self.container)
    async def approve_callback(self, interaction: discord.Interaction):
        database.update_status(self.db_id, "완료"); self.container.clear_items(); self.container.accent_color = 0x00ff00
        self.container.add_item(ui.TextDisplay(f"## 충전 완료")); self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**처리자:** {interaction.user.mention}\n**대상:** {self.user.mention}\n**금액:** {self.amount}원"))
        await interaction.response.edit_message(view=self)
        try: await self.user.send(f"**{self.amount}원 충전이 완료되었습니다**")
        except: pass
    async def cancel_callback(self, interaction: discord.Interaction):
        database.update_status(self.db_id, "취소"); self.container.clear_items(); self.container.accent_color = 0xff0000
        self.container.add_item(ui.TextDisplay(f"## 충전 취소")); self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**처리자:** {interaction.user.mention}\n**대상:** {self.user.mention}\n**금액:** {self.amount}원"))
        await interaction.response.edit_message(view=self)
