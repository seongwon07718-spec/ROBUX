# pip install -U discord.py

import os
import discord
from discord import app_commands
from discord.ext import commands

GUILD_ID = 1419200424636055592  # 네 서버 ID

# '뢰색' 톤
ROY_TEAL = discord.Color.from_str("#2AB2A6")

# 커스텀 이모지 (서버에서 사용 가능한지 확인)
EMOJI_NOTICE = "<a:book:1421336655545106572>"
EMOJI_PRODUCT = "<a:sakfnmasfagfamg:1421336645084512537>"
EMOJI_CHARGE = "<a:upuoipipi:1421392209089007718>"
EMOJI_BUY = "<a:thumbsuppp:1421336653389365289>"
EMOJI_INFO = "<a:list:1421336647303172107>"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


class ButtonPanel(discord.ui.View):
    def __init__(self):
        # 3분 후 비활성
        super().__init__(timeout=180)

        # 1행: 공지사항 | 제품 | 충전
        self.notice_btn = discord.ui.Button(
            label="공지사항",
            style=discord.ButtonStyle.primary,
            emoji=EMOJI_NOTICE,
            custom_id="panel_notice",
            row=0
        )
        self.product_btn = discord.ui.Button(
            label="제품",
            style=discord.ButtonStyle.success,
            emoji=EMOJI_PRODUCT,
            custom_id="panel_product",
            row=0
        )
        self.charge_btn = discord.ui.Button(
            label="충전",
            style=discord.ButtonStyle.success,
            emoji=EMOJI_CHARGE,
            custom_id="panel_charge",
            row=0
        )

        # 2행: 구매 | 내 정보 | 자리채움(비활성)
        self.buy_btn = discord.ui.Button(
            label="구매",
            style=discord.ButtonStyle.primary,
            emoji=EMOJI_BUY,
            custom_id="panel_buy",
            row=1
        )
        self.info_btn = discord.ui.Button(
            label="내 정보",
            style=discord.ButtonStyle.primary,
            emoji=EMOJI_INFO,
            custom_id="panel_info",
            row=1
        )
        self.placeholder_btn = discord.ui.Button(
            label="자리 채움",
            style=discord.ButtonStyle.secondary,
            disabled=True,
            custom_id="panel_placeholder",
            row=1
        )

        # View에 추가
        self.add_item(self.notice_btn)
        self.add_item(self.product_btn)
        self.add_item(self.charge_btn)
        self.add_item(self.buy_btn)
        self.add_item(self.info_btn)
        self.add_item(self.placeholder_btn)

        # 콜백 바인딩
        self.notice_btn.callback = self.on_notice
        self.product_btn.callback = self.on_product
        self.charge_btn.callback = self.on_charge
        self.buy_btn.callback = self.on_buy
        self.info_btn.callback = self.on_info
        # placeholder는 disabled라 콜백 필요 없음

    # 콜백들
    async def on_notice(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{EMOJI_NOTICE} 공지사항을 확인해줘!", ephemeral=True)

    async def on_product(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{EMOJI_PRODUCT} 제품 목록을 불러왔어!", ephemeral=True)

    async def on_charge(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{EMOJI_CHARGE} 충전 페이지로 안내할게!", ephemeral=True)

    async def on_buy(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{EMOJI_BUY} 구매 절차를 시작할게!", ephemeral=True)

    async def on_info(self, interaction: discord.Interaction):
        user = interaction.user
        await interaction.response.send_message(f"{EMOJI_INFO} {user.mention}님의 정보입니다.", ephemeral=True)

    async def on_timeout(self):
        # 타임아웃 시 비활성화 후 메시지 편집
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
    await interaction.response.send_message(embed=embed, view=view)


@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"길드 슬래시 커맨드 동기화 완료({GUILD_ID}): {len(synced)}개")
    except Exception as e:
        print(f"동기화 오류: {e}")
    print(f"로그인: {bot.user} (준비 완료)")


TOKEN = os.getenv("DISCORD_TOKEN", "여기에_토큰_넣기")
bot.run(TOKEN)
