class MeuLayout(ui.LayoutView):
    # ... (기존 __init__ 생략)

    async def shop_callback(self, it: discord.Interaction):
        if await check_black(it): return
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        # 현재 DB에 등록된 모든 카테고리 중복 없이 가져오기
        cur.execute("SELECT DISTINCT category FROM products")
        categories = [row[0] for row in cur.fetchall()]
        conn.close()

        if not categories:
            return await it.response.send_message("현재 등록된 제품 카테고리가 없습니다.", ephemeral=True)

        cat_con = ui.Container(ui.TextDisplay("## 📂 카테고리 선택"), accent_color=0x5865F2)
        options = [discord.SelectOption(label=cat, value=cat) for cat in categories]
        cat_select = ui.Select(placeholder="카테고리를 선택하세요", options=options)

        async def cat_callback(interaction: discord.Interaction):
            selected = cat_select.values[0]
            
            # DB에서 해당 카테고리의 제품 정보 실시간 조회
            conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
            cur.execute("SELECT name, price, stock FROM products WHERE category = ?", (selected,))
            products = cur.fetchall(); conn.close()

            item_text = "\n".join([f"• **{p[0]}** - {p[1]:,}원 (재고: {p[2]}개)" for p in products]) if products else "제품이 없습니다."
            
            res_con = ui.Container(ui.TextDisplay(f"## 📦 {selected} 목록"), accent_color=0x00ff00)
            res_con.add_item(ui.TextDisplay(f"### {selected} 카테고리 실시간 리스트\n\n{item_text}"))
            res_con.add_item(ui.ActionRow(cat_select))
            
            await interaction.response.edit_message(view=ui.LayoutView().add_item(res_con))

        cat_select.callback = cat_callback
        cat_con.add_item(ui.ActionRow(cat_select))
        await it.response.send_message(view=ui.LayoutView().add_item(cat_con), ephemeral=True)
