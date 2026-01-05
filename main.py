import discord
from discord import app_commands
from discord.ext import commands
import random
import os

# 사진 속 구조를 반영한 Slash Command 정의
@bot.tree.command(name="베팅하기", description="코인플립 베팅을 진행합니다.")
@app_commands.checks.has_permissions(administrator=True) # 관리자 전용 설정(필요 시 제거)
async def game(interaction: discord.Interaction):
    # 1. 초기 베팅 시작 패널 (사진 속 BloxFlip - 베팅하기 스타일)
    embed = discord.Embed(
        title="BloxFlip - 베팅하기",
        description=(
            "**✅ 베팅 중 문제 발생 시 문의 부탁드려주세요**\n"
            "**✅ 베팅한 기록들은 DB에 저장됩니다**\n\n"
            "***[BloxFlip 이용약관](https://discord.com/channels/...)*** [BloxFlip 문의하기](https://discord.com/channels/...)"
        ),
        color=0xffffff
    )
    # 사진에서 사용 중인 하단 배너 이미지 URL 유지
    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
    embed.set_image(url=img_url)

    class BettingView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="베팅 시작하기", style=discord.ButtonStyle.primary)
        async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            # 2. H / T 선택 단계
            choice_embed = discord.Embed(
                title="🪙 코인플립 선택",
                description="앞면(H) 또는 뒷면(T) 중 하나를 선택해 주세요!",
                color=0xffffff
            )
            choice_embed.set_image(url=img_url)

            class ChoiceView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=None)

                async def process_bet(self, inter, user_side):
                    # 결과 결정 및 GIF 파일 매칭
                    result_side = random.choice(["H", "T"])
                    is_win = (user_side == result_side)
                    gif_filename = f"final_fix_{result_side}.gif"

                    # 3. 결과보기 대기 임베드
                    wait_embed = discord.Embed(
                        title="📣 베팅 접수 완료",
                        description=f"{inter.user.mention}님이 **{user_side}**에 베팅하셨습니다!",
                        color=0x2ecc71
                    )
                    
                    class ResultView(discord.ui.View):
                        @discord.ui.button(label="결과보기", style=discord.ButtonStyle.success)
                        async def result_button(self, inter_res: discord.Interaction, btn: discord.ui.Button):
                            if not os.path.exists(gif_filename):
                                await inter_res.response.send_message("❌ GIF 파일을 찾을 수 없습니다.", ephemeral=True)
                                return

                            # 4. 최종 결과 출력 (미리 생성된 GIF 첨부)
                            file = discord.File(gif_filename, filename=gif_filename)
                            result_embed = discord.Embed(
                                title="🎊 코인플립 결과",
                                description=f"결과는 **{result_side}**입니다!\n\n" + 
                                            (f"✅ **승리! 베팅 성공**" if is_win else "❌ **패배! 다음 기회에...**"),
                                color=0x2ecc71 if is_win else 0xe74c3c
                            )
                            result_embed.set_image(url=f"attachment://{gif_filename}")
                            await inter_res.response.send_message(embed=result_embed, file=file)

                    await inter.response.edit_message(embed=wait_embed, view=ResultView())

                @discord.ui.button(label="앞면 (H)", style=discord.ButtonStyle.danger)
                async def h_button(self, inter: discord.Interaction, button: discord.ui.Button):
                    await self.process_bet(inter, "H")

                @discord.ui.button(label="뒷면 (T)", style=discord.ButtonStyle.primary)
                async def t_button(self, inter: discord.Interaction, button: discord.ui.Button):
                    await self.process_bet(inter, "T")

            await interaction.response.edit_message(embed=choice_embed, view=ChoiceView())

    await interaction.response.send_message(embed=embed, view=BettingView(), ephemeral=True)
