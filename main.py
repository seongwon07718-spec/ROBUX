class EscrowDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="머더 미스테리", description="머더 미스테리 충전 안내를 진행합니다.", emoji="🔪"),
            discord.SelectOption(label="입양하세요", description="입양하세요 충전 안내를 진행합니다.", emoji="👶")
        ]
        super().__init__(placeholder="충전할 로블록스 게임을 선택해주세요", min_values=1, max_values=1, options=options)

    # 반드시 클래스 안에(들여쓰기 포함) 있어야 합니다.
    async def callback(self, interaction: discord.Interaction):
        game_choice = self.values[0]
        await interaction.response.defer(ephemeral=True) # API 조회 시간 벌기

        bot_options = []
        # BOT_DATA에서 해당 게임의 봇 리스트를 가져와 실시간 상태 체크
        for bot in BOT_DATA.get(game_choice, []):
            is_online = await get_bot_status(bot["id"]) # 로블록스 ID로 체크
            emoji = "🟢" if is_online else "🔴"
            status_txt = "접속 중" if is_online else "미접속"
            
            bot_options.append(discord.SelectOption(
                label=f"{emoji} {bot['name']}",
                description=f"현재 {status_txt} 상태입니다.",
                value=bot['name'] # 값에는 이름만 전달
            ))

        if not bot_options:
            return await interaction.followup.send("현재 선택 가능한 봇이 없습니다.", ephemeral=True)

        embed = discord.Embed(
            title="🤖 충전할 봇을 선택해주세요",
            description=f"선택하신 **{game_choice}**의 실시간 봇 목록입니다.",
            color=0xffffff
        )
        
        # 새로운 봇 선택용 뷰 생성
        bot_view = discord.ui.View()
        bot_view.add_item(BotStatusSelect(game_choice, bot_options))
        
        # 마지막에 view=bot_view를 반드시 넣어줘야 합니다.
        await interaction.followup.send(embed=embed, view=bot_view, ephemeral=True)
