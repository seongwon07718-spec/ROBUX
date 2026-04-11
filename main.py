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


# ─────────────────────────────────────────────
# 관리자 계정 생성 모달
# ─────────────────────────────────────────────
class AdminAccountModal(discord.ui.Modal, title="🔐 관리자 계정 생성"):
    email = discord.ui.TextInput(
        label="이메일",
        placeholder="admin@example.com",
        required=True,
        max_length=100
    )
    password = discord.ui.TextInput(
        label="비밀번호",
        placeholder="8자 이상",
        required=True,
        min_length=8,
        max_length=100
    )
    password_confirm = discord.ui.TextInput(
        label="비밀번호 확인",
        placeholder="비밀번호 재입력",
        required=True,
        min_length=8,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.password.value != self.password_confirm.value:
            con = discord.ui.Container(accent_colour=discord.Colour(0xED4245))
            con.add_item(discord.ui.TextDisplay(
                "### ❌ 비밀번호 불일치\n"
                "-# 비밀번호가 일치하지 않습니다. 다시 시도해주세요."
            ))
            await interaction.response.send_message(components=[con], ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            async with aiohttp.ClientSession() as sess:
                resp = await sess.post(
                    f"{SERVER_URL}/internal/create_admin",
                    json={
                        "email":    self.email.value.strip(),
                        "password": self.password.value,
                    },
                    headers={"X-Discord-Client-Secret": DISCORD_CLIENT_SECRET},
                    timeout=aiohttp.ClientTimeout(total=10),
                )
                data = await resp.json()

            if resp.status == 200:
                con = discord.ui.Container(accent_colour=discord.Colour(0x57F287))
                con.add_item(discord.ui.TextDisplay(
                    "### ✅ 관리자 계정 생성 완료"
                ))
                con.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                con.add_item(discord.ui.TextDisplay(
                    f"-# - **이메일**: {self.email.value.strip()}\n"
                    f"-# 웹사이트에서 관리자 대시보드에 접근할 수 있습니다."
                ))
                btn = discord.ui.Button(
                    label="대시보드 바로가기",
                    style=discord.ButtonStyle.link,
                    url="https://sailor-piece.shop/admin/dashboard"
                )
                con.add_item(discord.ui.ActionRow(btn))
                await interaction.followup.send(components=[con], ephemeral=True)

            else:
                con = discord.ui.Container(accent_colour=discord.Colour(0xED4245))
                con.add_item(discord.ui.TextDisplay(
                    f"### ❌ 오류\n"
                    f"-# {data.get('message', '알 수 없는 오류')}"
                ))
                await interaction.followup.send(components=[con], ephemeral=True)

        except aiohttp.ClientConnectorError:
            con = discord.ui.Container(accent_colour=discord.Colour(0xED4245))
            con.add_item(discord.ui.TextDisplay(
                "### ❌ 서버 연결 실패\n"
                "-# server.py 가 실행 중인지 확인하세요."
            ))
            await interaction.followup.send(components=[con], ephemeral=True)

        except Exception as e:
            con = discord.ui.Container(accent_colour=discord.Colour(0xED4245))
            con.add_item(discord.ui.TextDisplay(f"### ❌ 예외\n-# `{e}`"))
            await interaction.followup.send(components=[con], ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        con = discord.ui.Container(accent_colour=discord.Colour(0xED4245))
        con.add_item(discord.ui.TextDisplay(f"### ❌ 오류\n-# {error}"))
        await interaction.response.send_message(components=[con], ephemeral=True)


# ─────────────────────────────────────────────
# 슬래시 명령어
# ─────────────────────────────────────────────
@tree.command(name="관리자_아이디", description="관리자 계정을 생성합니다 (서버 관리자 전용)")
@app_commands.checks.has_permissions(administrator=True)
async def cmd_admin_create(interaction: discord.Interaction):
    await interaction.response.send_modal(AdminAccountModal())

@cmd_admin_create.error
async def cmd_error(interaction: discord.Interaction, error):
    con = discord.ui.Container(accent_colour=discord.Colour(0xED4245))
    if isinstance(error, app_commands.MissingPermissions):
        con.add_item(discord.ui.TextDisplay(
            "### ❌ 권한 없음\n-# 서버 관리자만 사용할 수 있습니다."
        ))
    else:
        con.add_item(discord.ui.TextDisplay(f"### ❌ 오류\n-# {error}"))
    await interaction.response.send_message(components=[con], ephemeral=True)


# ─────────────────────────────────────────────
# 봇 준비
# ─────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"[봇] {bot.user} 준비 완료")
    if GUILD_ID:
        guild = discord.Object(id=int(GUILD_ID))
        tree.copy_global_to(guild=guild)
        synced = await tree.sync(guild=guild)
    else:
        synced = await tree.sync()
    print(f"[봇] 명령어 동기화: {len(synced)}개")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
