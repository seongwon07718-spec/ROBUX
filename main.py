import discord
import asyncio
import random
import string
import aiohttp
import re
from discord.ext import commands

# --- 설정 (수정 필요) ---
CATEGORY_ID = 1455820042368450580
ADMIN_ROLE_ID = 1455824154283606195
VERIFY_ROLE_ID = 1456531768109961287

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"커맨드 동기화 완료: {self.user.name}")

bot = MyBot()

# --- Roblox 닉네임 유효성 및 존재 검증 함수 ---
async def check_roblox_user(username: str):
    if not re.match(r"^[A-Za-z0-9_]{3,}$", username):
        return None, "형식 불일치 (영어/숫자/언더바 3자 이상)"
    url = "https://users.roblox.com/v1/usernames/users"
    data = {"usernames": [username], "excludeBannedUsers": True}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as resp:
            if resp.status == 200:
                res_json = await resp.json()
                if res_json.get("data"):
                    return res_json["data"][0]["name"], "존재함"
                else:
                    return None, "존재하지 않는 닉네임"
            else:
                return None, "API 오류"

# --- VerifyStartView: 최초 공개 패널 - 인증 시작용 버튼 ---
class VerifyStartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="로블록스 인증하기", style=discord.ButtonStyle.gray,
                       emoji=discord.PartialEmoji(name="verified", id=1455996645337468928))
    async def start_verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="로블록스 인증 절차 시작",
            description="아래에 닉네임을 입력하고 진행 버튼을 눌러주세요.",
            color=0xffffff
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1456321236643741728/IMG_0751.png")
        
        # ephemeral 메시지 새로 보내기 (본인에게만 보임)
        await interaction.response.send_message(embed=embed, view=VerifyStepView(), ephemeral=True)

# --- NicknameModal: 닉네임 입력 모달 ---
class NicknameModal(discord.ui.Modal, title="로블록스 닉네임 입력"):
    nickname = discord.ui.TextInput(label="로블록스 닉네임", min_length=3)

    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view

    async def on_submit(self, interaction: discord.Interaction):
        username = self.nickname.value.strip()
        name, status = await check_roblox_user(username)
        if name is None:
            self.original_view.roblox_user = None
            status_msg = f"❌ {status}"
            self.original_view.confirm_btn.disabled = True
        else:
            self.original_view.roblox_user = {"name": name}
            status_msg = f"✅ {name} (닉네임 확인됨)"
            self.original_view.confirm_btn.disabled = False

        embed = discord.Embed(color=0xffffff)
        embed.add_field(name="로블록스 닉네임 상태", value=status_msg)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1456321236643741728/IMG_0751.png")

        # 메시지 수정 (본인에게만 보이는 ephemeral 메시지)
        await interaction.response.edit_message(embed=embed, view=self.original_view)

# --- VerifyStepView: 닉네임 입력 후 인증 진행 뷰 ---
class VerifyStepView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.roblox_user = None

    @discord.ui.button(label="닉네임 수정하기", style=discord.ButtonStyle.gray)
    async def edit_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NicknameModal(self))

    @discord.ui.button(label="진행하기", style=discord.ButtonStyle.green, disabled=True)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        verify_key = "FLIP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        embed = discord.Embed(
            title="최종 단계 - 프로필 확인",
            description=(
                f"로블록스 계정: **{self.roblox_user['name']}**\n"
                f"인증 문구: `{verify_key}`\n\n"
                "┗ 로블록스 프로필 소개란에 위 문구를 반드시 작성해주세요."
            ),
            color=discord.Color.gold()
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1456321236643741728/IMG_0751.png")
        await interaction.response.edit_message(embed=embed, view=VerifyCheckView(self.roblox_user['name'], verify_key))

# --- VerifyCheckView: 최종 인증 확인 및 역할 부여 뷰 ---
class VerifyCheckView(discord.ui.View):
    def __init__(self, roblox_name, verify_key):
        super().__init__(timeout=None)
        self.roblox_name = roblox_name
        self.verify_key = verify_key

    @discord.ui.button(label="인증 완료하기", style=discord.ButtonStyle.gray)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        url = f"https://users.roblox.com/v1/users/search?keyword={self.roblox_name}&limit=1"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("data"):
                        user = data["data"][0]
                        user_id = user["id"]
                        # 프로필 소개 확인 API
                        detail_url = f"https://users.roblox.com/v1/users/{user_id}"
                        async with session.get(detail_url) as detail_resp:
                            if detail_resp.status == 200:
                                detail_data = await detail_resp.json()
                                description = detail_data.get("description", "")
                                if self.verify_key in description:
                                    role = interaction.guild.get_role(VERIFY_ROLE_ID)
                                    await interaction.user.add_roles(role)
                                    embed = discord.Embed(
                                        title="인증 완료",
                                        description=f"**{self.roblox_name}님의 인증이 완료되었습니다.**",
                                        color=discord.Color.green()
                                    )
                                    await interaction.response.edit_message(embed=embed, view=None)
                                    return
                                else:
                                    await interaction.response.send_message(
                                        "프로필 소개에 인증 문구가 없습니다. 정확히 입력했는지 확인하세요.", ephemeral=True
                                    )
                                    return
                await interaction.response.send_message(
                    "로블록스 API 오류 또는 유저를 찾을 수 없습니다.", ephemeral=True
                )

# --- /verify 명령어 ---
@bot.tree.command(name="verify", description="로블록스 인증하기 시작")
async def verify_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("**인증 안내 메시지**", ephemeral=False)

    embed = discord.Embed(
        title="로블록스 인증 안내",
        description=(
            "게임 이용을 위해 인증은 필수입니다.\n"
            "아래 인증하기 버튼을 눌러 절차를 시작하세요.\n\n"
            "[로블록스 이용약관](https://www.roblox.com/terms) | [디스코드 TOS](https://discord.com/terms)"
        ),
        color=0xffffff
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1456494848457572433/IMG_0753.png")

    await interaction.channel.send(embed=embed, view=VerifyStartView())

if __name__ == "__main__":
    bot.run('YOUR_BOT_TOKEN')
