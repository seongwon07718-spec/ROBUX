import discord
import asyncio
import random
import string
import requests
from discord.ext import commands

# --- 설정 (기본 유지) ---
CATEGORY_ID = 1455820042368450580
ADMIN_ROLE_ID = 1455824154283606195
VERIFY_ROLE_ID = 1456531768109961287
ROBLOX_USER_SEARCH = "https://users.roblox.com/v1/users/search"
ROBLOX_USER_DETAIL = "https://users.roblox.com/v1/users/"

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"커맨드 동기화 완료: {self.user.name}")

bot = MyBot()

# ---- 1. 최초 인증 안내 + 인증하기 버튼 뷰 ----
class VerifyStartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="로블록스 인증하기", style=discord.ButtonStyle.gray,
                       emoji=discord.PartialEmoji(name="verified", id=1455996645337468928))
    async def start_verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 인증 시작 → 정보 수정 + 진행 버튼 뷰로 전환
        embed = discord.Embed(
            title="로블록스 - 인증 절차",
            description="아래 버튼으로 닉네임을 수정하고, 진행하기 버튼을 눌러 인증을 시작하세요.",
            color=0xffffff
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1456321236643741728/IMG_0751.png")
        await interaction.response.edit_message(embed=embed, view=VerifyStepView())

# ---- 2. 정보 수정 및 진행 버튼 뷰 ----
class VerifyStepView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.roblox_user = None

    @discord.ui.button(label="정보 수정하기", style=discord.ButtonStyle.gray,
                       emoji=discord.PartialEmoji(name="quick", id=1455996651218141286))
    async def edit_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NicknameModal(self))

    @discord.ui.button(label="진행하기", style=discord.ButtonStyle.green, disabled=True,
                       emoji=discord.PartialEmoji(name="ID", id=1455996414684303471))
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        verify_key = "FLIP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

        embed = discord.Embed(title="최종 단계 - 프로필 확인", color=discord.Color.gold())
        embed.description = (
            f"**로블록스 계정 = ** {self.roblox_user['name']}\n"
            f"**인증 문구 = ** `{verify_key}`\n\n"
            f"**┗   로블록스 프로필 소개 칸에 위 문구를 작성하고 아래 버튼을 눌러주세요**"
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1456321236643741728/IMG_0751.png")
        await interaction.response.edit_message(embed=embed,
                                                view=VerifyCheckView(self.roblox_user['name'], self.roblox_user['id'], verify_key))

# ---- 3. 닉네임 입력 모달 ----
class NicknameModal(discord.ui.Modal, title="로블록스 닉네임 입력"):
    nickname = discord.ui.TextInput(label="로블록스 닉네임", placeholder="닉네임을 입력하세요", min_length=2)

    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view

    async def on_submit(self, interaction: discord.Interaction):
        res = requests.get(ROBLOX_USER_SEARCH, params={"keyword": self.nickname.value, "limit": 1})
        data = res.json().get("data", [])

        if not data:
            self.original_view.roblox_user = None
            status_msg = "```❌ 존재하지 않는 이름입니다```"
            self.original_view.confirm_btn.disabled = True
        else:
            user = data[0]
            self.original_view.roblox_user = user
            status_msg = f"```{user['name']} (ID: {user['id']})```"
            self.original_view.confirm_btn.disabled = False

        embed = discord.Embed(color=0xffffff)
        embed.add_field(name="로블록스 닉네임", value=status_msg)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1456321236643741728/IMG_0751.png")

        await interaction.response.edit_message(embed=embed, view=self.original_view)

# ---- 4. 최종 인증 확인 뷰 ----
class VerifyCheckView(discord.ui.View):
    def __init__(self, roblox_name, roblox_id, target_key):
        super().__init__(timeout=None)
        self.roblox_name = roblox_name
        self.roblox_id = roblox_id
        self.target_key = target_key

    @discord.ui.button(label="로블록스 인증 완료하기", style=discord.ButtonStyle.gray,
                       emoji=discord.PartialEmoji(name="verified", id=1455996645337468928))
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        res = requests.get(f"{ROBLOX_USER_DETAIL}{self.roblox_id}")
        if res.status_code == 200:
            about_text = res.json().get("description", "")
            if self.target_key in about_text:
                role = interaction.guild.get_role(VERIFY_ROLE_ID)
                await interaction.user.add_roles(role)

                embed = discord.Embed(title="로블록스 - 인증완료",
                                      description=f"**{self.roblox_name}님의 인증이 완료되었습니다\n이제 다양한 서비스를 이용가능합니다**",
                                      color=0xffffff)
                embed.set_image(
                    url="https://cdn.discordapp.com/attachments/1455759161039261791/1456494848457572433/IMG_0753.png")
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"**인증에 실패하였습니다\n로블 닉네임의 '소개'란에 인증 코드를 정확히 기재해주세요\n┗   `{self.target_key}`**",
                    ephemeral=True)
        else:
            await interaction.response.send_message(
                "**로블록스 API 요청에 실패하였습니다\n봇이 실시간으로 점검중이오니 잠시 후 시도해주세요**", ephemeral=True)

# ---- 5. /verify 명령어 ----
@bot.tree.command(name="verify", description="로블록스 인증하기 패널")
async def verify_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("**DONE**", ephemeral=True)

    embed = discord.Embed(
        title="로블록스 - VERIFY BOT",
        description=(
            "**게임을 이용하실려면 인증은 필수입니다**\n"
            "**아래 버튼을 눌러 인증 절차를 시작하세요**\n\n"
            "**┗ 인증 후 게임 이용이 가능합니다**\n"
            "**┗ 상호작용 오류시 문의부탁드려요**\n\n"
            "**[로블록스 이용약관](https://www.roblox.com/terms)         [디스코드 TOS](https://discord.com/terms)**"
        ),
        color=0xffffff
    )
    embed.set_image(
        url="https://cdn.discordapp.com/attachments/1455759161039261791/1456494848457572433/IMG_0753.png"
    )
    # 최초 인증 안내 + 인증 시작 버튼 뷰 출력
    await interaction.channel.send(embed=embed, view=VerifyStartView())


if __name__ == "__main__":
    bot.run('토큰을_여기에_넣으세요')  # 실제 토큰으로 교체하세요.
