        kimchi_premium = coin.get_kimchi_premium()
        embed = disnake.Embed(color=0xffffff)
        try:
            embed.set_thumbnail(url=EMBED_ICON_URL)
        except Exception:
            pass

        embed.add_field(name="**실시간 재고**", value=balance_text if balance_text else "**```🛒 0원```**", inline=True)
        embed.add_field(name="**실시간 김프**", value=f"**```📈 {kimchi_premium:.2f}%```**", inline=True)
        embed.add_field(name=f"**<a:sexymega:1441678230175350817> {timestamp_str}에 재고, 김프가 갱신되었습니다**", value="**――――――――――――――――――――**", inline=False)
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
