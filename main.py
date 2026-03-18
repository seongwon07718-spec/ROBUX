class PurchaseModal(ui.Modal):
    def __init__(self, prod_name, price, stock):
        super().__init__(title=f"{prod_name} 구매")
        self.prod_name = prod_name
        self.price = price
        self.stock = stock
        
        self.count = ui.TextInput(
            label="구매 수량", 
            placeholder="수량을 입력하세요", 
            min_length=1, 
            max_length=5
        )
        self.add_item(self.count)

    # 구매 로그 웹훅 전송 함수 (새로 추가)
    async def send_purchase_webhook(self, user, prod_name, count, price):
        # ⚠️ 여기에 구매로그 채널의 웹훅 URL을 입력하세요
        WEBHOOK_URL = "본인의_구매로그_웹훅_주소"
        
        dm_con = ui.Container(ui.TextDisplay("## 구매 로그 알림"), accent_color=0xffffff)
        dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        dm_con.add_item(ui.TextDisplay(
            f"구매자: {user} ({user.id})\n"
            f"제품명: {prod_name}\n"
            f"구매 수량: {count}개\n"
            f"결제 금액: {price:,}원"
        ))
        
        dm_v = ui.LayoutView().add_item(dm_con)
        
        try:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
                await webhook.send(view=dm_v)
        except Exception as e:
            print(f"구매 로그 웹훅 전송 실패: {e}")

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
        user_money_res = cur.fetchone()
        user_money = user_money_res[0] if user_money_res else 0

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
        purchased_stock_text = "\n".join(delivery_items) 
        remaining_stock_data = "\n".join(stock_list[buy_count:])

        cur.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (total_price, u_id))
        cur.execute("""UPDATE products 
                       SET stock = stock - ?, 
                           sold_count = sold_count + ?, 
                           stock_data = ? 
                       WHERE name = ?""", (buy_count, buy_count, remaining_stock_data, self.prod_name))
        
        web_key = str(uuid.uuid4())
        
        cur.execute("INSERT INTO buy_log (user_id, product_name, stock_data, date, web_key) VALUES (?, ?, ?, ?, ?)",
                    (u_id, self.prod_name, purchased_stock_text, time.strftime('%Y-%m-%d %H:%M'), web_key))
        conn.commit()
        conn.close()

        # [핵심 추가] 구매 성공 시 웹훅 호출
        await self.send_purchase_webhook(it.user, self.prod_name, buy_count, total_price)

        res_con.accent_color = 0x00ff00; res_con.add_item(ui.TextDisplay(f"## 구매 완료"))
        res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        res_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 제품명: {self.prod_name}\n<:dot_white:1482000567562928271> 구매 수량: {buy_count}개\n<:dot_white:1482000567562928271> 차감 금액: {total_price:,}원"))
        res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        res_con.add_item(ui.TextDisplay("-# DM으로 제품 전송되었습니다"))
        await it.edit_original_response(view=ui.LayoutView().add_item(res_con))
