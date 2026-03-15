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
            cur.execute("SELECT name, price, stock, sold_count FROM products WHERE category = ?", (selected,))
            products = cur.fetchall(); conn.close()

            if products:
                item_text = "\n".join([
                    f"<:dot_white:1482000567562928271> 제품: {p[0]}\n"
                    f"<:dot_white:1482000567562928271> 가격: {p[1]:,}원\n"
                    f"<:dot_white:1482000567562928271> 재고: {p[2]}개 / 누적 판매: {p[3]}개" 
                    for p in products
                ])
            else:
                item_text = "제품이 없습니다"
            
            res_con = ui.Container(ui.TextDisplay(f"## {selected} 제품 목록"), accent_color=0xffffff)
            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.TextDisplay(f"{item_text}"))
            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.ActionRow(cat_select))
            
            await interaction.response.edit_message(view=ui.LayoutView().add_item(res_con))

        cat_select.callback = cat_callback
        cat_con.add_item(ui.ActionRow(cat_select))
        await it.response.send_message(view=ui.LayoutView().add_item(cat_con), ephemeral=True)
    async def chage_callback(self, it: discord.Interaction):
        if await check_black(it): return
        await it.response.send_message(view=ChargeLayout(), ephemeral=True)
    async def buy_callback(self, it: discord.Interaction):
        if await check_black(it): return

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products WHERE stock > 0") 
        cats = [row[0] for row in cur.fetchall()]
        conn.close()

        if not cats:
            return await it.response.send_message("❌ 현재 구매 가능한 제품이 없습니다.", ephemeral=True)

        cat_con = ui.Container(ui.TextDisplay(f"## 카테고리 선택하기"), accent_color=0xffffff)
        cat_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        cat_con.add_item(ui.TextDisplay("구매할 제품 카테고리를 선택해주세요"))
        cat_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        cat_options = [discord.SelectOption(label=c, value=c) for c in cats]
        cat_select = ui.Select(placeholder="카테고리를 선택하세요", options=cat_options)

        async def cat_callback(it2: discord.Interaction):
            selected_cat = cat_select.values[0]
            
            conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
            cur.execute("SELECT name, price, stock, sold_count FROM products WHERE category = ? AND stock > 0", (selected_cat,))
            prods = cur.fetchall(); conn.close()

            prod_con = ui.Container(ui.TextDisplay(f"## 제품 선택하기"), accent_color=0xffffff)
            prod_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            prod_con.add_item(ui.TextDisplay("구매할 제품을 선택해주세요"))
            prod_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            prod_options = [
    discord.SelectOption(
        label=f"{p[0]}", 
        description=f"제품 가격: {p[1]:,}원ㅣ남은 재고: {p[2]}개ㅣ누적 판매: {p[3]}개",
        value=f"{p[0]}|{p[1]}|{p[2]}"
    ) for p in prods
]
            prod_select = ui.Select(placeholder="구매하실 제품을 선택하세요", options=prod_options)

            async def prod_callback(it3: discord.Interaction):
                p_name, p_price, p_stock = prod_select.values[0].split('|') 
                await it3.response.send_modal(PurchaseModal(p_name, int(p_price), int(p_stock)))

            prod_select.callback = prod_callback
            prod_con.add_item(ui.ActionRow(prod_select))
            await it2.response.edit_message(view=ui.LayoutView().add_item(prod_con))
