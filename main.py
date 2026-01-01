@bot.tree.command(name="amp_panel", description="입양 중개 패널 전송")
async def escrow_panel(interaction: discord.Interaction):
    # 1. 명령어 입력자에게만 보이는 완료 문구 전송 (ephemeral=True)
    await interaction.response.send_message("**✅ 중개 패널 임베드가 성공적으로 전송되었습니다.**", ephemeral=True)

    # 2. 실제 채널에 전송될 패널 임베드 설정
    embed = discord.Embed(
        title="자동중개 - AMP 전용", 
        description=(
            "**안전 거래하기 위해서는 중개가 필수입니다**\n"
            "**아래 버튼을 눌려 중개 절차를 시작해주세요**\n\n"
            "**┗ 티켓 여시면 중개봇이 안내해줍니다**\n"
            "**┗ 상호작용 오류시 문의부탁드려요**\n\n"
            "**[중개 이용약관](https://swnx.shop) / [디스코드 TOS](https://discord.com/terms)**"
        ), 
        color=0xffffff
    )
    
    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1455922358417358848/IMG_0741.png"
    embed.set_image(url=img_url)

    # 3. interaction.channel.send를 사용하여 실제 패널 전송
    await interaction.channel.send(embed=embed, view=EscrowView())
