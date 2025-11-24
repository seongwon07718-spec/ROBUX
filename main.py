@tasks.loop(seconds=120)
async def update_embed_task():
    global embed_message, current_stock, current_rate, last_update_time, embed_updating, api_update_counter, timer_message, stop_event
    
    try:
        if embed_message is None:
            return
        
        embed_updating = True
        
        api_update_counter += 1
        if api_update_counter >= 1:
            new_stock = get_stock_amount()
            new_rate = get_exchange_rate()
            
            if new_stock != current_stock or new_rate != current_rate:
                current_stock = new_stock
                current_rate = new_rate
            
            api_update_counter = 0
            
        last_update_time = datetime.now()
        
        # 모든 코인 잔액 조회
        all_balances = coin.get_all_balances()
        all_prices = coin.get_all_coin_prices()
        
        # 지원하는 코인들만 표시 (USDT, BNB, TRX, LTC)
        supported_coins = ['USDT', 'BNB', 'TRX', 'LTC']
        balance_text = ""
        total_krw_value = 0
        
        for coin_symbol in supported_coins:
            balance = all_balances.get(coin_symbol, 0)
            if balance > 0:
                price = all_prices.get(coin_symbol, 0)
                krw_value = balance * price * current_rate
                total_krw_value += krw_value
                balance_text += f"**```🛒 {krw_value:,.0f}원```**\n"
        
        # 김치프리미엄 조회
        kimchi_premium = coin.get_kimchi_premium()
        embed = disnake.Embed(color=0xffffff)
        try:
            embed.set_thumbnail(url=EMBED_ICON_URL)
        except Exception:
            pass
        embed.add_field(name="**실시간 재고**", value=balance_text if balance_text else "**```🛒 0원```**", inline=True)
        embed.add_field(name="**실시간 김프**", value=f"**```📈 {kimchi_premium:.2f}%```**", inline=True)
        embed.add_field(name=f"**<a:sexymega:1441678230175350817> 2분마다 재고하고 김프가 갱신됩니다**", value="**――――――――――――――――――――**", inline=False)
        embed.set_footer(text="Tip : 정보 조회 버튼 누르시면 거래내역 확인 가능")

        view = CoinView()
        await embed_message.edit(embed=embed, view=view)
        embed_updating = False
        
    except disnake.HTTPException as e:
        logger.error(f"업데이트 도중 에러: {e}")
        embed_message = None
        embed_updating = False
    except Exception as e:
        logger.error(f"업데이트 도중 에러: {e}")
        embed_message = None
        embed_updating = False
