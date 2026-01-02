# 1. 인증 시작 버튼 뷰: 인증 안내 임베드에 달린 버튼 UI
class VerifyStartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="로블록스 인증하기", style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji(name="verified", id=1455996645337468928))
    async def start_verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        # "정보 수정하기" 버튼 포함 버전으로 메시지 수정 (VerifyStepView 새 인스턴스)
        embed = discord.Embed(
            title="로블록스 - 인증 절차",
            description="아래 버튼을 눌러 정보를 수정하고 인증을 진행해 주세요.",
            color=0xffffff
        )
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1456321236643741728/IMG_0751.png"
        embed.set_image(url=img_url)

        await interaction.response.edit_message(embed=embed, view=VerifyStepView())

# 2. 기존 /verify 명령어 수정: 인증 안내 임베드 + VerifyStartView 출력
@bot.tree.command(name="verify", description="로블록스 인증하기 패널")
async def verify_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("**DONE**", ephemeral=True)

    embed = discord.Embed(
        title="로블록스 - VERIFY BOT",
        description=(
            "**게임을 이용하실려면 인증은 필수입니다**\n"
            "**아래 버튼을 눌러 인증 절차를 시작하세요**\n\n"
            "**┗ 인증 후 게임 이용이 가능합니다**\n"
            "**┗ 상호작용 오류시 문의부탁드려요**\n\n"
            "**[로블록스 이용약관](https://www.roblox.com/terms)         [디스코드 TOS](https://discord.com/terms)**"
        ),
        color=0xffffff
    )
    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1456494848457572433/IMG_0753.png"
    embed.set_image(url=img_url)

    await interaction.channel.send(embed=embed, view=VerifyStartView())
