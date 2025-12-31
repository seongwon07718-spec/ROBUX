import discord
from discord import app_commands
from discord.ext import commands

# 1. 봇 설정 클래스
class MyBot(commands.Bot):
    def __init__(self):
        # 모든 인텐트 활성화 (필요에 따라 조정 가능)
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 슬래시 커맨드를 디스코드 서버에 등록(동기화)
        await self.tree.sync()
        print(f"✅ 커맨드 동기화 완료: {self.user.name}")

bot = MyBot()

# 2. 버튼이 포함된 뷰 클래스
class EscrowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # 버튼이 사라지지 않도록 설정

    @discord.ui.button(
        label="중개 시작", 
        style=discord.ButtonStyle.primary, 
        custom_id="start_escrow",
        emoji="<:1_:1455806365053489297>" # 요청하신 특수 이모지
    )
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 버튼 클릭 시 작동할 응답
        await interaction.response.send_message(
            f"{interaction.user.mention}님, 중개 절차를 시작합니다. 판매하실 아이템 정보를 준비해주세요!", 
            ephemeral=True
        )

# 3. /중개패널 커맨드 설정
@bot.tree.command(name="중개패널", description="로블록스 아이템 중개 거래 패널을 생성합니다.")
async def escrow_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ ROBLOX 안전 중개 시스템",
        description=(
            "**안전한 아이템 거래를 위해 봇이 중개역할을 수행합니다.**\n\n"
            "**[진행 순서]**\n"
            "1️⃣ 아래의 **중개 시작** 버튼을 클릭합니다.\n"
            "2️⃣ 판매자가 봇에게 아이템을 먼저 전달합니다.\n"
            "3️⃣ 구매자가 확인 후 대금을 입금합니다.\n"
            "4️⃣ 입금 확인 시 봇이 구매자에게 아이템을 전달합니다."
        ),
        color=discord.Color.from_rgb(43, 45, 49) # 다크 테마 색상
    )
    embed.set_image(url="https://i.imgur.com/your_banner_image.png") # (선택사항) 배너 이미지 주소
    embed.set_footer(text="보안을 위해 모든 거래 내역은 기록됩니다.")
    
    # 뷰와 함께 메시지 전송
    await interaction.response.send_message(embed=embed, view=EscrowView())

# 4. 봇 실행 (토큰 입력)
if __name__ == "__main__":
    bot.run('YOUR_BOT_TOKEN_HERE')
