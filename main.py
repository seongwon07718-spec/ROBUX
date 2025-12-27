import discord
from discord import ui
from discord.ext import commands
intents= discord.Intents.all()

bot = commands.Bot(".", intents=intents)

class MeuLayout(ui.View):
    def __init__(self):
        super().__init__()

        container = ui.Container(ui.TextDisplay("**로블록스 쿠키 체커기**"))
        container.add_item(ui.Button(label="로블록스 쿠키 체커기 시작", style=discord.ButtonStyle.gray, custom_id="start_checker"))
        self.add_item(container)

@bot.command()
async def teste(ctx:commands.Context):
    layout = MeuLayout()
    await ctx.reply(view=layout)

bot.run("")
