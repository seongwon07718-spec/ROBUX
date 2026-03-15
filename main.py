class PurchaseModal(ui.Modal):
    def __init__(self, prod_name, price, stock):
        super().__init__(title=f"{prod_name} 구매")
        self.prod_name = prod_name
        self.price = price
        self.stock = stock
        self.count = ui.TextInput(label="구매 수량", placeholder=f"수량을 입력하세요", min_length=1, max_length=5)
        self.add_item(self.count)

    async def on_submit(self, it: discord.Interaction):
        if not self.count.value.isdigit():
            err_con = ui.Container(ui.TextDisplay("## ❌ 입력 오류"), accent_color=0xff0000)
            err_con.add_item(ui.TextDisplay("숫자로만 입력해주세요."))
            return await it.response.send_message(view=ui.LayoutView().add_item(err_con), ephemeral=True)
        
        buy_count = int(self.count.value)
        total_price = self.price * buy_count
        u_id = str(it.user.id)

        wait_con = ui.Container(ui.TextDisplay("## 구매 진행 중"), accent_color=0xffff00)
        wait_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        wait_con.add_item(ui.TextDisplay(f"**<a:027:1482026501279977574>  구매 처리 진행중입니다**"))
        await it.response.send_message(view=ui.LayoutView().add_item(wait_con), ephemeral=True)

        await asyncio.sleep(3.0)

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        cur.execute("SELECT money FROM users WHERE user_id = ?", (u_id,))
        user_money = cur.fetchone()
        user_money = user_money[0] if user_money else 0

        res_con = ui.Container()
        if buy_count > self.stock:
            res_con.accent_color = 0xff0000; res_con.add_item(ui.TextDisplay("## 재고 부족"))
            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.TextDisplay(f"(현재 재고: {self.stock}개)"))
            return await it.edit_original_response(view=ui.LayoutView().add_item(res_con))
        
        if user_money < total_price:
            res_con.accent_color = 0xff0000; res_con.add_item(ui.TextDisplay("## 잔액 부족"))
            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.TextDisplay(f"(필요: {total_price:,}원 / 보유: {user_money:,}원)"))
            return await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

        cur.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (total_price, u_id))
        cur.execute("UPDATE products SET stock = stock - ? WHERE name = ?", (buy_count, self.prod_name))
        cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                    (u_id, -total_price, time.strftime('%Y-%m-%d %H:%M'), f"제품구매({self.prod_name} x {buy_count})"))
        conn.commit(); conn.close()


      async def shop_callback(self, it: discord.Interaction):
        if await check_black(it): return
        
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



