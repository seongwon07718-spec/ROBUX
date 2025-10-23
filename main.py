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

        self.c = ui.Container(ui.TextDisplay("24시간 OTT 자판기\n-# 버튼을 눌러 이용해주세요 !"))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        custom_emoji1 = PartialEmoji(name="3_", id=1426934636428394678)
        custom_emoji2 = PartialEmoji(name="6_", id=1426943544928505886)
        custom_emoji3 = PartialEmoji(name="5_", id=1426936503635939428)
        custom_emoji4 = PartialEmoji(name="4_", id=1426936460149395598)

        # 버튼 생성 및 이모지 추가
        button_1 = ui.Button(label="충전", custom_id="button_1", emoji=custom_emoji1)
        button_2 = ui.Button(label="알림", custom_id="button_2", emoji=custom_emoji2)
        button_3 = ui.Button(label="정보", custom_id="button_3", emoji=custom_emoji3)
        button_4 = ui.Button(label="구매", custom_id="button_4", emoji=custom_emoji4)
        
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
    layout = MyLayoutVending()
    # 반드시 interaction에 응답을 보내야 합니다 (없으면 상호작용 오류 발생)
    await interaction.response.send_message(view=layout, ephemeral=False)

# ---------------- on_ready ----------------
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)}개의 슬래시 명령이 동기화되었습니다.")
    except Exception as e:
        print("명령 동기화 오류:", e)
    print(f"{bot.user}로 로그인했습니다.")

bot.run("")
