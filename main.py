        # (기존 PurchaseModal 내 on_submit 메서드 하단부)
        
        # 3. 제품 구매 시 DM 전송 (후기 버튼 포함)
        try:
            # DM용 컨테이너 생성
            dm_con = ui.Container(ui.TextDisplay("## 📦 구매하신 제품 정보"), accent_color=0x00ff00)
            dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            dm_con.add_item(ui.TextDisplay(
                f"**제품명:** {self.prod_name}\n"
                f"**구매수량:** {buy_count}개\n"
                f"**결제금액:** {total_price:,}원\n"
                f"**구매일시:** {time.strftime('%Y-%m-%d %H:%M:%S')}"
            ))
            dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            dm_con.add_item(ui.TextDisplay("이용해주셔서 감사합니다! 아래 버튼을 눌러 후기를 남겨주세요."))

            # [중요] 후기 작성 버튼 생성 및 연결
            review_btn = ui.Button(label="구매 후기 작성", style=discord.ButtonStyle.primary, emoji="📝")
            
            async def review_btn_callback(it_btn: discord.Interaction):
                # 위에서 만든 ReviewModal을 띄움
                await it_btn.response.send_modal(ReviewModal(self.prod_name))
            
            review_btn.callback = review_btn_callback
            dm_con.add_item(ui.ActionRow(review_btn))

            # 최종 DM 발송
            await it.user.send(view=ui.LayoutView().add_item(dm_con))
            
        except Exception as e:
            print(f"DM 전송 실패: {e}")
