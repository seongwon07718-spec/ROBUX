import discord
from discord import ui
from discord.ext import commands
from discord import app_commands # 슬래시 명령어 사용을 위해 추가

intents = discord.Intents.all()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=".", intents=intents)

    # 슬래시 명령어를 디스코드 서버에 동기화하는 설정
    async def setup_hook(self):
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

bot = MyBot()

class MeuLayout(ui.View):
    def __init__(self):
        super().__init__()

        # 요청하신 컨테이너 구조 (기존 코드 유지)
        container = ui.Container(ui.TextDisplay("**로블록스 쿠키 체커기**"))
        container.add_item(ui.Button(label="로블록스 쿠키 체커기 시작", style=discord.ButtonStyle.gray, custom_id="start_checker"))
        self.add_item(container)

# /쿠키체커기 슬래시 명령어 추가
@bot.tree.command(name="쿠키체커기", description="로블록스 쿠키 체커기 컨테이너를 보여줍니다.")
async def cookie_checker(interaction: discord.Interaction):
    layout = MeuLayout()
    await interaction.response.send_message(view=layout)

# 기존 .teste 명령어 유지
@bot.command()
async def teste(ctx: commands.Context):
    layout = MeuLayout()
    await ctx.reply(view=layout)

# 토큰을 입력하세요
bot.run("YOUR_TOKEN_HERE")
