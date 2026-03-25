        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        buy = ui.Button(label="공지", emoji="📢")
        buy.callback = self.buy_callback
        
        shop = ui.Button(label="구매", emoji="🛒")
        shop.callback = self.shop_callback
        
        charge = ui.Button(label="충전", emoji="💳", custom_id="charge")
        charge.callback = self.main_callback
        
        info = ui.Button(label="정보", emoji="👤")
        info.callback = self.info_callback
        
        row_btns = ui.ActionRow(buy, shop, charge, info)
        con.add_item(row_btns)
        
        # 중요: 이 시점에서 self(View)에 con을 추가
        self.add_item(con)
        return con # 이미지의 'NoneType' 에러를 해결하기 위해 con을 반환

    # ... (callback 함수들은 기존과 동일)

# --- 명령어 및 태스크 부분 수정 ---
@bot.tree.command(name="자판기", description="실시간 재고 자판기를 소환합니다.")
async def spawn_vending(it: discord.Interaction):
    view = RobuxVending(bot)
    con = await view.build_main_menu()
    
    # 이미 view.add_item(con)이 내부에서 실행되었으므로 view를 그대로 전송
    await it.response.send_message(view=view)
    msg = await it.original_response()
    bot.vending_msg_info[it.channel_id] = msg.id

# stock_updater 내부 루프 수정
# ...
                msg = await channel.fetch_message(msg_id)
                v_view = RobuxVending(self)
                await v_view.build_main_menu() # 내부에서 add_item 수행됨
                await msg.edit(view=v_view)
# ...

