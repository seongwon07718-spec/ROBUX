@bot.slash_command(name="대행임베드", description="코인대행 임베드 전송")
async def service_embed(inter):
    global embed_message, current_stock, current_rate, last_update_time

    try:
        # 3초 타임아웃 방지용 선미응답
        await inter.response.defer(ephemeral=True)

        # 허용된 사용자만 사용 가능
        if inter.author.id not in ALLOWED_USER_IDS:
            embed = disnake.Embed(
                title="**접근 거부**",
                description="**이 명령어는 허용된 사용자만 사용할 수 있습니다.**",
                color=0xff0000
            )
            await inter.edit_original_response(embed=embed)
            return

        # 관리자 권한 확인
        if not check_admin(inter.author.id):
            embed = disnake.Embed(
                title="**오류**",
                description="**권한이 없습니다.**",
                color=0xff6200
            )
            await inter.edit_original_response(embed=embed)
            return

        # --- [초기 데이터 로드] ---
        # 루프에서 사용할 데이터도 여기서 초기화
        all_balances = coin.get_all_balances()
        all_prices = coin.get_all_coin_prices()
        current_stock = get_stock_amount() # 초기 재고/환율 로드
        current_rate = get_exchange_rate() 
        last_update_time = datetime.now()


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

        # 김치 프리미엄 조회
        kimchi_premium = coin.get_kimchi_premium()

        embed = disnake.Embed(color=0xffffff)
        try:
            embed.set_thumbnail(url=EMBED_ICON_URL)
        except Exception:
            pass

        timestamp_str = f"<t:{int(time.time()) - 1}:R>"

        embed.add_field(name="**실시간 재고**", value=balance_text if balance_text else "**```🛒 0원```**", inline=True)
        embed.add_field(name="**김프 (%)**", value=f"**```📈 {kimchi_premium:.2f}%```**", inline=True)
        embed.add_field(
            name=f"**<a:sexymega:1441678230175350817>마지막 갱신 = {timestamp_str}**",
            value="**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**",
            inline=False
        )
        embed.set_footer(text="Tip : 정보 조회 버튼 누르시면 거래내역 확인 가능합니다.")

        view = CoinView()
        # 메시지를 전송하고 전역 변수에 저장
        embed_message = await inter.channel.send(embed=embed, view=view)

        if update_embed_task.is_running():
            update_embed_task.restart()
        else:
            update_embed_task.start()

        # 관리자 응답
        admin_embed = disnake.Embed(color=0xffffff)
        admin_embed.add_field(name="대행 임베드 전송", value=f"**{inter.author.display_name}** 대행임베드를 사용함", inline=False)
        await inter.edit_original_response(embed=admin_embed)

    except Exception as e:
        logger.error(f"대행임베드 오류: {e}")
        error_embed = disnake.Embed(
            title="**오류**",
            description="**처리 중 오류가 발생했습니다.**",
            color=0xff6200
        )
        try:
            await inter.edit_original_response(embed=error_embed)
        except Exception:
            pass
