import discord
from discord import app_commands
from discord.ext import commands
import random
import os

# 사진에 나온 'game' 커맨드 위치에 이 내용을 덮어쓰세요.
@bot.tree.command(name="베팅하기", description="코인플립 베팅을 진행합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def game(interaction: discord.Interaction):
    # 사진 속 임베드 설정 그대로 반영
    embed = discord.Embed(
        title="BloxFlip - 베팅하기",
        description=(
            "**✅ 베팅 중 문제 발생 시 문의 부탁드려주세요**\n"
            "**✅ 베팅한 기록들은 DB에 저장됩니다**\n\n"
            "***[BloxFlip 이용약관](https://discord.com/channels/...)*** [BloxFlip 문의하기](https://discord.com/channels/...)"
        ),
        color=0xffffff
    )
    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
    embed.set_image(url=img_url)

    # 클래스를 별도로 정의하여 함수값(self) 오류 방지
    class CoinFlipView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="베팅 시작하기", style=discord.ButtonStyle.primary)
        async def start_betting(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
            # H/T 선택용 임베드
            choice_embed = discord.Embed(title="🪙 앞면(H) vs 뒷면(T)", description="원하는 면을 선택하세요.", color=0xffffff)
            choice_embed.set_image(url=img_url)
            
            # 선택 버튼 뷰 생성
            choice_view = CoinChoiceView()
            await btn_interaction.response.edit_message(embed=choice_embed, view=choice_view)

    class CoinChoiceView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        async def handle_choice(self, ch_interaction: discord.Interaction, user_side: str):
            result_side = random.choice(["H", "T"])
            is_win = (user_side == result_side)
            
            # 결과 대기 화면
            wait_embed = discord.Embed(
                title="📣 베팅 완료", 
                description=f"{ch_interaction.user.mention}님이 **{user_side}**를 선택했습니다!", 
                color=0x2ecc71
            )
            
            # 결과보기 버튼 뷰 생성 (결과값을 미리 넘겨줌)
            result_view = ResultShowView(result_side, is_win)
            await ch_interaction.response.edit_message(embed=wait_embed, view=result_view)

        @discord.ui.button(label="앞면 (H)", style=discord.ButtonStyle.danger)
        async def head_btn(self, inter: discord.Interaction, button: discord.ui.Button):
            await self.handle_choice(inter, "H")

        @discord.ui.button(label="뒷면 (T)", style=discord.ButtonStyle.primary)
        async def tail_btn(self, inter: discord.Interaction, button: discord.ui.Button):
            await self.handle_choice(inter, "T")

    class ResultShowView(discord.ui.View):
        def __init__(self, result_side, is_win):
            super().__init__(timeout=None)
            self.result_side = result_side
            self.is_win = is_win

        @discord.ui.button(label="결과보기", style=discord.ButtonStyle.success)
        async def show_result(self, res_interaction: discord.Interaction, button: discord.ui.Button):
            filename = f"final_fix_{self.result_side}.gif"
            
            if not os.path.exists(filename):
                await res_interaction.response.send_message("❌ GIF 파일이 경로에 없습니다!", ephemeral=True)
                return

            file = discord.File(filename, filename=filename)
            res_embed = discord.Embed(
                title="🎊 결과 발표",
                description=f"결과는 **{self.result_side}**입니다!\n" + ("✅ 승리!" if self.is_win else "❌ 패배..."),
                color=0x2ecc71 if self.is_win else 0xe74c3c
            )
            res_embed.set_image(url=f"attachment://{filename}")
            
            # 결과는 새로운 메시지로 전송 (ephemeral=True 설정 가능)
            await res_interaction.response.send_message(embed=res_embed, file=file)

    # 첫 실행 (사진처럼 ephemeral 처리 여부는 선택 가능)
    await interaction.response.send_message(embed=embed, view=CoinFlipView(), ephemeral=True)
