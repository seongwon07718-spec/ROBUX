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
