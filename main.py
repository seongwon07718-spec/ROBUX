from discord.ext import tasks
import discord
from datetime import datetime

# 실시간 업데이트할 메시지를 저장할 변수
status_message = None

class BotStateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

# 1. 10초마다 실행되는 자동 업데이트 루프
@tasks.loop(seconds=10)
async def update_bot_status_loop():
    global status_message
    if status_message:
        try:
            # 최신 상태로 임베드 생성
            new_embed = await create_bot_state_embed()
            # 메시지 수정 (새로고침 버튼 없이 내용만 변경)
            await status_message.edit(embed=new_embed)
        except Exception as e:
            print(f"루프 업데이트 오류: {e}")

# 2. 명령어 실행 시 루프 시작
@bot.tree.command(name="bot_state", description="모든 유저에게 실시간 봇 상태를 생중계합니다.")
async def bot_state(interaction: discord.Interaction):
    global status_message
    
    # 즉시 응답 (모두가 볼 수 있게 ephemeral=False)
    await interaction.response.defer(ephemeral=False)
    
    embed = await create_bot_state_embed()
    # 첫 메시지 전송 및 변수에 저장
    status_message = await interaction.followup.send(embed=embed)
    
    # 루프가 실행 중이 아니라면 시작
    if not update_bot_status_loop.is_running():
        update_bot_status_loop.start()

# 3. 임베드 생성 함수 (기존과 동일)
async def create_bot_state_embed():
    embed = discord.Embed(
        title="📡 실시간 봇 생중계 현황",
        description="이 메시지는 10초마다 자동으로 갱신됩니다.",
        color=0x00ff00 # 실시간 느낌을 위해 초록색
    )
    
    for category, bots in BOT_DATA.items():
        status_lines = []
        for bot in bots:
            is_online = await get_bot_status(bot["id"]) # 실시간 API 호출
            emoji = "🟢 **온라인**" if is_online else "🔴 **오프라인**"
            status_lines.append(f"**{bot['name']}**: {emoji}")
        
        embed.add_field(name=f"📌 {category.upper()}", value="\n".join(status_lines), inline=False)
    
    embed.set_footer(text=f"최근 자동 갱신: {datetime.now().strftime('%H:%M:%S')}")
    return embed
