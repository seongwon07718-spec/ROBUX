class MeuLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None) 
        self.container = ui.Container(ui.TextDisplay("## 구매하기"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("아래 버튼을 눌려 이용해주세요"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 버튼 정의 및 콜백 연결
        buy = ui.Button(label="구매", emoji="<:buy:1481994292255002705>")
        buy.callback = self.buy_callback
        
        shop = ui.Button(label="제품", emoji="<:shop:1481994009499930766>")
        shop.callback = self.shop_callback
        
        chage = ui.Button(label="충전", emoji="<:change:1481994723802611732>")
        chage.callback = self.chage_callback
        
        info = ui.Button(label="정보", emoji="<:info:1481993647774892043>")
        info.callback = self.info_callback
        
        self.container.add_item(ui.ActionRow(buy, shop, chage, info))
        self.add_item(self.container)

    # --- [1] 정보 조회 콜백 ---
    async def info_callback(self, it: discord.Interaction):
        if await check_black(it): return
        
        u_id = str(it.user.id)
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT money, total_spent FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone(); conn.close()
        
        money, total_spent = (row[0], row[1]) if row else (0, 0)
        
        container = ui.Container(ui.TextDisplay(f"## {it.user.display_name}님의 정보"), accent_color=0xffffff)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        container.add_item(ui.TextDisplay(
            f"<:dot_white:1482000567562928271> 보유 잔액: {money:,}원\n"
            f"<:dot_white:1482000567562928271> 누적 금액: {total_spent:,}원"
        ))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        selecao = ui.Select(placeholder="조회할 내역 선택", options=[
            discord.SelectOption(label="최근 충전 내역", value="charge", emoji="<:dot_white:1482000567562928271>"),
            discord.SelectOption(label="최근 구매 내역", value="purchase", emoji="<:dot_white:1482000567562928271>")
        ])

        async def res_callback(i: discord.Interaction):
            selected_val = selecao.values[0]
            conn2 = sqlite3.connect('vending_data.db'); cur2 = conn2.cursor()
            
            if selected_val == "charge":
                cur2.execute("SELECT amount, date, method FROM charge_logs WHERE user_id = ? AND amount > 0 ORDER BY date DESC LIMIT 5", (u_id,))
                logs = cur2.fetchall(); conn2.close()
                log_con = ui.Container(ui.TextDisplay("## 최근 충전 내역"), accent_color=0xffffff)
                if logs:
                    for l in logs:
                        log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                        log_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 금액: {l[0]:,}원 ({l[2]})\n<:dot_white:1482000567562928271> 시간: {l[1]}"))
                else:
                    log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    log_con.add_item(ui.TextDisplay("충전 내역이 없습니다"))
            
            elif selected_val == "purchase":
                cur2.execute("SELECT amount, date, method FROM charge_logs WHERE user_id = ? AND amount < 0 ORDER BY date DESC LIMIT 5", (u_id,))
                logs = cur2.fetchall(); conn2.close()
                log_con = ui.Container(ui.TextDisplay("## 최근 구매 내역"), accent_color=0xffffff)
                if logs:
                    for l in logs:
                        log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                        log_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 금액: {abs(l[0]):,}원 ({l[2].replace('제품구매(', '').replace(')', '')})\n<:dot_white:1482000567562928271> 시간: {l[1]}"))
                else:
                    log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    log_con.add_item(ui.TextDisplay("구매 내역이 없습니다"))
                
            await i.response.send_message(view=ui.LayoutView().add_item(log_con), ephemeral=True)
            
        selecao.callback = res_callback
        container.add_item(ui.ActionRow(selecao))
        await it.response.send_message(view=ui.LayoutView().add_item(container), ephemeral=True)

    # --- [2] 제품 목록 콜백 ---
    async def shop_callback(self, it: discord.Interaction):
        if await check_black(it): return
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products")
        categories = [row[0] for row in cur.fetchall()]; conn.close()
        
        if not categories:
            return await it.response.send_message("**현재 등록된 제품 카테고리가 없습니다**", ephemeral=True)
            
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
            res_con = ui.Container(ui.TextDisplay(f"## {selected} 제품 목록"), accent_color=0xffffff)
            if products:
                for p in products:
                    res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    item_info = (f"<:dot_white:1482000567562928271> 제품: {p[0]}\n<:dot_white:1482000567562928271> 가격: {p[1]:,}원\n<:dot_white:1482000567562928271> 재고: {p[2]}개 / 누적 판매: {p[3]}개")
                    res_con.add_item(ui.TextDisplay(item_info))
            else:
                res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                res_con.add_item(ui.TextDisplay("등록된 제품이 없습니다."))
            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.ActionRow(cat_select))
            await interaction.response.edit_message(view=ui.LayoutView().add_item(res_con))
            
        cat_select.callback = cat_callback
        cat_con.add_item(ui.ActionRow(cat_select))
        await it.response.send_message(view=ui.LayoutView().add_item(cat_con), ephemeral=True)

    # --- [3] 충전 콜백 ---
    async def chage_callback(self, it: discord.Interaction):
        if await check_black(it): return
        await it.response.send_message(view=ChargeLayout(), ephemeral=True)

    # --- [4] 구매 콜백 ---
    async def buy_callback(self, it: discord.Interaction):
        if await check_black(it): return
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products WHERE stock > 0") 
        cats = [row[0] for row in cur.fetchall()]; conn.close()
        
        if not cats:
            return await it.response.send_message("**현재 구매 가능한 제품이 없습니다**", ephemeral=True)
            
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
            
            prod_options = [discord.SelectOption(label=f"{p[0]}", description=f"가격: {p[1]:,}원 ㅣ 재고: {p[2]}개 ㅣ 누적 판매: {p[3]}개", value=f"{p[0]}|{p[1]}|{p[2]}") for p in prods]
            prod_select = ui.Select(placeholder="구매하실 제품을 선택하세요", options=prod_options)
            
            async def prod_callback(it3: discord.Interaction):
                v = prod_select.values[0].split('|')
                await it3.response.send_modal(PurchaseModal(v[0], int(v[1]), int(v[2])))
                
            prod_select.callback = prod_callback
            prod_con.add_item(ui.ActionRow(prod_select))
            await it2.response.edit_message(view=ui.LayoutView().add_item(prod_con))
            
        cat_select.callback = cat_callback
        cat_con.add_item(ui.ActionRow(cat_select))
        await it.response.send_message(view=ui.LayoutView().add_item(cat_con), ephemeral=True)
