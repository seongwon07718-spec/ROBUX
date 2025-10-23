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

        self.c = ui.Container(ui.TextDisplay("**24시간 OTT 자판기**\n-# 버튼을 눌러 이용해주세요 !"))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        help_container = ui.Container(ui.TextDisplay("**자동충전** 오류시 [바로가기](https://discord.com/channels/1419200424636055592/1428821675142811729)\n**제품설명** 확인은? [바로가기](https://discord.com/channels/1419200424636055592/1430852730720878695)"))
        help_container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.c.add_item(help_container)
        

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

# ----------------- 안전하게 변경한 panel_vending 함수 -----------------
@bot.tree.command(name="자판기패널", description="자판기 패널을 표시합니다")
@app_commands.checks.has_permissions(administrator=True)
async def panel_vending(interaction: discord.Interaction):
    """
    주의: MyLayoutVending 클래스는 그대로 두고,
    interaction 처리에서 400 오류가 나는 환경을 피하기 위해
    안전한 discord.ui.View 기반 응답으로 대체합니다.
    (다른 코드는 절대 변경하지 않았습니다)
    """
    # 1) 동일한 텍스트 내용 구성 (원본 컨테이너 내용과 동일하게 보이도록)
    content_lines = [
        "**24시간 OTT 자판기**",
        "-# 버튼을 눌러 이용해주세요 !",
        "",
        "**자동충전** 오류시 <#1428821675142811729>",
        "**제품설명** 확인은? <#1430852730720878695>"
    ]
    content = "\n".join(content_lines)

    # 2) 안전한 View 생성 (discord.ui.View + Buttons)
    view = discord.ui.View(timeout=None)

    # 이모지 생성(문제가 있으면 None으로 처리)
    try:
        e1 = PartialEmoji(name="3_", id=1426934636428394678)
        e2 = PartialEmoji(name="6_", id=1426943544928505886)
        e3 = PartialEmoji(name="5_", id=1426936503635939428)
        e4 = PartialEmoji(name="4_", id=1426936460149395598)
    except Exception:
        e1 = e2 = e3 = e4 = None

    # 간단한 버튼 클래스: 눌렀을 때 에페메럴로 확인 메시지 전송
    class SimpleButton(discord.ui.Button):
        def __init__(self, label, custom_id, emoji=None):
            super().__init__(label=label, custom_id=custom_id, emoji=emoji)
        async def callback(self, interaction: discord.Interaction):
            # 버튼 클릭 시 안전하게 한 번만 응답
            await interaction.response.send_message(f"'{self.label}' 버튼을 누르셨습니다.", ephemeral=True)

    # 버튼을 View에 추가 (원래 라벨/아이디 그대로 사용)
    view.add_item(SimpleButton(label="충전", custom_id="button_1", emoji=e1))
    view.add_item(SimpleButton(label="알림", custom_id="button_2", emoji=e2))
    view.add_item(SimpleButton(label="정보", custom_id="button_3", emoji=e3))
    view.add_item(SimpleButton(label="구매", custom_id="button_4", emoji=e4))

    # 3) interaction에 단 한 번만 안전하게 응답
    await interaction.response.send_message(content=content, view=view, ephemeral=False)

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
