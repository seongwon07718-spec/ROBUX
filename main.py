        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products")
        categories = [row[0] for row in cur.fetchall()]
        conn.close()

        if not categories:
            return await it.response.send_message("현재 등록된 제품 카테고리가 없습니다.", ephemeral=True)

        cat_con = ui.Container(ui.TextDisplay("## 카테고리 선택"), accent_color=0xffffff)
        cat_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        cat_con.add_item(ui.TextDisplay("원하시는 제품의 카테고리를 선택해주세요"))
        cat_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        options = [discord.SelectOption(label=cat, value=cat) for cat in categories]
        cat_select = ui.Select(placeholder="카테고리를 선택하세요", options=options)

        async def cat_callback(interaction: discord.Interaction):
            selected = cat_select.values[0]
            
            conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
            cur.execute("SELECT name, price, stock FROM products WHERE category = ?", (selected,))
            products = cur.fetchall(); conn.close()

            item_text = "\n".join([f"<:dot_white:1482000567562928271> 제품: {p[0]}\n<:dot_white:1482000567562928271> 가격: {p[1]:,}원\n<:dot_white:1482000567562928271> 재고: {p[2]}개 / 누적 판매: " for p in products]) if products else "제품이 없습니다"
            
            res_con = ui.Container(ui.TextDisplay(f"## {selected} 제품 목록"), accent_color=0xffffff)
            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.TextDisplay(f"{item_text}"))
            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.ActionRow(cat_select))
            
            await interaction.response.edit_message(view=ui.LayoutView().add_item(res_con))
