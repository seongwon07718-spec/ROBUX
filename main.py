import os
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN         = os.environ["DISCORD_TOKEN"]
DISCORD_CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
SERVER_URL            = os.environ.get("SERVER_URL", "http://localhost:5000")
GUILD_ID              = os.environ.get("ADMIN_GUILD_ID")

intents = discord.Intents.default()
bot     = commands.Bot(command_prefix="!", intents=intents)
tree    = bot.tree


class AdminAccountModal(discord.ui.Modal, title="🔐 관리자 계정 생성"):
    email = discord.ui.TextInput(label="이메일", placeholder="admin@example.com", required=True, max_length=100)
    password = discord.ui.TextInput(label="비밀번호", placeholder="8자 이상", required=True, min_length=8, max_length=100)
    password_confirm = discord.ui.TextInput(label="비밀번호 확인", placeholder="비밀번호 재입력", required=True, min_length=8, max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        if self.password.value != self.password_confirm.value:
            await interaction.response.send_message("❌ 비밀번호가 일치하지 않습니다.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            async with aiohttp.ClientSession() as sess:
                resp = await sess.post(
                    f"{SERVER_URL}/internal/create_admin",
                    json={"email": self.email.value.strip(), "password": self.password.value},
                    headers={"X-Discord-Client-Secret": DISCORD_CLIENT_SECRET},
                    timeout=aiohttp.ClientTimeout(total=10),
                )
                data = await resp.json()

            if resp.status == 200:
                await interaction.followup.send(
                    f"✅ **관리자 계정 생성 완료!**\n```\n이메일: {self.email.value.strip()}\n```",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(f"❌ {data.get('message', '오류 발생')}", ephemeral=True)

        except aiohttp.ClientConnectorError:
            await interaction.followup.send("❌ 서버에 연결할 수 없습니다. server.py를 확인하세요.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ 오류: `{e}`", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message(f"❌ {error}", ephemeral=True)


@tree.command(name="관리자_아이디", description="관리자 계정을 생성합니다 (서버 관리자 전용)")
@app_commands.checks.has_permissions(administrator=True)
async def cmd_admin_create(interaction: discord.Interaction):
    await interaction.response.send_modal(AdminAccountModal())

@cmd_admin_create.error
async def cmd_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ 서버 관리자만 사용 가능합니다.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ {error}", ephemeral=True)


@bot.event
async def on_ready():
    print(f"[봇] {bot.user} 준비 완료")
    if GUILD_ID:
        guild = discord.Object(id=int(GUILD_ID))
        tree.copy_global_to(guild=guild)
        synced = await tree.sync(guild=guild)
    else:
        synced = await tree.sync()
    print(f"[봇] 슬래시 명령어 동기화: {len(synced)}개")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
