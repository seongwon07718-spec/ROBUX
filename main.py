import discord
from discord.ext import commands
import json
import aiohttp
import time
import pymem
import pymem.process
from datetime import datetime, timedelta
from database import save_verified_user

# --- 설정 및 파일 경로 ---
TOKEN = 'YOUR_BOT_TOKEN'
ADMIN_WEBHOOK_URL = "YOUR_WEBHOOK_URL"
VERIFIED_USERS_FILE = "verified_users.json"
RECHARGE_LOG_FILE = "recharge_logs.json"

# --- 메모리 주소 설정 (MM2 전용) ---
# 이 주소들은 예시이며, Cheat Engine을 통해 실제 'AutoAccept' 플래그 주소를 찾아야 합니다.
ROBLOX_PROCESS = "RobloxPlayerBeta.exe"
MEM_AUTO_ACCEPT_OFFSET = 0x3A2B1C0  # 거래 자동 수락 플래그 주소 (예시)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
start_time = time.time()

# --- 메모리 조작 함수 ---
def toggle_roblox_auto_accept(state: bool):
    """로블록스 프로세스 메모리에 자동 수락 상태 기록"""
    try:
        pm = pymem.Pymem(ROBLOX_PROCESS)
        client = pymem.process.module_from_name(pm.process_handle, ROBLOX_PROCESS).lpBaseOfDll
        target_addr = client + MEM_AUTO_ACCEPT_OFFSET
        
        # 1: 켜짐(True), 0: 꺼짐(False)
        val = 1 if state else 0
        pm.write_int(target_addr, val)
        return True
    except Exception as e:
        print(f"❌ 메모리 조작 실패: {e}")
        return False

# --- 유틸리티 함수 ---
def get_verified_user_by_roblox_id(roblox_id):
    try:
        with open(VERIFIED_USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
            return users.get(str(roblox_id))
    except: return None

# --- 거래 완료 처리 (인게임 봇 -> 디스코드 API 수신부 가정) ---
async def process_trade_success(roblox_id, roblox_name, items):
    user_data = get_verified_user_by_roblox_id(roblox_id)
    
    if user_data:
        # DB 저장 및 알림
        discord_id = user_data['discord_id']
        await send_recharge_webhook(discord_id, roblox_name, items)
        # 로그 파일 저장 로직 추가 가능
    else:
        print(f"⚠️ 비인증 유저({roblox_name})와 거래 완료. 기록되지 않음.")

# --- 관리자 웹훅 (Discohook 스타일) ---
async def send_recharge_webhook(discord_id, roblox_name, items):
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(ADMIN_WEBHOOK_URL, session=session)
        embed = discord.Embed(title="💰 MM2 아이템 자동 수령 완료", color=0x00ff00)
        embed.add_field(name="기부/충전자", value=f"<@{discord_id}>", inline=True)
        embed.add_field(name="로블록스 계정", value=roblox_name, inline=True)
        embed.add_field(name="수령 아이템", value=f"```\n{items}\n```", inline=False)
        embed.set_footer(text="Der System Auto-Trade")
        await webhook.send(embed=embed)

# --- 봇 상태 확인 명령어 ---
@bot.tree.command(name="bot_info")
async def bot_info(interaction: discord.Interaction):
    uptime = str(timedelta(seconds=int(time.time() - start_time)))
    ping = round(bot.latency * 1000)
    
    embed = discord.Embed(title="🤖 봇 시스템 상태", color=discord.Color.blue())
    embed.add_field(name="가동 시간", value=f"`{uptime}`", inline=True)
    embed.add_field(name="지연 시간", value=f"`{ping}ms`", inline=True)
    
    # 메모리 자동화 상태 확인 (프로세스 체크)
    try:
        pymem.Pymem(ROBLOX_PROCESS)
        mem_status = "🟢 로블록스 연결됨 (자동화 활성)"
    except:
        mem_status = "🔴 로블록스 미실행"
    
    embed.add_field(name="자동화 엔진", value=mem_status, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    await bot.tree.sync()
    # 봇이 켜지면 로블록스 메모리 자동 수락 On
    toggle_roblox_auto_accept(True)
    print(f"✅ {bot.user.name} 가동 및 MM2 메모리 엔진 로드 완료")

if __name__ == "__main__":
    bot.run(TOKEN)
