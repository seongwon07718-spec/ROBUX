import discord
from discord import app_commands
from discord.ext import commands

# 봇 설정
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 슬래시 명령어를 디스코드 서버에 동기화합니다.
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
        title="💰 자동 로벅스 시스템",
        description="원하시는 메뉴를 선택하거나 정보를 확인하세요.",
        color=discord.Color.blue()
    )

    # 필드 추가 (인라인 설정 가능)
    embed.add_field(name="상태", value="🟢 정상 작동 중", inline=True)
    embed.add_field(name="잔액", value="1,000 Robux", inline=True)
    
    # 이미지나 썸네일 추가 (URL 필요)
    # embed.set_thumbnail(url="이미지 주소")
    
    # 하단 문구
    embed.set_footer(text="요청자: " + interaction.user.name)

    # 답변 전송
    await interaction.response.send_message(embed=embed)

bot.run('YOUR_TOKEN_HERE')
