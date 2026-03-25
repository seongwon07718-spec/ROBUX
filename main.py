class RobuxMenu(ui.LayoutView):
    def __init__(self):
        super().__init__()
        con = ui.Container()
        con.accent_color = 0xffffff
        con.add_item(ui.TextDisplay("## 구매하기"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay("아래 버튼을 눌려 이용해주세요"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        row = ui.ActionRow(buy, shop, chage, info)

        buy = ui.Button(label="공지", emoji="<:emoji_16:1486337864953495743>")
        buy.callback = self.buy_callback
        
        shop = ui.Button(label="제품", emoji="<:emoji_13:1486337836796874905>")
        shop.callback = self.shop_callback
        
        chage = ui.Button(label="충전", emoji="<:emoji_14:1486337849367330857>")
        chage.callback = self.main_callback
        
        info = ui.Button(label="정보", emoji="<:emoji_13:1486337822989484212>")
        info.callback = self.info_callback
        
        con.add_item(row)
        self.add_item(con)

    async def main_callback(self, it: discord.Interaction):
        cid = it.data['custom_id']
        if cid == "charge":
            con = ui.Container()
            con.accent_color = 0xffffff
            con.add_item(ui.TextDisplay("## 충전 수단 선택"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("원하시는 충전 방식을 선택해주세요"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            
        btn_bank = ui.Button(label="계좌이체", style=discord.ButtonStyle.gray)
        async def bank_cb(i: discord.Interaction):
            await i.response.send_modal(ChargeModal())
        btn_bank.callback = bank_cb
        
        con.add_item(ui.ActionRow(btn_bank))
        
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
