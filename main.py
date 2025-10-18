import discord
from discord import PartialEmoji, ui
from discord.ext import commands
intents = discord.Intents.all()

command_prefix = "!"
bot = commands.Bot(command_prefix=command_prefix, intents=intents)

class MyLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None) # 뷰 만료 없음

        c = ui.Container(ui.TextDisplay(
            "인증하기"
        ))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        c.add_item(ui.TextDisplay("아래 인증하기 버튼을 눌려 인증해주세요\n인증하시면 모든 채널을 보실 수 있습니다"))
        # c.add_item(c)  # <-- 이 줄을 제거했습니다 (자기 자신을 추가하면 재귀 오류 발생)
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        custom_emoji1 = PartialEmoji(name="Right", id=1428996148542181449)

        button_1 = ui.Button(label="인증하기", custom_id="button_1", emoji=custom_emoji1)

        linha = ui.ActionRow(button_1)

        c.add_item(linha)
        self.add_item(c)
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

@bot.event
async def on_ready():
    print(f"로벅스 자판기 봇이 {bot.user}로 로그인했습니다.")
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'슬래시 명령어 동기화 중 오류 발생.: {e}')

@bot.tree.command(name="인증패널", description="인증 패널을 표시합니다")
async def button_panel(interaction: discord.Interaction):
    layout = MyLayout()
    await interaction.response.send_message(view=layout, ephemeral=False)

# --- 봇 실행 ---
bot.run("") # 여기에 봇 토큰을 입력하세요
