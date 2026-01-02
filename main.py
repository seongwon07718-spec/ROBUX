import discord
from discord import app_commands
import psutil
import platform
import time
import datetime

@bot.tree.command(name="bot_info", description="봇의 현재 상태 및 서버 자원 사용량을 확인합니다.")
async def bot_info(interaction: discord.Interaction):
    # 1. 시스템 정보 가져오기
    cpu_usage = psutil.cpu_percent(interval=1) # CPU 점유율
    memory_info = psutil.virtual_memory() # 메모리 정보
    
    # 2. 봇 상태 정보
    ping = round(bot.latency * 1000) # 봇 지연 시간 (ms)
    uptime = str(datetime.timedelta(seconds=int(time.time() - start_time))) # 가동 시간
    
    # 3. 임베드 생성
    embed = discord.Embed(title="🤖 봇 상태 리포트", color=discord.Color.blue())
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    # 서버 자원 상태 필드
    embed.add_field(
        name="🖥️ 서버 리소스", 
        value=f"**CPU 사용량:** {cpu_usage}%\n"
              f"**메모리 사용량:** {memory_info.percent}%\n"
              f"**사용 가능한 메모리:** {round(memory_info.available / (1024**3), 2)} GB", 
        inline=False
    )
    
    # 봇 가동 상태 필드
    embed.add_field(
        name="⚡ 봇 상태", 
        value=f"**지연 시간 (Ping):** {ping}ms\n"
              f"**가동 시간 (Uptime):** {uptime}\n"
              f"**OS 환경:** {platform.system()} {platform.release()}", 
        inline=False
    )
    
    embed.set_footer(text=f"요청 시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await interaction.response.send_message(embed=embed)

# --- 가동 시간 계산을 위해 파일 상단(bot 정의 아래)에 추가 ---
# start_time = time.time() 
