# 인증 패널 - 바로 역할 지급 코드 (discord.py v2)
import discord
from discord import app_commands
from discord.ext import commands

# ---------------- 설정 ----------------
BOT_TOKEN = "여기에_봇_토큰"  # 이미 설정된 봇 토큰 사용
TARGET_ROLE_ID = 1441726232088543298  # 부여할 역할 ID (요청하신 값)
OWNER_ID = 1402654236570812467  # 소유자(관리용) - 필요시 변경
# --------------------------------------

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)
tree = bot.tree

# 임베드 템플릿
def embeda(embed_type: str, title: str, description: str):
    color_map = {"success":0x5c6cdf, "error":0xff5c5c, "info":0x5c6cdf}
    color = color_map.get(embed_type, 0x5c6cdf)
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="LinkRestoreBot")
    return embed

# 인증 버튼 뷰 (직접 역할 ID 사용)
class DirectAuthView(discord.ui.View):
    def __init__(self, role_id: int, timeout: int | None = None):
        super().__init__(timeout=timeout)
        self.role_id = role_id

    @discord.ui.button(label="인증 하기", style=discord.ButtonStyle.primary, custom_id="direct_auth_button")
    async def auth_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)  # 비공개 응답 대기
        if not interaction.guild:
            return await interaction.followup.send("서버에서만 사용할 수 있는 버튼입니다.", ephemeral=True)

        # 멤버 & 역할 확인
        member = interaction.user
        role = interaction.guild.get_role(self.role_id)
        if not role:
            return await interaction.followup.send("설정된 인증 역할을 찾을 수 없습니다. 관리자에게 문의하세요.", ephemeral=True)

        # 봇 권한 및 역할 계층 확인
        me = interaction.guild.me
        if not me.guild_permissions.manage_roles:
            return await interaction.followup.send("봇에게 역할 관리 권한이 없습니다. 관리자에게 권한을 부여해 주세요.", ephemeral=True)
        if role.position >= me.top_role.position:
            return await interaction.followup.send("봇의 역할이 인증 역할보다 낮습니다. 역할 순서를 조정해 주세요.", ephemeral=True)

        # 이미 역할이 있으면 안내
        if role in member.roles:
            return await interaction.followup.send(embed=embeda("info", "이미 인증됨", "이미 해당 역할을 보유하고 있습니다."), ephemeral=True)

        # 역할 부여 시도
        try:
            await member.add_roles(role, reason="인증 버튼을 통한 역할 부여")
            await interaction.followup.send(embed=embeda("success", "인증 완료", f"{member.mention}님, 인증 역할이 부여되었습니다."), ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(embed=embeda("error", "권한 오류", "봇에게 역할을 부여할 권한이 없습니다."), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=embeda("error", "오류", f"역할 부여 중 오류가 발생했습니다: {e}"), ephemeral=True)

# /인증패널 명령어: 채널에 인증 패널 발행
@tree.command(name="인증패널", description="인증 패널(임베드 + 버튼)을 발행합니다. (서버 관리자 권한 필요)")
@app_commands.describe(channel="인증 패널을 발행할 텍스트 채널")
async def auth_panel(interaction: discord.Interaction, channel: discord.TextChannel):
    # 관리자 또는 소유자만 사용 가능
    if interaction.user.id != OWNER_ID and (not interaction.guild or not interaction.user.guild_permissions.administrator):
        return await interaction.response.send_message("권한이 없습니다. 서버 관리자만 사용할 수 있습니다.", ephemeral=True)

    # 임베드 생성
    embed = embeda("info", "인증하기", "아래 버튼을 눌러 인증을 진행하세요. 버튼 클릭 시 자동으로 역할이 부여됩니다.")
    view = DirectAuthView(role_id=TARGET_ROLE_ID)
    try:
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"{channel.mention}에 인증 패널을 발행했습니다.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("봇에게 해당 채널에 메시지를 보낼 권한이 없습니다.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"패널 발행 중 오류: {e}", ephemeral=True)

# 봇 준비 이벤트
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user} ({bot.user.id})")

# 실행 (이미 메인에서 실행 중이면 중복 실행 금지)
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
