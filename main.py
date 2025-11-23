import asyncio
import time
import disnake
from disnake.ext import commands

bot = commands.Bot(command_prefix="!", intents=disnake.Intents.default())

@bot.slash_command(description="임베드에 60초 타임스탬프 카운트업")
async def 타임스탬프카운터(interaction: disnake.ApplicationCommandInteraction):
    await interaction.response.send_message("타임스탬프 카운트업 시작", ephemeral=False)
    message = await interaction.original_message()

    start_ts = int(time.time())
    while True:
        current_ts = int(time.time())
        elapsed = current_ts - start_ts
        seconds = elapsed % 60
        if seconds == 0:
            seconds = 60

        display_ts = current_ts - seconds + 1
        timestamp_str = f"<t:{display_ts}:R>"

        embed = disnake.Embed(title="실시간 타임스탬프 카운트업")
        embed.add_field(name="마지막 업데이트", value=timestamp_str)

        await message.edit(embed=embed)
        await asyncio.sleep(1)
