import discord
from discord import app_commands
from discord.ext import commands

# 1. 봇 설정 (인텐트 설정)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'로그인 완료: {bot.user.name}')
    try:
        # 슬래시 커맨드 동기화 (수정 후 반영까지 시간이 걸릴 수 있습니다)
        synced = await bot.tree.sync()
        print(f"동기화된 커맨드 수: {len(synced)}개")
    except Exception as e:
        print(e)

# 2. /매크로 커맨드 생성
@bot.tree.command(name="매크로", description="임베드 메시지를 전송합니다.")
async def macro(interaction: discord.Interaction):
    # 임베드 객체 생성 (제목, 설명, 색상 설정)
    embed = discord.Embed(
        title="📢 공지사항 매크로",
        description="이것은 자동으로 전송되는 임베드 메시지입니다.",
        color=discord.Color.blue() # 색상 코드 (Blue, Red, Green 등)
    )

    # 필드 추가 (이름, 내용, 가로 정렬 여부)
    embed.add_field(name="📌 항목 1", value="여기에 내용을 입력하세요.", inline=False)
    embed.add_field(name="⚙️ 항목 2", value="원하는 텍스트로 수정 가능합니다.", inline=True)
    
    # 푸터(하단) 및 타임스탬프 설정
    embed.set_footer(text="작성일자")
    embed.timestamp = discord.utils.utcnow()

    # 이미지나 썸네일을 넣고 싶다면 주석을 해제하세요
    # embed.set_thumbnail(url="이미지 주소")

    # 응답 전송
    await interaction.response.send_message(embed=embed)

# 3. 봇 실행 (본인의 토큰을 입력하세요)
bot.run('YOUR_BOT_TOKEN_HERE')
