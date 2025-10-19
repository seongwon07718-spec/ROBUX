import discord
from discord import PartialEmoji, ui
from discord.ext import commands
intents = discord.Intents.all()

command_prefix = "!"
bot = commands.Bot(command_prefix=command_prefix, intents=intents)

class MyLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        self.c = ui.Container(ui.TextDisplay("**누락 보상 받기**"))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.c.add_item(ui.TextDisplay("-# 아래 누락보상 버튼을 누르시면 보상 받을 수 있습니다.\n-# 다만 제품 보증 없는거는 보상 받으실 수 없습니다."))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        custom_emoji1 = PartialEmoji(name="__", id=1429373065116123190)
        custom_emoji2 = PartialEmoji(name="1_7", id=1429373066588454943)

        self.button_1 = ui.Button(label="누락 보상 받기", custom_id="button_1", emoji=custom_emoji1)
        self.button_2 = ui.Button(label="누락 제품 확인", custom_id="button_2", emoji=custom_emoji2)

        linha = ui.ActionRow(self.button_1, self.button_2)

        self.c.add_item(linha)
        self.add_item(self.c)

active_views = {}

# 클래스 이름 중복으로 인한 덮어쓰기 문제 해결을 위해 클래스명을 변경했습니다.
class MyLayoutVending(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        
        c = ui.Container(ui.TextDisplay(
            "**24시간 OTT 자판기**\n-# 버튼을 눌러 이용해주세요 !"
        ))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        sessao = ui.Section(ui.TextDisplay("**총 판매 금액\n-# 실시간으로 올라갑니다.**"), accessory=ui.Button(label="0원", disabled=True))
        c.add_item(sessao)
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 이모지 (예시 ID, 실제 사용 시 올바른 ID로 변경)
        custom_emoji1 = PartialEmoji(name="3_", id=1426934636428394678)
        custom_emoji2 = PartialEmoji(name="6_", id=1424003480007475281)
        custom_emoji3 = PartialEmoji(name="5_", id=1426936503635939428)
        custom_emoji4 = PartialEmoji(name="4_", id=1426936460149395598)

        # 메인 버튼들
        button_1 = ui.Button(label="충전", custom_id="button_1", emoji=custom_emoji1)
        button_2 = ui.Button(label="입고알림", custom_id="button_2", emoji=custom_emoji2)
        button_3 = ui.Button(label="내 정보", custom_id="button_3", emoji=custom_emoji3)
        button_4 = ui.Button(label="구매", custom_id="button_4", emoji=custom_emoji4)

        linha = ui.ActionRow(button_1, button_2)
        linha2 = ui.ActionRow(button_3, button_4)

        c.add_item(linha)
        c.add_item(linha2)
        self.add_item(c)

@bot.event
async def on_ready():
    print(f"로벅스 자판기 봇이 {bot.user}로 로그인했습니다.")
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'슬래시 명령어 동기화 중 오류 발생.: {e}')

# 같은 슬래시 이름을 사용하더라도 파이썬 함수명이 중복되면 덮어쓰기나 등록 문제가 생깁니다.
# 따라서 데코레이터는 그대로 두고 내부 함수 이름만 고유하게 변경했습니다.

@bot.tree.command(name="누락패널", description="누락 보상 패널을 표시합니다")
async def button_panel_nurak(interaction: discord.Interaction):
    layout = MyLayout()
    await interaction.response.send_message(view=layout, ephemeral=False)

@bot.tree.command(name="자판기패널", description="자판기 패널을 표시합니다")
async def button_panel_vending(interaction: discord.Interaction):
    layout = MyLayoutVending()
    await interaction.response.send_message(view=layout, ephemeral=False)

bot.run("")
