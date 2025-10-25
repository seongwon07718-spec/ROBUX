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

        c = ui.Container(ui.TextDisplay("**최저가 부스트**\n-# 버튼을 눌러 이용해주세요"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))


        boost = ui.Section(ui.TextDisplay("**부스트 재고\n-# 60초마다 갱신됩니다**"), accessory=ui.Button(label="1000 부스트", disabled=True, style=discord.ButtonStyle.primary))
        c.add_item(boost)
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        custom_emoji1 = PartialEmoji(name="d3", id=1431500583415713812)
        custom_emoji2 = PartialEmoji(name="d8", id=1431500580198682676)
        custom_emoji3 = PartialEmoji(name="d4", id=1431500582295965776)
        custom_emoji4 = PartialEmoji(name="d19", id=1431500579162554511)

        button_1 = ui.Button(label="충전", custom_id="button_1", emoji=custom_emoji1)
        button_2 = ui.Button(label="후기", custom_id="button_2", emoji=custom_emoji2)
        button_3 = ui.Button(label="정보", custom_id="button_3", emoji=custom_emoji3)
        button_4 = ui.Button(label="구매", custom_id="button_4", emoji=custom_emoji4)
        
        linha = ui.ActionRow(button_1, button_2)
        linha2 = ui.ActionRow(button_3, button_4)
        
        c.add_item(linha)
        c.add_item(linha2)
        self.add_item(c)

@bot.tree.command(name="부스트_자판기", description="부스트 자판기를 표시합니다")
@app_commands.checks.has_permissions(administrator=True)
async def panel_vending(interaction: discord.Interaction):

    view = MyLayoutVending()
    await interaction.response.send_message(view=view, ephemeral=False)

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅{len(synced)}개의 슬래시 명령이 동기화 완료")
    except Exception as e:
        print("❌명령 동기화 오류:", e)
    print(f"✅{bot.user}로 로그인 성공")

bot.run("")
