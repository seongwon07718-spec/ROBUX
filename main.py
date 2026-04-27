import discord
from discord.ext import commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ─── 수정 가능한 은행 정보 ────────────────────────────────
BANK_NAME = "국민은행"
BANK_ACCOUNT = "000000-00-000000"
BANK_OWNER = "홍길동"
# ─────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user}")


# ─── 입금 모달 ───────────────────────────────────────────
class DepositModal(discord.ui.Modal, title="계좌이체 충전"):
    name = discord.ui.TextInput(
        label="입금자명",
        placeholder="입금자명을 입력하세요",
        required=True
    )
    amount = discord.ui.TextInput(
        label="충전할 금액",
        placeholder="예) 10000",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        class BankContainer(discord.ui.Container):
            text = discord.ui.TextDisplay(
                f"## 🏦 계좌 정보\n"
                f"입금자명: **{self.name.value}**\n"
                f"충전 금액: **{self.amount.value}원**\n\n"
                f"**은행명:** {BANK_NAME}\n"
                f"**계좌번호:** {BANK_ACCOUNT}\n"
                f"**예금주:** {BANK_OWNER}\n\n"
                f"입금 확인 후 자동으로 충전됩니다."
            )

        class BankLayout(discord.ui.LayoutView):
            container = BankContainer(accent_color=0x5865F2)

        await interaction.response.send_message(view=BankLayout(), ephemeral=True)


# ─── 충전 방법 선택 컨테이너 ──────────────────────────────
class ChargeContainer(discord.ui.Container):
    text = discord.ui.TextDisplay("## 💳 충전 방법 선택\n원하는 충전 방법을 선택하세요.")
    sep = discord.ui.Separator(divider=True)
    row = discord.ui.ActionRow()

    @row.button(label="계좌이체", style=discord.ButtonStyle.secondary, custom_id="charge_bank", emoji="🏦")
    async def bank_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DepositModal())

    @row.button(label="코인결제", style=discord.ButtonStyle.secondary, custom_id="charge_coin", emoji="🪙")
    async def coin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🪙 **코인결제** 메뉴입니다.", ephemeral=True)


class ChargeLayout(discord.ui.LayoutView):
    container = ChargeContainer(accent_color=0xffffff)


# ─── 메인 패널 컨테이너 ───────────────────────────────────
class PanelContainer(discord.ui.Container):
    text = discord.ui.TextDisplay("## 구매하기\n원하는 항목을 선택하세요")
    sep = discord.ui.Separator(divider=True)
    image = discord.ui.MediaGallery(
        discord.MediaGalleryItem(media="https://여기에이미지URL.png")
    )
    sep2 = discord.ui.Separator(divider=True)
    row = discord.ui.ActionRow()

    @row.button(label="구매", style=discord.ButtonStyle.secondary, custom_id="panel_buy", emoji="<:1302328398856847474:1498278220087431188>")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**구매** 메뉴입니다.", ephemeral=True)

    @row.button(label="제품", style=discord.ButtonStyle.secondary, custom_id="panel_product", emoji="<:1302328347765899395:1498278218644324543>")
    async def product_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**제품** 목록입니다.", ephemeral=True)

    @row.button(label="충전", style=discord.ButtonStyle.secondary, custom_id="panel_charge", emoji="<:1302328427545624689:1498278217017196594>")
    async def charge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(view=ChargeLayout(), ephemeral=True)

    @row.button(label="정보", style=discord.ButtonStyle.secondary, custom_id="panel_info", emoji="<:1306285145132892180:1498278215116919029>")
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**정보** 페이지입니다.", ephemeral=True)


class PanelLayout(discord.ui.LayoutView):
    container = PanelContainer(accent_color=0xffffff)


@bot.tree.command(name="panel", description="구매 패널을 표시합니다")
async def panel(interaction: discord.Interaction):
    await interaction.response.send_message(view=PanelLayout())


bot.run("YOUR_BOT_TOKEN")
