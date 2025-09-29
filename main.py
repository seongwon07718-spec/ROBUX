import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands

# ----- 기본 설정 -----
INTENTS = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=INTENTS)

GUILD_ID = None  # 특정 길드만 테스트할 때 ID 넣기 (예: 123456789012345678)
COLOR_GRAY = 0x2F3136  # 디스코드 다크 회색 톤

# ----- PartialEmoji 세팅 -----
# 제목/정보 라인에 쓰는 애니메 이모지
EMO_LIVE = discord.PartialEmoji.from_str("<a:upuoipipi:1421392209089007718>")

# 버튼 아이콘들
EMO_NOTICE = discord.PartialEmoji.from_str("<a:notification:1422183909013196880>")
EMO_BUY = discord.PartialEmoji.from_str("<a:myst_cart:1422183911466733630>")
EMO_CHARGE = discord.PartialEmoji.from_str("<a:11845034938353746621:1421383445669613660>")
EMO_MYINFO = discord.PartialEmoji.from_str("<:1306285145132892180:1421336642828111922>")

# ----- 실시간 데이터 placeholder 함수 -----
# 나중에 DB/외부 API 연동해서 값 채워넣으면 됨
async def get_realtime_data():
    # 예시 값들
    price = "예시"
    stock = "예시"
    sales = "예시"
    return price, stock, sales

# ----- 뷰/버튼 구성 -----
class ButtonPanelView(discord.ui.View):
    def __init__(self, *, timeout: float | None = 120):
        super().__init__(timeout=timeout)
        # 회색 버튼은 ButtonStyle.secondary
        self.add_item(discord.ui.Button(
            label="공지사항",
            style=discord.ButtonStyle.secondary,
            emoji=EMO_NOTICE,
            custom_id="btn_notice"
        ))
        self.add_item(discord.ui.Button(
            label="구매",
            style=discord.ButtonStyle.secondary,
            emoji=EMO_BUY,
            custom_id="btn_buy"
        ))
        self.add_item(discord.ui.Button(
            label="충전",
            style=discord.ButtonStyle.secondary,
            emoji=EMO_CHARGE,
            custom_id="btn_charge"
        ))
        self.add_item(discord.ui.Button(
            label="내 정보",
            style=discord.ButtonStyle.secondary,
            emoji=EMO_MYINFO,
            custom_id="btn_myinfo"
        ))

    # 버튼 콜백들
    @discord.ui.button(label="공지사항", style=discord.ButtonStyle.secondary, emoji=EMO_NOTICE, custom_id="btn_notice_hidden", row=4)
    async def hidden_notice(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 이건 보이지 않게 할 용도 아니고, 위에서 add_item로 이미 추가했으니 사용 안 함
        pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # 필요시 권한/역할 체크 넣기
        return True

    async def on_timeout(self):
        # 타임아웃 시 버튼 비활성화 하고 싶으면 여기서 처리
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

# 개별 버튼 핸들러는 on_interaction_create로 처리
@bot.event
async def on_interaction(interaction: discord.Interaction):
    # 슬래시 커맨드는 app_commands 라우터가 처리하니 여기선 custom_id만 체크
    if interaction.type == discord.InteractionType.component and interaction.data:
        cid = interaction.data.get("custom_id")
        if cid == "btn_notice":
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("공지사항 패널로 이동할게. 여기에 최신 공지 불러오는 로직 붙이면 됨.", ephemeral=True)
        elif cid == "btn_buy":
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("구매 플로우 시작! 상품 선택 → 수량 입력 → 결제 로직 연결해줘.", ephemeral=True)
        elif cid == "btn_charge":
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("충전 메뉴로 이동. 잔액 충전/웹훅 결제/코드입력 등 붙이면 됨.", ephemeral=True)
        elif cid == "btn_myinfo":
            await interaction.response.defer(ephemeral=True)
            # 여기서 유저별 '내 정보' 불러와서 임베드로 보여줘
            embed = discord.Embed(
                title="내 정보",
                description="• 잔액: 예시\n• 누적 금액: 예시\n• 등급: 예시\n• 최근 주문: 예시",
                color=COLOR_GRAY
            )
            embed.set_footer(text=f"요청자: {interaction.user}")
            await interaction.followup.send(embed=embed, ephemeral=True)

# ----- 슬래시 커맨드 -----
class PanelCog(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    @app_commands.command(name="버튼패널", description="자동화 로벅스 버튼 패널을 불러옵니다.")
    async def button_panel(self, interaction: discord.Interaction):
        price, stock, sales = await get_realtime_data()
        title = "자동화 로벅스"

        # 설명부 텍스트
        desc_lines = [
            f"{EMO_LIVE} 실시간 가격 : `{price}`",
            f"{EMO_LIVE} 실시간 재고 : `{stock}`",
            f"{EMO_LIVE} 실시간 판매량 : `{sales}`",
            "",
            "아래 버튼을 선택하여 이용해주세요"
        ]
        description = "\n".join(desc_lines)

        embed = discord.Embed(title=title, description=description, color=COLOR_GRAY)
        view = ButtonPanelView(timeout=180)

        await interaction.response.send_message(embed=embed, view=view)

async def setup_hook():
    await bot.add_cog(PanelCog(bot))
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        await bot.tree.sync(guild=guild)
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
        raise RuntimeError("환경변수 DISCORD_TOKEN을 설정해줘.")
    bot.run(token)

if __name__ == "__main__":
    main()
