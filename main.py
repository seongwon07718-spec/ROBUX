# pip install -U discord.py

import os
import discord
from discord import app_commands
from discord.ext import commands

GUILD_ID = 1419200424636055592  # 튜어오오오옹 서버 ID 적용

# '뢰색' 톤의 청록 계열
ROY_TEAL = discord.Color.from_str("#2AB2A6")

# 커스텀 애니메이션 이모지
EMOJI_NOTICE = "<a:book:1421336655545106572>"
EMOJI_PRODUCT = "<a:sakfnmasfagfamg:1421336645084512537>"
EMOJI_CHARGE = "<a:upuoipipi:1421392209089007718>"
EMOJI_BUY = "<a:thumbsuppp:1421336653389365289>"
EMOJI_INFO = "<a:list:1421336647303172107>"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

class ButtonPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        # 2x3 배열: 1행(공지사항, 제품, 충전), 2행(구매, 내 정보, 자리채움)
        self.add_item(self.notice_button())
        self.add_item(self.product_button())
        self.add_item(self.charge_button())
        self.add_item(self.buy_button())
        self.add_item(self.info_button())
        self.add_item(self.placeholder_button())

    def notice_button(self):
        return discord.ui.Button(
            label="공지사항",
            style=discord.ButtonStyle.primary,
            emoji=EMOJI_NOTICE,
            custom_id="panel_notice"
        )

    def product_button(self):
        return discord.ui.Button(
            label="제품",
            style=discord.ButtonStyle.success,
            emoji=EMOJI_PRODUCT,
            custom_id="panel_product"
        )

    def charge_button(self):
        return discord.ui.Button(
            label="충전",
            style=discord.ButtonStyle.success,
            emoji=EMOJI_CHARGE,
            custom_id="panel_charge"
        )

    def buy_button(self):
        return discord.ui.Button(
            label="구매",
            style=discord.ButtonStyle.primary,
            emoji=EMOJI_BUY,
            custom_id="panel_buy"
        )

    def info_button(self):
        return discord.ui.Button(
            label="내 정보",
            style=discord.ButtonStyle.primary,
            emoji=EMOJI_INFO,
            custom_id="panel_info"
        )

    def placeholder_button(self):
        return discord.ui.Button(
            label=" ",
            style=discord.ButtonStyle.secondary,
            disabled=True
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

@bot.tree.command(name="버튼패널", description="윈드 OTT 버튼 패널을 표시합니다.")
async def button_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="윈드 OTT",
        description="아래 원하시는 버튼을 눌러 이용해주세요!",
        color=ROY_TEAL
    )
    view = ButtonPanel()

    # 버튼 콜백 매핑
    for item in view.children:
        if isinstance(item, discord.ui.Button) and getattr(item, "custom_id", None):
            async def make_callback(i: discord.Interaction, cid=item.custom_id):
                if cid == "panel_notice":
                    await i.response.send_message(f"{EMOJI_NOTICE} 공지사항을 확인해줘!", ephemeral=True)
                elif cid == "panel_product":
                    await i.response.send_message(f"{EMOJI_PRODUCT} 제품 목록을 불러왔어!", ephemeral=True)
                elif cid == "panel_charge":
                    await i.response.send_message(f"{EMOJI_CHARGE} 충전 페이지로 안내할게!", ephemeral=True)
                elif cid == "panel_buy":
                    await i.response.send_message(f"{EMOJI_BUY} 구매 절차를 시작할게!", ephemeral=True)
                elif cid == "panel_info":
                    user = i.user
                    await i.response.send_message(f"{EMOJI_INFO} {user.mention}님의 정보입니다.", ephemeral=True)
                else:
                    await i.response.send_message("지원하지 않는 버튼이야.", ephemeral=True)
            item.callback = make_callback

    await interaction.response.send_message(embed=embed, view=view)

@bot.event
async def on_ready():
    try:
        # 길드 전용 동기화: 네 서버에만 바로 등록돼서 반영 빠름
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"길드 슬래시 커맨드 동기화 완료({GUILD_ID}): {len(synced)}개")
    except Exception as e:
        print(f"동기화 오류: {e}")
    print(f"로그인: {bot.user} (준비 완료)")

TOKEN = os.getenv("DISCORD_TOKEN", "여기에_토큰_넣기")
bot.run(TOKEN)
