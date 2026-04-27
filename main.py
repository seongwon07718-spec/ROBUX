import discord
from discord.ext import commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user}")


class PanelContainer(discord.ui.Container):
    text = discord.ui.TextDisplay("## 구매하기\n원하는 항목을 선택하세요")
    sep = discord.ui.Separator()
    row = discord.ui.ActionRow()

    @row.button(label="구매", style=discord.ButtonStyle.secondary, custom_id="panel_buy", emoji="<:1302328398856847474:1498278220087431188>")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**구매** 메뉴입니다.", ephemeral=True)

    @row.button(label="제품", style=discord.ButtonStyle.secondary, custom_id="panel_product", emoji="<:1302328347765899395:1498278218644324543>")
    async def product_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**제품** 목록입니다.", ephemeral=True)

    @row.button(label="충전", style=discord.ButtonStyle.secondary, custom_id="panel_charge", emoji="<:1302328427545624689:1498278217017196594>")
    async def charge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**충전** 메뉴입니다.", ephemeral=True)

    @row.button(label="정보", style=discord.ButtonStyle.secondary, custom_id="panel_info", emoji="<:1306285145132892180:1498278215116919029>")
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**정보** 페이지입니다.", ephemeral=True)


class PanelLayout(discord.ui.LayoutView):
    container = PanelContainer(accent_color=0xffffff)


@bot.tree.command(name="panel", description="구매 패널을 표시합니다")
async def panel(interaction: discord.Interaction):
    await interaction.response.send_message(view=PanelLayout())
