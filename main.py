import discord
from discord import app_commands
from discord.ext import commands
import random
import os

# 전역 변수 설정 (이미지 URL 및 파일 존재 확인용)
IMG_BANNER_URL = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"

# 1. 결과보기 버튼 뷰
class ResultShowView(discord.ui.View):
    def __init__(self, result_side, is_win):
        super().__init__(timeout=None)
        self.result_side = result_side
        self.is_win = is_win

    @discord.ui.button(label="결과보기", style=discord.ButtonStyle.success)
    async def show_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        filename = f"final_fix_{self.result_side}.gif"
        
        if not os.path.exists(filename):
            await interaction.response.send_message("❌ GIF 파일을 찾을 수 없습니다.", ephemeral=True)
            return

        file = discord.File(filename, filename=filename)
        res_embed = discord.Embed(
            title="🎊 코인플립 결과",
            description=f"결과는 **{self.result_side}**입니다!\n\n" + 
                        (f"✅ **승리! 축하드립니다!**" if self.is_win else "❌ **아쉽게 패배하셨습니다.**"),
            color=0x2ecc71 if self.is_win else 0xe74c3c
        )
        res_embed.set_image(url=f"attachment://{filename}")
        # 결과도 본인에게만 보이게 전송
        await interaction.response.send_message(embed=res_embed, file=file, ephemeral=True)

# 2. H/T 선택 버튼 뷰
class CoinChoiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def handle_choice(self, interaction: discord.Interaction, user_side: str):
        result_side = random.choice(["H", "T"])
        is_win = (user_side == result_side)

        wait_embed = discord.Embed(
            title="📣 베팅 접수 완료",
            description=f"{interaction.user.mention}님이 **{user_side}**에 베팅하셨습니다!",
            color=0x2ecc71
        )
        view = ResultShowView(result_side, is_win)
        # 이 단계부터는 본인에게만 보임
        await interaction.response.edit_message(embed=wait_embed, view=view)

    @discord.ui.button(label="앞면 (H)", style=discord.ButtonStyle.danger)
    async def head_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "H")

    @discord.ui.button(label="뒷면 (T)", style=discord.ButtonStyle.primary)
    async def tail_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "T")

# 3. 메인 명령어 (전체 공개 패널)
@bot.tree.command(name="베팅하기", description="코인플립 베팅 패널을 출력합니다.")
async def betting_command(interaction: discord.Interaction):
    start_embed = discord.Embed(
        title="BloxFlip - 베팅하기",
        description=(
            "**✅ 베팅 중 문제 발생 시 문의 부탁드려주세요**\n"
            "**✅ 베팅한 기록들은 DB에 저장됩니다**\n\n"
            "***[BloxFlip 이용약관](https://discord.com)***"
        ),
        color=0xffffff
    )
    start_embed.set_image(url=IMG_BANNER_URL)

    class StartView(discord.ui.View):
        @discord.ui.button(label="베팅 시작하기", style=discord.ButtonStyle.primary)
        async def start(self, interaction_start: discord.Interaction, button: discord.ui.Button):
            # 클릭한 사람에게만 보이는 새로운 메시지로 전환 (ephemeral=True)
            choice_view = CoinChoiceView()
            choice_embed = discord.Embed(title="🪙 선택", description="앞면 혹은 뒷면을 골라주세요.", color=0xffffff)
            choice_embed.set_image(url=IMG_BANNER_URL)
            await interaction_start.response.send_message(embed=choice_embed, view=choice_view, ephemeral=True)

    # 누구나 볼 수 있게 ephemeral=True를 제거함
    await interaction.response.send_message(embed=start_embed, view=StartView())
