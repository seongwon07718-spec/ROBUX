import discord
from discord import app_commands, ui

TOKEN = ''

class vending(ui.LayoutView):

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

        con = ui.Container()
        con.accent_color = 0xffffff

        con.add_item(ui.TextDisplay("### 테스트"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        charge = ui.Button(label="충전", custom_id="charge", style=discord.ButtonStyle.gray)
        charge.callback = self.change_callback

        info = ui.Button(label="정보", custom_id="info", style=discord.ButtonStyle.gray)
        info.callback = self.info_callback

        shop = ui.Button(label="구매", custom_id="buying", style=discord.ButtonStyle.gray)
        shop.callback = self.shop_callback

        calc = ui.Button(label="계산", custom_id="calc", style=discord.ButtonStyle.gray)
        calc.callback = self.calc_callback

        con.add_item(ui.ActionRow(charge, info, shop, calc))
        self.add_item(con)
        return con
    
    async def change_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("충전 메뉴입니다.", ephemeral=True)

    async def info_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("정보 페이지입니다.", ephemeral=True)

    async def shop_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("구매 창을 엽니다.", ephemeral=True)

    async def calc_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("계산 페이지입니다.", ephemeral=True)

class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"{self.user}")

bot = MyBot()

@bot.tree.command(name="자판기", description="자판기 메뉴를 불러옵니다")
async def vending(it: discord.Interaction):
    view = vending(bot)
    await it.response.send_message(view=view)

bot.run(TOKEN)
