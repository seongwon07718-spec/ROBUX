from discord.ext import tasks
import discord
from datetime import datetime

# 자동 업데이트를 관리할 전역 변수
status_msg = None

# 1. 자동 업데이트 루프 정의 (반드시 @tasks.loop를 사용해야 합니다)
@tasks.loop(seconds=10)
async def bot_status_loop():
    global status_msg
    if status_msg:
        try:
            # 새로운 실시간 상태 임베드 생성
            new_embed = await create_bot_state_embed()
            # 기존 메시지 수정 (새 메시지를 보내지 않고 내용만 교체)
            await status_msg.edit(embed=new_embed)
        except Exception as e:
            print(f"자동 업데이트 중 오류 발생: {e}")
            bot_status_loop.stop()

# 2. 실시간 상태 임베드 생성 함수
async def create_bot_state_embed():
    embed = discord.Embed(
        title="📡 실시간 봇 가동 생중계",
        description="이 메시지는 **10초마다** 자동으로 업데이트됩니다.",
        color=0x2F3136
    )
    
    # 사진 36번의 BOT_DATA (머더, 입양) 구조에 맞춰 실시간 체크
    for category, bots in BOT_DATA.items():
        status_lines = []
        for bot in bots:
            # 로블록스 API를 통한 실시간 온라인 여부 확인
            is_online = await get_bot_status(bot["id"])
            emoji = "🟢 **온라인**" if is_online else "🔴 **오프라인**"
            status_lines.append(f"{bot['name']}: {emoji}")
        
        embed.add_field(
            name=f"🎮 {category}",
            value="\n".join(status_lines) if status_lines else "등록된 봇 없음",
            inline=False
        )
    
    embed.set_footer(text=f"마지막 자동 갱신: {datetime.now().strftime('%H:%M:%S')}")
    return embed

# 3. /bot_state 명령어 정의
@bot.tree.command(name="bot_state", description="채널에 실시간 봇 상태 메시지를 고정합니다.")
async def bot_state_cmd(interaction: discord.Interaction):
    global status_msg
    
    # [에러 방지] 사진 36번의 중복 응답 에러를 막기 위해 지연 응답 사용
    await interaction.response.defer(ephemeral=False) 
    
    # 초기 임베드 생성 및 전송
    embed = await create_bot_state_embed()
    status_msg = await interaction.followup.send(embed=embed)
    
    # [사진 37번 에러 해결] 함수가 아닌 loop 객체의 상태를 확인하여 시작
    if not bot_status_loop.is_running():
        bot_status_loop.start()
