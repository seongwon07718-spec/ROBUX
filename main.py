# pip install -U discord.py

import os
import discord
from discord.ext import commands

# 네 서버 ID
GUILD_ID = 1419200424636055592

# 회색 임베드 컬러
GRAY = discord.Color.from_str("#808080")

# 커스텀 이모지
EMOJI_NOTICE = "<:ticket:1422579515955085388>"
EMOJI_CHARGE = "<:charge:1422579517679075448>"
EMOJI_INFO   = "<:info:1422579514218905731>"
EMOJI_BUY    = "<a:11845034938353746621:1421383445669613660>"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


class ButtonPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

        # 2x2 버튼 구성 (모두 회색 스타일)
        self.notice_btn = discord.ui.Button(
            label="공지사항",
            style=discord.ButtonStyle.secondary,
            emoji=EMOJI_NOTICE,
            custom_id="panel_notice",
            row=0
        )
        self.charge_btn = discord.ui.Button(
            label="충전",
            style=discord.ButtonStyle.secondary,
            emoji=EMOJI_CHARGE,
            custom_id="panel_charge",
            row=0
        )
        self.info_btn = discord.ui.Button(
            label="내 정보",
            style=discord.ButtonStyle.secondary,
            emoji=EMOJI_INFO,
            custom_id="panel_info",
            row=1
        )
        self.buy_btn = discord.ui.Button(
            label="구매",
            style=discord.ButtonStyle.secondary,
            emoji=EMOJI_BUY,
            custom_id="panel_buy",
            row=1
        )

        self.add_item(self.notice_btn)
        self.add_item(self.charge_btn)
        self.add_item(self.info_btn)
        self.add_item(self.buy_btn)

        # 콜백 바인딩
        self.notice_btn.callback = self.on_notice
        self.charge_btn.callback = self.on_charge
        self.info_btn.callback = self.on_info
        self.buy_btn.callback = self.on_buy

    # 공지사항: 회색 임베드 + 나만 보이게
    async def on_notice(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="공지사항",
            description=(
                "서버규칙 필독 부탁드립니다\n"
                "구매후 이용후기는 필수입니다\n"
                "자충 오류시 티켓 열어주세요"
            ),
            color=GRAY
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # 충전
    async def on_charge(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{EMOJI_CHARGE} 충전 페이지로 안내할게!", ephemeral=True)

    # 내 정보: 회색 임베드 + 나만 보이게, 예시 값 표시
    async def on_info(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="내 정보",
            description=(
                "보유 금액 : `예시`원\n"
                "누적 금액 : `예시`원\n"
                "거래 횟수 : `예시`번"
            ),
            color=GRAY
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # 구매
    async def on_buy(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{EMOJI_BUY} 구매 절차를 시작할게!", ephemeral=True)

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


@bot.tree.command(name="버튼패널", description="윈드 OTT 버튼 패널을 표시합니다.")
async def button_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="윈드 OTT",
        description="아래 원하시는 버튼을 눌러 이용해주세요!",
        color=GRAY
    )
    view = ButtonPanel()
    await interaction.response.send_message(embed=embed, view=view)


@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)  # 길드 전용 동기화
        print(f"길드 슬래시 커맨드 동기화 완료({GUILD_ID}): {len(synced)}개")
    except Exception as e:
        print(f"동기화 오류: {e}")
    print(f"로그인: {bot.user} (준비 완료)")


TOKEN = os.getenv("DISCORD_TOKEN", "여기에_토큰_넣기")
bot.run(TOKEN)
