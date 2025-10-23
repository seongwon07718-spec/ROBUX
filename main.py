import discord
from discord import PartialEmoji, ui, app_commands
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class MyLayoutVending(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        
        # 메인 컨테이너 생성
        self.c = ui.Container(ui.TextDisplay("24시간 OTT 자판기\n-# 버튼을 눌러 이용해주세요 !"))
        
        # 첫 번째 구분선
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 이미지 표시
        imagem_disco = ui.Thumbnail(attachment://disco.png)
        
        # 두 번째 구분선
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 이모지 생성
        charge_emoji = PartialEmoji.from_str("<:3_:1426934636428394678>")
        notification_emoji = PartialEmoji.from_str("<:6_:1426943544928505886>")
        info_emoji = PartialEmoji.from_str("<:5_:1426936503635939428>")
        purchase_emoji = PartialEmoji.from_str("<:4_:1426936460149395598>")
        
        # 버튼 생성 및 이모지 추가
        button_1 = ui.Button(label="충전", custom_id="charge_button", emoji=charge_emoji)
        button_2 = ui.Button(label="알림", custom_id="notification_button", emoji=notification_emoji)
        button_3 = ui.Button(label="정보", custom_id="my_info_button", emoji=info_emoji)
        button_4 = ui.Button(label="구매", custom_id="purchase_button", emoji=purchase_emoji)
        
        # 버튼 행 생성
        linha = ui.ActionRow(button_1, button_2)
        linha2 = ui.ActionRow(button_3, button_4)
        
        # 컨테이너에 버튼 행 추가
        self.c.add_item(linha)
        self.c.add_item(linha2)
        
        # 뷰에 컨테이너 추가
        self.add_item(self.c)

@bot.tree.command(name="자판기패널", description="자판기 패널을 표시합니다")
@app_commands.checks.has_permissions(administrator=True)
async def panel_vending(interaction: discord.Interaction):
    disco = discord.File('imagens/disco.png', 'disco.png')
    layout = MyLayoutVending()
    await interaction.response.send_message(view=layout, ephemeral=False)

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)}개의 슬래시 명령이 동기화되었습니다.")
    except Exception as e:
        print("명령 동기화 오류:", e)
    print(f"{bot.user}로 로그인했습니다.")

bot.run("")
