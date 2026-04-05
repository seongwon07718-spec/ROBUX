    async def shop_callback(self, it: discord.Interaction):
        con = ui.Container()
        con.accent_color = 0x5865F2
        
        con.add_item(ui.TextDisplay("### <:acy2:1489883409001091142>  구매 방식 선택"))
        con.add_item(ui.TextDisplay("-# - 원하시는 구매 방식을 선택해주세요\n-# - 현재는 **게임패스 방식**만 지원됩니다"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        btn_gp = ui.Button(label="게임패스 방식", style=discord.ButtonStyle.gray, emoji="<:opt_online:1489872305138962452>")
        btn_ingame = ui.Button(label="글로벌 선물 방식", style=discord.ButtonStyle.gray, emoji="<:opt_offline:1489886702368723087>", disabled = True)
        btn_group = ui.Button(label="그룹 지급 방식", style=discord.ButtonStyle.gray, emoji="<:opt_offline:1489886702368723087>", disabled = True)

        async def method_callback(interaction):
            await interaction.response.send_message(f"**{interaction.data['label']}** 방식 상품 준비 중입니다.", ephemeral=True)
        
        btn_gp.callback = method_callback
        btn_gp.callback = lambda i: i.response.send_modal(NicknameSearchModal())
        btn_ingame.callback = method_callback
        btn_group.callback = method_callback

        con.add_item(ui.ActionRow(btn_gp, btn_group, btn_ingame))
        
        new_view = ui.LayoutView(timeout=None)
        new_view.add_item(con)
        
        await it.response.send_message(view=new_view, ephemeral=True)
