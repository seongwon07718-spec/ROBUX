import discord
from discord.ext import commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} 온라인!")


class PanelContainer(discord.ui.Container):
    text = discord.ui.TextDisplay("## 🛒 구매 패널\n원하는 항목을 선택하세요.")
    sep = discord.ui.Separator()
    row = discord.ui.ActionRow()

    @row.button(label="🛍️ 구매", style=discord.ButtonStyle.primary, custom_id="panel_buy")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🛍️ **구매** 메뉴입니다.", ephemeral=True)

    @row.button(label="📦 제품", style=discord.ButtonStyle.secondary, custom_id="panel_product")
    async def product_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📦 **제품** 목록입니다.", ephemeral=True)

    @row.button(label="💳 충전", style=discord.ButtonStyle.success, custom_id="panel_charge")
    async def charge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("💳 **충전** 메뉴입니다.", ephemeral=True)

    @row.button(label="ℹ️ 정보", style=discord.ButtonStyle.secondary, custom_id="panel_info")
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("ℹ️ **정보** 페이지입니다.", ephemeral=True)


class PanelLayout(discord.ui.LayoutView):
    container = PanelContainer(accent_color=0x5865F2)


@bot.tree.command(name="panel", description="구매 패널을 표시합니다.")
async def panel(interaction: discord.Interaction):
    await interaction.response.send_message(view=PanelLayout())


bot.run("YOUR_BOT_TOKEN")
