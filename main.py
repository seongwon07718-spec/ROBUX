import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp
import sqlite3
import uvicorn
from fastapi import FastAPI
from threading import Thread
import uuid

# ================= [ 설정 영역 ] =================
TOKEN = "YOUR_BOT_TOKEN"
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
REDIRECT_URI = "http://v0ut.com/callback" # 클라우드플레어 도메인

app = FastAPI()
intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        # DB 초기화
        conn = sqlite3.connect('recovery.db')
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, access_token TEXT)")
        conn.commit()
        conn.close()
        await self.tree.sync()

bot = RecoveryBot()

# ================= [ FastAPI: 인증 로직 ] =================
@app.get("/callback")
async def oauth_callback(code: str):
    async with aiohttp.ClientSession() as session:
        # 1. 코드를 토큰으로 교환
        data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        async with session.post('https://discord.com/api/v10/oauth2/token', data=data, headers=headers) as r:
            token_json = await r.json()
            access_token = token_json.get('access_token')
            
            # 2. 유저 정보 가져오기
            auth_headers = {'Authorization': f'Bearer {access_token}'}
            async with session.get('https://discord.com/api/v10/users/@me', headers=auth_headers) as r2:
                user_info = await r2.json()
                user_id = user_info.get('id')
                
                # 3. DB 저장
                conn = sqlite3.connect('recovery.db')
                cur = conn.cursor()
                cur.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (user_id, access_token))
                conn.commit()
                conn.close()
                
    return {"status": "success", "message": "인증 완료! 이제 창을 닫으셔도 됩니다."}

# ================= [ Discord: 명령어 ] =================

@bot.tree.command(name="인증하기", description="복구 인증 컨테이너를 호출합니다.")
async def authenticate(it: discord.Interaction):
    # 컨테이너 UI 구성
    res_con = ui.Container()
    res_con.accent_color = 0xffffff # 화이트 테마
    
    res_con.add_item(ui.TextDisplay("## 🛡️ 서버 보안 및 복구 인증"))
    res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    res_con.add_item(ui.TextDisplay(
        "본 서버는 유저 보호를 위해 **자동 복구 시스템**을 운영 중입니다.\n"
        "아래 인증을 완료하면 서버 이동 시 자동으로 초대됩니다."
    ))
    
    # OAuth2 URL 생성
    auth_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join"
    
    # 버튼 추가 (Link 스타일)
    auth_btn = ui.Button(label="안전 인증 시작하기", url=auth_url, style=discord.ButtonStyle.link)
    action_row = ui.ActionRow(auth_btn)
    res_con.add_item(action_row)

    # LayoutView로 전송 (사진에 나왔던 문법 오류 수정됨)
    view = ui.LayoutView().add_item(res_con)
    await it.response.send_message(view=view, ephemeral=True)

@bot.tree.command(name="유저복구", description="인증된 모든 유저를 현재 서버로 불러옵니다.")
@app_commands.checks.has_permissions(administrator=True)
async def restore(it: discord.Interaction):
    # 진행 상황 알림 컨테이너
    res_con = ui.Container()
    res_con.accent_color = 0x00ff00 # 초록색
    res_con.add_item(ui.TextDisplay("## 🔄 복구 프로세스 가동"))
    res_con.add_item(ui.TextDisplay("> 유저 데이터를 불러와 서버 가입을 시도합니다..."))
    
    await it.response.send_message(view=ui.LayoutView().add_item(res_con), ephemeral=True)
    
    conn = sqlite3.connect('recovery.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id, access_token FROM users")
    all_users = cur.fetchall()
    conn.close()

    success, fail = 0, 0
    async with aiohttp.ClientSession() as session:
        for u_id, token in all_users:
            url = f"https://discord.com/api/v10/guilds/{it.guild_id}/members/{u_id}"
            headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
            payload = {"access_token": token}
            
            async with session.put(url, headers=headers, json=payload) as resp:
                if resp.status in [201, 204]: success += 1
                else: fail += 1
                
    await it.followup.send(f"✅ 복구 완료! (성공: {success} / 실패: {fail})")

# ================= [ 실행부 ] =================

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080) # 포트 번호 확인

if __name__ == "__main__":
    # FastAPI를 별도 스레드에서 실행
    api_thread = Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    
    # 봇 실행
    bot.run(TOKEN)
