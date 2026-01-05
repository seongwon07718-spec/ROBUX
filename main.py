import discord
from discord import app_commands
from discord.ext import commands
import random
import os

# 사진 속 main.py의 구조를 반영한 Slash Command 방식
class BettingSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="베팅하기", description="코인플립 베팅을 시작합니다.")
    async def game(self, interaction: discord.Interaction):
        # 1단계: 베팅 시작 임베드 (사진의 BloxFlip - 베팅하기 스타일 반영)
        embed = discord.Embed(
            title="BloxFlip - 베팅하기",
            description="**코인플립 베팅을 진행하시겠습니까?**\n\n베팅한 기록은 DB에 저장됩니다.",
            color=0xffffff
        )
        # 사진에 있던 이용약관 링크 등 필요한 정보 추가 가능
        
        view = discord.ui.View()
        btn_start = discord.ui.Button(label="베팅 시작하기", style=discord.ButtonStyle.primary)

        async def start_callback(interaction_start):
            # 2단계: H / T 선택 버튼 생성
            embed_choice = discord.Embed(
                title="🪙 앞면(H) vs 뒷면(T)",
                description="원하시는 면을 골라주세요!",
                color=0xFFCC00
            )
            view_choice = discord.ui.View()
            btn_h = discord.ui.Button(label="앞면 (H)", style=discord.ButtonStyle.danger)
            btn_t = discord.ui.Button(label="뒷면 (T)", style=discord.ButtonStyle.primary)

            async def flip_callback(interaction_choice, user_side):
                # 결과 미리 결정
                result_side = random.choice(["H", "T"])
                is_win = (user_side == result_side)

                # 3단계: 베팅 채널 알림 (임베드 및 결과보기 버튼)
                embed_wait = discord.Embed(
                    title="📣 베팅 완료!",
                    description=f"{interaction_choice.user.mention}님이 **{user_side}**에 베팅했습니다!",
                    color=0x2ecc71
                )
                view_wait = discord.ui.View()
                btn_result = discord.ui.Button(label="결과보기", style=discord.ButtonStyle.success)

                async def result_callback(interaction_res):
                    # 사진에 있는 이미 생성된 파일명 사용
                    filename = f"final_fix_{result_side}.gif"
                    
                    if not os.path.exists(filename):
                        await interaction_res.response.send_message(f"❌ 파일을 찾을 수 없습니다: {filename}", ephemeral=True)
                        return

                    # 4단계: 최종 결과 출력 (GIF 첨부)
                    file = discord.File(filename, filename=filename)
                    final_embed = discord.Embed(
                        title="🎊 결과 발표!",
                        description=f"결과는 **{result_side}**입니다!\n\n" + 
                                    (f"✅ **승리! 베팅에 성공하셨습니다.**" if is_win else "❌ **패배! 다음 기회에...**"),
                        color=0x2ecc71 if is_win else 0xe74c3c
                    )
                    final_embed.set_image(url=f"attachment://{filename}")
                    
                    # 기존 메시지를 수정하거나 새로 보내기 (여기서는 새로운 메시지로 결과 전송)
                    await interaction_res.response.send_message(embed=final_embed, file=file)

                btn_result.callback = result_callback
                view_wait.add_item(btn_result)
                await interaction_choice.response.edit_message(embed=embed_wait, view=view_wait)

            btn_h.callback = lambda i: flip_callback(i, "H")
            btn_t.callback = lambda i: flip_callback(i, "T")
            view_choice.add_item(btn_h)
            view_choice.add_item(btn_t)
            await interaction_start.response.edit_message(embed=embed_choice, view=view_choice)

        btn_start.callback = start_callback
        view.add_item(btn_start)
        await interaction.response.send_message(embed=embed, view=view)

# Bot 설정 부분에 Cog 추가 필요 (bot.add_cog)
