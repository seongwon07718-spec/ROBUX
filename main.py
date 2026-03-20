async def on_submit(self, it: discord.Interaction):
    # --- 이 줄을 추가해서 응답 시간을 벌고 중복 응답 에러를 방지합니다 ---
    await it.response.defer(ephemeral=True) 
    
    # ... 기존 로직 (재고 차감, DB 업데이트 등) ...

    # 385번 줄 근처 (기존 코드)
    await self.send_purchase_webhook(it.user, self.prod_name, buy_count, total_price)

    res_con.accent_color = 0x00ff00; res_con.add_item(ui.TextDisplay(f"## 구매 완료"))
    # ... (중략) ...

    # edit_original_response는 defer 이후에 사용하면 안전합니다.
    await it.edit_original_response(view=ui.LayoutView().add_item(res_con))
