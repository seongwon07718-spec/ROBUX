import os
import discord
from discord import app_commands
from discord.ext import commands

INTENTS = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=INTENTS)

GUILD_ID = None
COLOR_GRAY = 0x2F3136

# PartialEmoji
EMO_LIVE = discord.PartialEmoji.from_str("<a:upuoipipi:1421392209089007718>")
EMO_NOTICE = discord.PartialEmoji.from_str("<a:notification:1422183909013196880>")
EMO_BUY = discord.PartialEmoji.from_str("<a:myst_cart:1422183911466733630>")
EMO_CHARGE = discord.PartialEmoji.from_str("<a:11845034938353746621:1421383445669613660>")
EMO_MYINFO = discord.PartialEmoji.from_str("<:1306285145132892180:1421336642828111922>")

async def get_realtime_data():
    return "예시", "예시", "예시"

class ButtonPanelView(discord.ui.View):
    def __init__(self, *, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        # 2x2 레이아웃: row=0 두 개, row=1 두 개
        self.add_item(discord.ui.Button(
            label="공지사항",
            style=discord.ButtonStyle.secondary,
            emoji=EMO_NOTICE,
            custom_id="btn_notice",
            row=0
        ))
        self.add_item(discord.ui.Button(
            label="구매",
            style=discord.ButtonStyle.secondary,
            emoji=EMO_BUY,
            custom_id="btn_buy",
            row=0
        ))
        self.add_item(discord.ui.Button(
            label="충전",
            style=discord.ButtonStyle.secondary,
            emoji=EMO_CHARGE,
            custom_id="btn_charge",
            row=1
        ))
        self.add_item(discord.ui.Button(
            label="내 정보",
            style=discord.ButtonStyle.secondary,
            emoji=EMO_MYINFO,
            custom_id="btn_myinfo",
            row=1
        ))

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component and interaction.data:
        cid = interaction.data.get("custom_id")
        if cid == "btn_notice":
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("공지사항 패널로 이동합니다. 여기에 공지 불러오기 로직을 붙이세요.", ephemeral=True)
        elif cid == "btn_buy":
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("구매 플로우 시작! 상품 선택 → 수량 입력 → 결제.", ephemeral=True)
        elif cid == "btn_charge":
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("충전 메뉴로 이동. 잔액 충전/코드 입력/웹훅 연동 등 구현.", ephemeral=True)
        elif cid == "btn_myinfo":
            await interaction.response.defer(ephemeral=True)
            embed = discord.Embed(
                title="내 정보",
                description="• 잔액: 예시\n• 누적 금액: 예시\n• 등급: 예시\n• 최근 주문: 예시",
                color=COLOR_GRAY
            )
            embed.set_footer(text=f"요청자: {interaction.user}")
            await interaction.followup.send(embed=embed, ephemeral=True)

class PanelCog(commands.Cog):
    def __init__(self, bot_):
        self.bot = bot_

    @app_commands.command(name="버튼패널", description="자동화 로벅스 버튼 패널을 불러옵니다.")
    async def button_panel(self, interaction: discord.Interaction):
        price, stock, sales = await get_realtime_data()

        # 제목
        title = "자동화 로벅스"

        # 임베드 본문: 헤더 크기 확대는 불가 → 굵게 처리로 강조
        description = (
            f"{EMO_LIVE} **실시간 가격** : `{price}`\n"
            f"{EMO_LIVE} **실시간 재고** : `{stock}`\n"
            f"{EMO_LIVE} **실시간 판매량** : `{sales}`\n\n"
            "아래 버튼을 선택하여 이용해주세요"
        )

        embed = discord.Embed(title=title, description=description, color=COLOR_GRAY)
        view = ButtonPanelView(timeout=180)

        await interaction.response.send_message(embed=embed, view=view)

async def setup_hook():
    await bot.add_cog(PanelCog(bot))
    if GUILD_ID:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    else:
        await bot.tree.sync()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    try:
        await setup_hook()
        print("Slash commands synced.")
    except Exception as e:
        print("Sync error:", e)

def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("환경변수 DISCORD_TOKEN이 설정되어 있지 않음")
    bot.run(token)

if __name__ == "__main__":
    main()
