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
            conn.close()
            return await it.edit_original_response(view=ui.LayoutView().add_item(res_con))
        
        if user_money < total_price:
            res_con.accent_color = 0xff0000; res_con.add_item(ui.TextDisplay("## 잔액 부족"))
            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.TextDisplay(f"(필요: {total_price:,}원 / 보유: {user_money:,}원)"))
            conn.close()
            return await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

        cur.execute("SELECT stock_data FROM products WHERE name = ?", (self.prod_name,))
        stock_res = cur.fetchone()
        stock_list = stock_res[0].split('\n') if stock_res and stock_res[0] else []
        
        delivery_items = stock_list[:buy_count]
        remaining_stock_data = "\n".join(stock_list[buy_count:])

        cur.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (total_price, u_id))
        cur.execute("""UPDATE products 
                       SET stock = stock - ?, 
                           sold_count = sold_count + ?, 
                           stock_data = ? 
                       WHERE name = ?""", (buy_count, buy_count, remaining_stock_data, self.prod_name))
        
        cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                    (u_id, -total_price, time.strftime('%Y-%m-%d %H:%M'), f"제품구매({self.prod_name} x {buy_count})"))
        
        conn.commit()
        conn.close()

        res_con.accent_color = 0x00ff00; res_con.add_item(ui.TextDisplay(f"## 구매 완료"))
        res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        res_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 제품명: {self.prod_name}\n<:dot_white:1482000567562928271> 구매 수량: {buy_count}개\n<:dot_white:1482000567562928271> 차감 금액: {total_price:,}원"))
        res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        res_con.add_item(ui.TextDisplay("-# DM으로 제품 전송되었습니다"))
        await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

        try:
            domain = "rbxshop.cloud"
            safe_prod_name = urllib.parse.quote(self.prod_name)
            view_url = f"https://{domain}/view?user={it.user.id}&product={safe_prod_name}"

            dm_con = ui.Container(ui.TextDisplay("## 구매 제품"), accent_color=0xffffff)
            dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            dm_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 제품명: {self.prod_name}\n<:dot_white:1482000567562928271> 구매수량: {buy_count}개\n<:dot_white:1482000567562928271> 결제금액: {total_price:,}원\n<:dot_white:1482000567562928271> 남은 잔액: {user_money - total_price:,}원"))
            dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            review_btn = ui.Button(label="후기작성", style=discord.ButtonStyle.gray, emoji="<:bel:1482196301578764308>")
            async def review_btn_callback(it_btn: discord.Interaction):
                await it_btn.response.send_modal(ReviewModal(self.prod_name))
            review_btn.callback = review_btn_callback
            
            view_btn = ui.Button(
    label="제품보기", 
    url=view_url, 
    style=discord.ButtonStyle.link,
    emoji="<:shop:1481994009499930766>"
)
            
            dm_con.add_item(ui.ActionRow(review_btn, view_btn))
            
            await it.user.send(view=ui.LayoutView().add_item(dm_con))

        except Exception as e:
            print(f"DM 전송 실패: {e}")
