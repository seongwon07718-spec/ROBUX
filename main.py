        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### <:emoji_18:1487422236838334484>  지급방식\n-# - 겜패 선물 방식\n-# - 인게임 선물 방식"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay("### <:emoji_18:1487422236838334484>  실시간 재고\n"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay(f"### <:emoji_18:1487422236838334484>  버튼 안내\n-# - **Charge** - 충전하기 / 24시간 자동 충전\n-# - **Info** - 내 정보 / 거래내역 확인하기\n-# - **Buying** - 로벅스 구매하기 / 24시간 구매 가능"))

        charge = ui.Button(label="Charge", custom_id="charge", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        charge.callback = self.main_callback
        
        info = ui.Button(label="Info", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        info.callback = self.info_callback

        shop = ui.Button(label="Buying", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        shop.callback = self.shop_callback
        
        row_btns = ui.ActionRow(charge, info, shop)
        con.add_item(row_btns)
        self.add_item(con)
        return con
