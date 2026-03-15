        cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                    (u_id, -total_price, time.strftime('%Y-%m-%d %H:%M'), f"제품구매({self.prod_name} x {buy_count})"))
        
        cur.execute("INSERT INTO buy_log (user_id, product_name, stock_data) VALUES (?, ?, ?)",
                    (u_id, self.prod_name, purchased_stock_text))
        buy_id = cur.lastrowid

        conn.commit()
        conn.close()

        res_con.accent_color = 0x00ff00; res_con.add_item(ui.TextDisplay(f"## 구매 완료"))
        res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        res_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 제품명: {self.prod_name}\n<:dot_white:1482000567562928271> 구매 수량: {buy_count}개\n<:dot_white:1482000567562928271> 차감 금액: {total_price:,}원"))
        res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        res_con.add_item(ui.TextDisplay("-# DM으로 제품 전송되었습니다"))
        await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

        try:
            domain = "rbxshop.cloud:88" 
            view_url = f"http://{domain}/view?id={buy_id}"

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
            
            dm_v = ui.LayoutView().add_item(dm_con)
            dm_v.add_item(ui.ActionRow(review_btn, view_btn))
            await it.user.send(view=dm_v)

        except Exception as e:
            print(f"DM 전송 실패: {e}")
