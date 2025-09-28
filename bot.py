import os
import asyncio
from dotenv import load_dotenv
import discord
from discord import app_commands

load_dotenv()
TOKEN = os.getenv("TOKEN")  # 디스코드 봇 토큰
GUILD_ID = os.getenv("GUILD_ID")  # 테스트 서버(길드) ID: 선택사항(빠른 동기화용)

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # 길드 지정하면 즉시(수 초 내) 동기화, 전역은 전파 수분 소요
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print("길드 슬래시 명령 동기화 완료")
        else:
            await self.tree.sync()
            print("전역 슬래시 명령 동기화 완료(전파에 수분 걸릴 수 있음)")

client = MyClient()

@client.tree.command(name="hello", description="간단한 인사하기")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("안녕! 튜어오오오옹 ㅎㅎ")

@client.event
async def on_ready():
    print(f"로그인 성공: {client.user} (ID: {client.user.id})")

def main():
    if not TOKEN:
        raise RuntimeError("TOKEN이 .env에 없음")
    client.run(TOKEN)

if __name__ == "__main__":
    main()
