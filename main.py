import discord
from discord.ext import commands
from fastapi import FastAPI, Request
import uvicorn
import json
import aiohttp
import threading
from datetime import datetime

# --- [1. 설정 및 에러 수정 섹션] ---
TOKEN = 'YOUR_BOT_TOKEN'
ADMIN_WEBHOOK_URL = "여기에_새로_만든_웹훅_주소" # 사진 2, 4의 401 에러 해결용
VERIFIED_USERS_FILE = "verified_users.json" # 사진 3, 5의 Pylance 에러 해결
RECHARGE_LOG_FILE = "recharge_logs.json"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
app = FastAPI()

# --- [2. 데이터베이스 처리] ---
def get_user_data(roblox_id):
    try:
        with open(VERIFIED_USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get(str(roblox_id))
    except Exception: return None

def log_transaction(action, discord_id, roblox_name, items):
    try:
        with open(RECHARGE_LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    except: logs = []
    
    logs.append({
        "action": action,
        "discord_id": discord_id,
        "roblox_name": roblox_name,
        "items": items,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    with open(RECHARGE_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=4, ensure_ascii=False)

# --- [3. API 엔드포인트: Bloxluck 방식] ---
@app.post("/trade/event")
async def handle_trade(request: Request):
    data = await request.json()
    action = data.get("action") # "deposit" 또는 "withdraw"
    r_id = data.get("roblox_id")
    r_name = data.get("roblox_name")
    items = data.get("items")

    user_info = get_user_data(r_id)
    if user_info:
        d_id = user_info['discord_id']
        log_transaction(action, d_id, r_name, items)
        
        # [사진 1] 에러 해결: discord.Webhook.from_url 사용
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(ADMIN_WEBHOOK_URL, session=session)
            embed = discord.Embed(title=f"📦 {action.upper()} 감지", color=0x00ff00)
            embed.add_field(name="유저", value=f"<@{d_id}>", inline=True)
            embed.add_field(name="아이템", value=f"```\n{items}\n```")
            await webhook.send(embed=embed)
            
    return {"status": "ok"}

# --- [4. 봇 및 서버 실행] ---
@bot.event
async def on_ready():
    print(f"✅ 시스템 가동: {bot.user}")

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    threading.Thread(target=run_api, daemon=True).start()
    bot.run(TOKEN)
