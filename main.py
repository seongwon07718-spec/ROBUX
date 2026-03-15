        try:
            # --- 제품 데이터 가공 (웹으로 넘길 값들) ---
            # DB에서 가져온 stock_data 중 구매한 수량만큼의 데이터를 웹 주소 뒤에 파라미터로 붙이거나, 
            # 단순히 도메인 메인으로 연결할 수 있습니다.
            domain = "yourdomain.com" # 보유하신 도메인 주소로 수정하세요
            view_url = f"https://{domain}/view?user={it.user.id}&product={self.prod_name}"

            dm_con = ui.Container(ui.TextDisplay("## 구매 제품"), accent_color=0xffffff)
            dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            dm_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 제품명: {self.prod_name}\n<:dot_white:1482000567562928271> 구매수량: {buy_count}개\n<:dot_white:1482000567562928271> 결제금액: {total_price:,}원\n<:dot_white:1482000567562928271> 남은 잔액: {user_money - total_price:,}원"))
            dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            # 1. 후기작성 버튼 (기존)
            review_btn = ui.Button(label="후기작성", style=discord.ButtonStyle.gray, emoji="<:bel:1482196301578764308>")
            async def review_btn_callback(it_btn: discord.Interaction):
                await it_btn.response.send_modal(ReviewModal(self.prod_name))
            review_btn.callback = review_btn_callback
            
            # 2. 제품보기 버튼 (신규 - 웹 이동)
            # URL 버튼은 callback이 필요 없으며 클릭 시 바로 브라우저가 열립니다.
            view_btn = ui.Button(label="제품보기", url=view_url, emoji="<:shop:1481994009499930766>")
            
            # 버튼들을 한 줄(ActionRow)에 배치
            dm_con.add_item(ui.ActionRow(review_btn, view_btn))
            
            # 전송 로직
            await it.user.send(view=ui.LayoutView().add_item(dm_con))

        except Exception as e:
            print(f"DM 전송 실패: {e}")
