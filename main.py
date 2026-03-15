        # 1. 보안 키(UUID) 생성 (남이 재고를 추측해서 털어가는 것 방지)
        import uuid
        web_key = str(uuid.uuid4())

        # 2. 구매 로그 저장 (web_key 컬럼 포함)
        # 테이블에 web_key 컬럼이 반드시 있어야 합니다. (init_db에서 추가한 버전 사용)
        cur.execute("INSERT INTO buy_log (user_id, product_name, stock_data, date, web_key) VALUES (?, ?, ?, ?, ?)",
                    (u_id, self.prod_name, purchased_stock_text, time.strftime('%Y-%m-%d %H:%M'), web_key))

        conn.commit()
        conn.close()

        # 3. 결과 메시지 업데이트
        res_con.accent_color = 0x00ff00; res_con.add_item(ui.TextDisplay(f"## 구매 완료"))
        res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        res_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 제품명: {self.prod_name}\n<:dot_white:1482000567562928271> 구매 수량: {buy_count}개\n<:dot_white:1482000567562928271> 차감 금액: {total_price:,}원"))
        res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        res_con.add_item(ui.TextDisplay("-# DM으로 제품 전송되었습니다"))
        await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

        try:
            # 4. 보안 URL 생성 (88번 포트 사용 및 key 파라미터 적용)
            domain = "rbxshop.cloud:88" 
            view_url = f"http://{domain}/view?key={web_key}"

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
