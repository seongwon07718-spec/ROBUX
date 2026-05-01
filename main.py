import discord, asyncio

async def clear():
    bot = discord.Client(intents=discord.Intents.default())
    await bot.login("토큰")
    tree = discord.app_commands.CommandTree(bot)
    # 명령어 등록된 서버 ID 전부 넣기
    await tree.sync(guild=discord.Object(id=서버ID))
    await bot.close()

asyncio.run(clear())
