from discord.ext import tasks
import discord
from datetime import datetime

# 자동 업데이트를 관리할 전역 변수
status_msg = None

# 1. 자동 업데이트 루프 (10초 주기)
@tasks.loop(seconds=10)
async def bot_status_auto_update():
    global status_msg
    if status_msg:
        try:
            # 실시간 상태 임베드 생성
            new_embed = await create_bot_state_embed()
            # 기존 메시지를 '수정'하여 실시간 상태 반영
            await status_msg.edit(embed=new_embed)
        except Exception as e:
            print(f"자동 업데이트 중 오류: {e}")
            bot_status_auto_update.stop() # 메시지 삭제 등의 경우 루프 중단

# 2. 명령어 정의 (모두에게 공개 버전)
@bot.tree.command(name="bot_state", description="봇들의 실시간 접속 상태를 채널에 생중계합니다.")
async def bot_state(interaction: discord.Interaction):
    global status_msg
    
    # [에러 방지] 이미 응답했는지 확인 후 defer 처리
    await interaction.response.defer(ephemeral=False) 
    
    embed = await create_bot_state_embed()
    
    # 첫 전송 시 followup.send를 사용하여 중복 응답 에러 차단
    status_msg = await interaction.followup.send(embed=embed)
    
    # 루프 시작 (이미 실행 중이면 무시)
    if not bot_status_auto_update.is_running():
        bot_status_auto_update.start()

# 3. 실시간 임베드 생성 함수 (중복 사용을 위해 분리)
async def create_bot_state_embed():
    embed = discord.Embed(
        title="📡 실시간 봇 가동 생중계",
        description="이 메시지는 **10초마다** 자동으로 업데이트됩니다.",
        color=0x2F3136 # 깔끔한 다크 모드 색상
    )
    
    # 사진 36번의 BOT_DATA 키값인 "머더", "입양"에 맞춰 순회
    for category, bots in BOT_DATA.items():
        status_lines = []
        for bot in bots:
            # 실시간 로블록스 API 체크
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
