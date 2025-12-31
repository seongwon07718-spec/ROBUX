import discord
from discord import app_commands
from discord.ext import commands

# 설정
CATEGORY_ID = 1455820042368450580  # 중개 티켓이 생성될 카테고리 ID
ADMIN_ROLE_ID = 1454398431996018724  # 중개 관리자 역할 ID

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"커맨드 동기화 완료: {self.user.name}")

bot = MyBot()

class EscrowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="중개문의 티켓열기", 
        style=discord.ButtonStyle.gray, 
        custom_id="start_escrow",
        emoji="<:emoji_2:1455814454490038305>"
    )

# 중개 커맨드 설정
@bot.tree.command(name="입양중개", description="입양 중개 패널 전송")
async def escrow_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="자동중개 - AMP 전용",
        description=(
            "**안전 거래하기 위해서는 중개가 필수입니다\n아래 버튼을 눌려 중개 절차를 시작해주세요\n\n┗ 티켓 여시면 중개봇이 안내해줍니다\n┗ 상호작용 오류시 문의부탁드려요\n\n[중개 이용약관](https://swnx.shop)      [디스코드 TOS](https://discord.com/terms)**"
        ),
        color=0xffffff
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1455811337937747989/IMG_0723.png?ex=69561576&is=6954c3f6&hm=daf60069947d93e54dcb3b85facb151b9ecea1de76c234b91e68c36d997384b2&") # (선택사항) 배너 이미지 주소
    
    # 뷰와 함께 메시지 전송
    await interaction.response.send_message(embed=embed, view=EscrowView())

# 4. 봇 실행 (토큰 입력)
if __name__ == "__main__":
    bot.run('import discord')
from discord import app_commands
from discord.ext import commands

# 설정
CATEGORY_ID = 1455820042368450580  # 중개 티켓이 생성될 카테고리 ID
ADMIN_ROLE_ID = 1454398431996018724  # 중개 관리자 역할 ID

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"커맨드 동기화 완료: {self.user.name}")

bot = MyBot()

class EscrowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="중개문의 티켓열기", 
        style=discord.ButtonStyle.gray, 
        custom_id="start_escrow",
        emoji="<:emoji_2:1455814454490038305>"
    )
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 버튼 클릭 시 작동할 응답
        guild = interaction.guild
        user = interaction.user

# 중개 커맨드 설정
@bot.tree.command(name="입양중개", description="입양 중개 패널 전송")
async def escrow_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="자동중개 - AMP 전용",
        description=(
            "**안전 거래하기 위해서는 중개가 필수입니다\n아래 버튼을 눌려 중개 절차를 시작해주세요\n\n┗ 티켓 여시면 중개봇이 안내해줍니다\n┗ 상호작용 오류시 문의부탁드려요\n\n[중개 이용약관](https://swnx.shop)      [디스코드 TOS](https://discord.com/terms)**"
        ),
        color=0xffffff
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1455811337937747989/IMG_0723.png?ex=69561576&is=6954c3f6&hm=daf60069947d93e54dcb3b85facb151b9ecea1de76c234b91e68c36d997384b2&") # (선택사항) 배너 이미지 주소
    
    # 뷰와 함께 메시지 전송
    await interaction.response.send_message(embed=embed, view=EscrowView())

# 4. 봇 실행 (토큰 입력)
if __name__ == "__main__":
    bot.run('')
