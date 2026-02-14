import discord
from discord import app_commands
from discord.ext import commands

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
    # 임베드 생성 (제목, 설명, 색상 설정)
    embed = discord.Embed(
        title="24시간 자동 로벅스 자판기",
        color=0xffffff
    )

    # 필드 추가 (인라인 설정 가능)
    embed.add_field(name="현재 재고", value="```1,000 로벅스```", inline=True)
    embed.add_field(name="현재 가격", value="```만원 = 1300로벅스```", inline=True)

    embed.set_footer(text="안내: 문제 발생 시 관리자에게 문의해주세요")

    # 답변 전송
    await interaction.response.send_message(embed=embed)

bot.run('')
