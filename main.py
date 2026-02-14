import discord
from discord import app_commands
from discord.ext import commands

class RobuxButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="구매", style=discord.ButtonStyle.grey, emoji=discord.PartialEmoji(name="PAY", id=1472159579545796628))
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("구매 프로세스를 시작합니다.", ephemeral=True)

    @discord.ui.button(label="내 정보", style=discord.ButtonStyle.grey, emoji=discord.PartialEmoji(name="User", id=1472159581017739386))
    async def info(self, interaction: discord.Interaction, button: discord.ui.Button):
        info_embed = discord.Embed(
            color=0xffffff
        )
        info_embed.set_author(name=f"{interaction.user.name}님의 정보", icon_url=interaction.client.user.display_avatar.url)
        info_embed.add_field(name="누적 금액", value="```0로벅스```", inline=True)
        info_embed.add_field(name="등급 혜택", value="```브론즈 ( 할인 1.5% 적용 )```", inline=True)

        await interaction.response.send_message(embed=info_embed, ephemeral=True)

    @discord.ui.button(label="충전", style=discord.ButtonStyle.grey, emoji=discord.PartialEmoji(name="ID", id=1472159578371133615))
    async def charge(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("충전 페이지 안내입니다.", ephemeral=True)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.tree.command(name="자판기", description="자동화 로벅스 자판기 전송")
async def auto_robux(interaction: discord.Interaction):
    await interaction.response.send_message("**로벅스 자판기를 불러오는 중입니다**", ephemeral=True)
    embed = discord.Embed(
        color=0xffffff
    )

    embed.set_author(name="자동 로벅스 자판기", icon_url=bot.user.display_avatar.url)

    embed.add_field(name="현재 재고", value="```1,000로벅스```", inline=True)
    embed.add_field(name="현재 가격", value="```만원 = 1300로벅스```", inline=True)

    embed.set_footer(text="안내: 문제 발생 시 관리자에게 문의해주세요")

    view = RobuxButtons()
    await interaction.followup.send(embed=embed, view=view)
