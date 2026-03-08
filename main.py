# --- [ 구매 수량 입력 모달 ] ---
class PurchaseModal(ui.Modal):
    def __init__(self, prod_name, price, stock):
        super().__init__(title=f"{prod_name} 구매")
        self.prod_name = prod_name
        self.price = price
        self.stock = stock
        self.count = ui.TextInput(label="구매 수량", placeholder=f"수량을 입력하세요 (현재 재고: {stock}개)", min_length=1, max_length=5)
        self.add_item(self.count)

    async def on_submit(self, it: discord.Interaction):
        if not self.count.value.isdigit():
            return await it.response.send_message("❌ 숫자로만 입력해주세요.", ephemeral=True)
        
        buy_count = int(self.count.value)
        total_price = self.price * buy_count
        u_id = str(it.user.id)

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()

        # 1. 유저 잔액 및 제품 재고 확인
        cur.execute("SELECT money FROM users WHERE user_id = ?", (u_id,))
        user_money = cur.fetchone()
        user_money = user_money[0] if user_money else 0

        if buy_count > self.stock:
            return await it.response.send_message(f"❌ 재고가 부족합니다. (현재 재고: {self.stock}개)", ephemeral=True)
        
        if user_money < total_price:
            return await it.response.send_message(f"❌ 잔액이 부족합니다. (필요 금액: {total_price:,}원 / 보유: {user_money:,}원)", ephemeral=True)

        # 2. 잔액 차감 및 재고 차감 처리
        cur.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (total_price, u_id))
        cur.execute("UPDATE products SET stock = stock - ? WHERE name = ?", (buy_count, self.prod_name))
        
        # 3. 구매 로그 기록 (선택 사항)
        cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                    (u_id, -total_price, time.strftime('%Y-%m-%d %H:%M'), f"제품구매({self.prod_name} x {buy_count})"))
        
        conn.commit()
        conn.close()

        # 4. 완료 컨테이너 전송
        res_con = ui.Container(ui.TextDisplay(f"## 🎉 구매 완료"), accent_color=0x00ff00)
        res_con.add_item(ui.TextDisplay(f"제품명: **{self.prod_name}**\n구매 수량: **{buy_count}개**\n차감 금액: **{total_price:,}원**\n\n구매가 성공적으로 완료되었습니다!"))
        
        await it.response.send_message(view=ui.LayoutView().add_item(res_con), ephemeral=True)

# --- [ MeuLayout 내 구매 콜백 ] ---
class MeuLayout(ui.LayoutView):
    # ... (기존 코드 생략)

    async def buy_callback(self, it: discord.Interaction):
        if await check_black(it): return

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products WHERE stock > 0") # 재고 있는 카테고리만
        cats = [row[0] for row in cur.fetchall()]
        conn.close()

        if not cats:
            return await it.response.send_message("❌ 현재 구매 가능한 제품이 없습니다.", ephemeral=True)

        # 1단계: 카테고리 선택
        cat_con = ui.Container(ui.TextDisplay("## 🛒 구매 - 카테고리 선택"), accent_color=0x5865F2)
        cat_options = [discord.SelectOption(label=c, value=c) for c in cats]
        cat_select = ui.Select(placeholder="카테고리를 선택하세요", options=cat_options)

        async def cat_callback(it2: discord.Interaction):
            selected_cat = cat_select.values[0]
            
            # 2단계: 제품 선택 시칼렛 생성
            conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
            cur.execute("SELECT name, price, stock FROM products WHERE category = ? AND stock > 0", (selected_cat,))
            prods = cur.fetchall(); conn.close()

            prod_con = ui.Container(ui.TextDisplay(f"## 📦 {selected_cat} - 제품 선택"), accent_color=0x5865F2)
            prod_options = [discord.SelectOption(label=f"{p[0]} ({p[1]:,}원)", value=f"{p[0]}|{p[1]}|{p[2]}") for p in prods]
            prod_select = ui.Select(placeholder="구매하실 제품을 선택하세요", options=prod_options)

            async def prod_callback(it3: discord.Interaction):
                # 선택된 값 분리 (이름|가격|재고)
                p_name, p_price, p_stock = prod_select.values[0].split('|')
                # 3단계: 수량 입력 모달 띄우기
                await it3.response.send_modal(PurchaseModal(p_name, int(p_price), int(p_stock)))

            prod_select.callback = prod_callback
            prod_con.add_item(ui.ActionRow(prod_select))
            await it2.response.edit_message(view=ui.LayoutView().add_item(prod_con))

        cat_select.callback = cat_callback
        cat_con.add_item(ui.ActionRow(cat_select))
        await it.response.send_message(view=ui.LayoutView().add_item(cat_con), ephemeral=True)
