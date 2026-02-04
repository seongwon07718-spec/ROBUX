import discord
from discord import app_commands
from discord.ext import commands

# 봇 설정
token = 'YOUR_BOT_TOKEN_HERE' # 여기에 본인의 봇 토큰을 넣으세요
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # 슬래시 커맨드 동기화
    await bot.tree.sync()
    print(f'로그인 완료: {bot.user.name}')

@bot.tree.command(name="로벅스_임베드_전송", description="로벅스 판매 임베드를 전송합니다.")
async def robux_embed(interaction: discord.Interaction):
    # 임베드 설정
    embed = discord.Embed(
        title="💰 로벅스 판매 목록",
        description="안전하고 빠른 로벅스 충전 서비스입니다.",
        color=discord.Color.gold()
    )
    
    # 필드 추가 (가격표 등)
    embed.add_field(name="💎 1,000 Robux", value="10,000원", inline=True)
    embed.add_field(name="💎 5,000 Robux", value="45,000원", inline=True)
    embed.add_field(name="💎 10,000 Robux", value="85,000원", inline=True)
    
    embed.set_footer(text="문의는 고객센터 채널을 이용해주세요.")
    embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/c/c7/Robux_2019_Logo_gold.svg") # 로벅스 아이콘 예시
    
    # 임베드 전송
    await interaction.response.send_message(embed=embed)

bot.run(token)
