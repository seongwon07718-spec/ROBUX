@bot.slash_command(name="대행패널", description="대행 패널 전송")
async def service_embed(inter):
    try:
        # Defer early to avoid 3s timeout
        await inter.response.defer(ephemeral=True)
        if inter.author.id not in ALLOWED_USER_IDS:
            embed = disnake.Embed(
                title="**접근 거부**",
                description="**이 명령어는 허용된 사용자만 사용할 수 있습니다.**",
                color=0xff0000
            )
            await inter.edit_original_response(embed=embed)
            return
        if not check_admin(inter.author.id):
            embed = disnake.Embed(
                title="**오류**",
                description="**권한이 없습니다.**",
                color=0xff6200
            )
            await inter.edit_original_response(embed=embed)
            return
        
        global embed_message, current_stock, current_rate, last_update_time
        
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
        embed.add_field(name=f"**<a:sexymega:1441678230175350817>{timestamp_str}에 재고, 김프가 갱신되었습니다**", value="**――――――――――――――――――――**", inline=False)
        embed.set_footer(text="Tip : 정보 조회 버튼 누르시면 거래내역 확인 가능")

        view = CoinView()
        embed_message = await inter.channel.send(embed=embed, view=view)

        admin_embed = disnake.Embed(color=0xffffff)
        admin_embed.add_field(name="대행 전송", value=f"**{inter.author.display_name}** 대행임베드를 사용함", inline=False)
        await inter.edit_original_response(embed=admin_embed)
        await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"대행임베드 오류: {e}")
        embed = disnake.Embed(
            title="**오류**",
            description="**처리 중 오류가 발생했습니다.**",
            color=0xff6200
        )
        try:
            await inter.edit_original_response(embed=embed)
        except:
            pass
