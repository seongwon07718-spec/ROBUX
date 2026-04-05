    async def info_callback(self, it: discord.Interaction):
        
        u_id = str(it.user.id)
        money = 0
        try:
            conn = sqlite3.connect('robux_shop.db')
            cur = conn.cursor()
            cur.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
            row = cur.fetchone()
            conn.close()
            if row: money = row[0]
        except: pass

        roles = [role.name for role in it.user.roles if role.name != "@everyone"]
        role_grade = roles[-1] if roles else "Guest"

        con = ui.Container()
        con.accent_color = 0x5865F2

        con.add_item(ui.TextDisplay(
            f"### <:emoji_19:1487441741484392498>  {it.user.display_name} 님의 정보"))
        
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        info_text = (
            f"-# - **보유 잔액:** `{money:,}원`\n"
            f"-# - **사용 금액:** `0원`\n"
            f"-# - **역할 등급:** `{role_grade}`\n"
            f"-# - **할인 혜택:** `0%`"
        )
        con.add_item(ui.TextDisplay(info_text))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        selecao = ui.Select(placeholder="조회할 내역 선택해주세요", options=[
            discord.SelectOption(label="최근 충전 내역", value="charge"),
            discord.SelectOption(label="최근 구매 내역", value="purchase")
        ])
        
        async def res_cb(i: discord.Interaction):
            await i.response.send_message(f"{selecao.values[0]} 내역이 없습니다", ephemeral=True)
        selecao.callback = res_cb
        
        con.add_item(ui.ActionRow(selecao))
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
