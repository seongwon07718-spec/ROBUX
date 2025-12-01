@bot.slash_command(name="수동충전", description="인증고객님 수동 충전")
async def chrg_user(inter, 유저: disnake.Member, 금액: int):
    try:
        if inter.author.id not in ALLOWED_USER_IDS:
            embed = disnake.Embed(
                title="**접근 거부**",
                description="**이 명령어는 허용된 사용자만 사용할 수 있습니다.**",
                color=0xff0000
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        if not check_admin(inter.author.id):
            embed = disnake.Embed(
                title="**오류**",
                description="**권한이 없습니다.**",
                color=0xff6200
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        
        user_data = coin.get_verified_user(유저.id)
        if not user_data:
            embed = disnake.Embed(
                title="**오류**",
                description="**해당 고객님은 인증되지 않았습니다.**",
                color=0xff6200
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        
        add_balance(유저.id, 금액)
        embed = disnake.Embed(
            title="충전 완료",
            description=f"**{유저.display_name} / {user_data[3]} 고객님**\n충전금액: **₩{금액:,}**\n이제 대행을 이용해주세요!",
            color=0xffffff
        )
        embed.set_thumbnail(url=유저.display_avatar.url)
        embed.set_footer(text="충전이 즉시 반영되었습니다.")
        await inter.response.send_message(embed=embed)
        # 로그 채널에 알림
        channel = bot.get_channel(CHANNEL_CHARGE_LOG)
        if channel is not None:
            log_embed = disnake.Embed(
                title="충전 로그",
                description=f"**{유저.display_name} / {user_data[3]} 고객님**\n금액: **₩{금액:,}**",
                color=0xffffff
            )
            log_embed.set_footer(text=f"처리자: {inter.author.display_name}")
            await channel.send(embed=log_embed)
        else:
            logger.error(f"충전 로그 채널({CHANNEL_CHARGE_LOG})을 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"고객충전 오류: {e}")
        embed = disnake.Embed(
            title="**오류**",
            description="**처리 중 오류가 발생했습니다.**",
            color=0xff6200
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
