        try:
            dm_con = ui.Container(ui.TextDisplay("## 구매 제품"), accent_color=0xffffff)
            dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            dm_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 제품명: {self.prod_name}\n<:dot_white:1482000567562928271> 구매수량: {buy_count}개\n<:dot_white:1482000567562928271> 결제금액: {total_price:,}원\n<:dot_white:1482000567562928271> 남은 잔액: {user_money - total_price:,}원"))
            dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            review_btn = ui.Button(label="후기작성", style=discord.ButtonStyle.gray, emoji="<:bel:1482196301578764308>")
            async def review_btn_callback(it_btn: discord.Interaction):
                await it_btn.response.send_modal(ReviewModal(self.prod_name))
            review_btn.callback = review_btn_callback
            dm_con.add_item(ui.ActionRow(review_btn)); self.add_item(dm_con)
            await it.user.send(view=ui.LayoutView().add_item(dm_con))
        except Exception as e:
            print(f"DM 전송 실패: {e}")
