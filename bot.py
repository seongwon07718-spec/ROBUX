import os
import discord
from discord import app_commands

TOKEN = os.getenv("TOKEN")          # 디스코드 봇 토큰
GUILD_ID = os.getenv("GUILD_ID")    # 테스트 서버 ID(선택, 즉시 동기화용)

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # hello 명령 보장
        @self.tree.command(name="hello", description="간단 인사")
        async def hello(interaction: discord.Interaction):
            await interaction.response.send_message("안녕! 튜어오오오옹 ㅎㅎ")

        try:
            if GUILD_ID:
                gid = int(GUILD_ID)
                print(f"[sync] guild={gid}")
                await self.tree.sync(guild=discord.Object(id=gid))
                print("[sync] 길드 동기화 OK")
            else:
                print("[sync] global sync")
                await self.tree.sync()
                print("[sync] 전역 동기화 OK(전파 지연 가능)")
        except Exception as e:
            print(f"[sync][ERR] {type(e).__name__}: {e}", flush=True)

client = MyClient()

@client.event
async def on_ready():
    print(f"[ready] 로그인: {client.user} (ID: {client.user.id})")

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("TOKEN 비었음")
    # Zeabur 로그 핸들러 충돌 방지
    client.run(TOKEN, log_handler=None
