import discord
from discord import app_commands
from discord.ext import commands

# --- 버튼 기능을 담당하는 클래스 추가 ---
class RobuxButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="구매하기", style=discord.ButtonStyle.green)
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("구매 프로세스를 시작합니다.", ephemeral=True)

    @discord.ui.button(label="내 정보", style=discord.ButtonStyle.grey)
    async def info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"**{interaction.user.name}**님의 정보입니다.", ephemeral=True)

    @discord.ui.button(label="충전하기", style=discord.ButtonStyle.blurple)
    async def charge(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("충전 페이지 안내입니다.", ephemeral=True)
# ---------------------------------------

# 봇 설정
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

# /auto_robux 명령어 정의
@bot.tree.command(name="auto_robux", description="로벅스 정보를 임베드로 확인합니다.")
async def auto_robux(interaction: discord.Interaction):
    # 임베드 생성
    embed = discord.Embed(
        title="24시간 자동 로벅스 자판기",
        color=0xffffff
    )

    # 상단 작은 글씨 추가
    embed.set_author(name="자동화 시스템 가동 중")

    # 필드 추가
    embed.add_field(name="현재 재고", value="```1,000 로벅스```", inline=True)
    embed.add_field(name="현재 가격", value="```만원 = 1300로벅스```", inline=True)

    embed.set_footer(text="안내: 문제 발생 시 관리자에게 문의해주세요")

    # 버튼(View) 생성 후 함께 전송
    view = RobuxButtons()
    await interaction.response.send_message(embed=embed, view=view)

bot.run('')
