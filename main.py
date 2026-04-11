import os
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN         = os.environ["DISCORD_TOKEN"]
DISCORD_CLIENT_ID     = os.environ["DISCORD_CLIENT_ID"]
DISCORD_CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
SERVER_URL            = os.environ.get("SERVER_URL", "http://localhost:5000")
GUILD_ID              = os.environ.get("ADMIN_GUILD_ID")

# ── 봇 설정 ──────────────────────────────────────────────
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ── 모달: 이메일 & 비밀번호 입력 ─────────────────────────
class AdminAccountModal(discord.ui.Modal, title="🔐 관리자 계정 생성"):
    email = discord.ui.TextInput(
        label="이메일",
        placeholder="admin@example.com",
        required=True,
        max_length=100,
    )
    password = discord.ui.TextInput(
        label="비밀번호",
        placeholder="8자 이상 입력하세요",
        required=True,
        min_length=8,
        max_length=100,
        style=discord.TextStyle.short,
    )
    password_confirm = discord.ui.TextInput(
        label="비밀번호 확인",
        placeholder="비밀번호를 다시 입력하세요",
        required=True,
        min_length=8,
        max_length=100,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.password.value != self.password_confirm.value:
            await interaction.response.send_message(
                "❌ 비밀번호가 일치하지 않습니다. 다시 시도해주세요.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.post(
                    f"{SERVER_URL}/internal/create_admin",
                    json={
                        "email":    self.email.value.strip(),
                        "password": self.password.value,
                    },
                    # Discord Client Secret을 인증 헤더로 사용
                    headers={"X-Discord-Client-Secret": DISCORD_CLIENT_SECRET},
                    timeout=aiohttp.ClientTimeout(total=10),
                )
                data = await resp.json()

            if resp.status == 200:
                await interaction.followup.send(
                    f"✅ **관리자 계정이 생성되었습니다!**\n"
                    f"```\n이메일: {self.email.value.strip()}\n```\n"
                    f"웹사이트에서 관리자 대시보드에 접근할 수 있습니다.",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    f"❌ 오류: {data.get('message', '알 수 없는 오류')}",
                    ephemeral=True,
                )

        except aiohttp.ClientConnectorError:
            await interaction.followup.send(
                "❌ 서버에 연결할 수 없습니다. `server.py`가 실행 중인지 확인하세요.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(f"❌ 오류: `{e}`", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message(f"❌ 오류: {error}", ephemeral=True)


# ── 슬래시 명령어: /관리자_아이디 ────────────────────────
@tree.command(
    name="관리자_아이디",
    description="관리자 계정을 생성합니다 (서버 관리자 전용)",
)
@app_commands.checks.has_permissions(administrator=True)
async def cmd_admin_create(interaction: discord.Interaction):
    await interaction.response.send_modal(AdminAccountModal())


@cmd_admin_create.error
async def cmd_admin_create_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ 이 명령어는 **서버 관리자**만 사용할 수 있습니다.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(f"❌ 오류: {error}", ephemeral=True)


# ── 봇 준비 ──────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"[봇] {bot.user} 로그인 완료")

    if GUILD_ID:
        guild = discord.Object(id=int(GUILD_ID))
        tree.copy_global_to(guild=guild)
        synced = await tree.sync(guild=guild)
        print(f"[봇] 길드({GUILD_ID}) 명령어 동기화: {len(synced)}개")
    else:
        synced = await tree.sync()
        print(f"[봇] 글로벌 명령어 동기화: {len(synced)}개")

    print(f"[봇] SERVER_URL: {SERVER_URL}")
    print(f"[봇] 준비 완료! /관리자_아이디 명령어를 사용하세요.")


# ── 실행 ─────────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
