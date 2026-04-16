import discord
from discord import app_commands, ui # 이미지 스타일의 UI 라이브러리 가정

# 1. 봇 기본 설정
TOKEN = 'YOUR_BOT_TOKEN_HERE' # 여기에 봇 토큰을 넣으세요

class MyBot(discord.Client):
    def __init__(self):
        # 봇의 권한 설정
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # 슬래시 명령어 동기화
        await self.tree.sync()
        print(f"{self.user}로 로그인 성공 및 명령어 동기화 완료!")

bot = MyBot()

# 2. /자판기 명령어 정의
@bot.tree.command(name="자판기", description="자판기 메뉴를 불러옵니다.")
async def vending_machine(interaction: discord.Interaction):
    # 컨테이너 구성
    con = ui.Container()
    con.accent_color = 0x5865F2

    con.add_item(ui.TextDisplay(
        "### <:acy2:1489883409001091142> 자판기 시스템\n"
        "-# 아래 버튼을 클릭하여 메뉴를 선택하세요.\n"
        "-# **구매, 제품, 충전, 정보** 기능을 지원합니다."
    ))

    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

    # Action Row에 버튼 4개 배치
    row = ui.ActionRow()
    
    btns = [
        ui.Button(label="구매", style=discord.ButtonStyle.gray, emoji="🛒"),
        ui.Button(label="제품", style=discord.ButtonStyle.gray, emoji="📦"),
        ui.Button(label="충전", style=discord.ButtonStyle.gray, emoji="💳"),
        ui.Button(label="정보", style=discord.ButtonStyle.gray, emoji="ℹ️")
    ]

    # 콜백 연결 (람다식)
    btns[0].callback = lambda i: i.response.send_message("🛒 구매 창을 엽니다.", ephemeral=True)
    btns[1].callback = lambda i: i.response.send_message("📦 제품 리스트입니다.", ephemeral=True)
    btns[2].callback = lambda i: i.response.send_message("💳 충전 메뉴입니다.", ephemeral=True)
    btns[3].callback = lambda i: i.response.send_message("ℹ️ 정보 페이지입니다.", ephemeral=True)

    for btn in btns:
        row.add_item(btn)

    con.add_item(row)

    # 컨테이너 전송
    await interaction.response.send_message(container=con)

# 3. 봇 실행
bot.run(TOKEN)
