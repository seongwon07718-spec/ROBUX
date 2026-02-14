class RobuxButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="구매하기", style=discord.ButtonStyle.green, emoji="🛒")
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("구매 프로세스를 시작합니다.", ephemeral=True)

    # --- 정보 버튼 클릭 시 임베드가 나오도록 수정 ---
    @discord.ui.button(label="내 정보", style=discord.ButtonStyle.grey, emoji="👤")
    async def info(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. 정보용 새로운 임베드 생성
        info_embed = discord.Embed(
            title=f"👤 {interaction.user.name}님의 정보",
            description="현재 보유 중인 정보입니다.",
            color=0x5865F2 # 정보 버튼에 어울리는 파란색 계열
        )
        info_embed.add_field(name="보유 로벅스", value="```0 Robux```", inline=True)
        info_embed.add_field(name="누적 구매 금액", value="```0원```", inline=True)
        info_embed.set_footer(text="조회 시간", icon_url=interaction.user.display_avatar.url)
        info_embed.set_author(name="내 정보 시스템", icon_url=interaction.client.user.display_avatar.url)

        # 2. 생성한 임베드 전송 (ephemeral=True는 본인에게만 보임)
        await interaction.response.send_message(embed=info_embed, ephemeral=True)

    @discord.ui.button(label="충전하기", style=discord.ButtonStyle.blurple, emoji="💳")
    async def charge(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("충전 페이지 안내입니다.", ephemeral=True)
