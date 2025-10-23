import discord
from discord import PartialEmoji, ui, app_commands
from discord.ext import commands
import os
import asyncio

class MyLayoutVending(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.c = ui.Container(ui.TextDisplay("24시간 OTT 자판기\n-# 버튼을 눌러 이용해주세요 !"))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        button_1 = ui.Button(label="충전", custom_id="charge_button")
        button_2 = ui.Button(label="알림", custom_id="notification_button")
        button_3 = ui.Button(label="정보", custom_id="my_info_button")
        button_4 = ui.Button(label="구매", custom_id="purchase_button")
        linha = ui.ActionRow(button_1, button_2)
        linha2 = ui.ActionRow(button_3, button_4)
        self.c.add_item(linha)
        self.c.add_item(linha2)
        self.add_item(self.c)

@bot.tree.command(name="자판기패널", description="자판기 패널을 표시합니다")
@app_commands.checks.has_permissions(administrator=True)
async def panel_vending(interaction: discord.Interaction):
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
