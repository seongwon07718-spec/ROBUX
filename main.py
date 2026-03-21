import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp
import sqlite3
import uvicorn
from fastapi import FastAPI, Request
from threading import Thread
import asyncio

# ================= [ 1. 필수 설정 정보 ] =================
# 본인의 정보로 반드시 교체하세요.
TOKEN = "YOUR_BOT_TOKEN"
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
# 디스코드 포털 OAuth2 -> Redirects에 등록한 주소와 100% 일치해야 함
REDIRECT_URI = "http://restore.v0ut.com" 

app = FastAPI()
intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        # 데이터베이스 연결 및 테이블 생성
        conn = sqlite3.connect('recovery.db')
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT, 
                server_id TEXT, 
                access_token TEXT, 
                PRIMARY KEY(user_id, server_id)
            )
        """)
        conn.commit()
        conn.close()
        # 슬래시 명령어 동기화
        await self.tree.sync()
        print(f"봇 로그인 완료: {self.user}")

bot = RecoveryBot()

# ================= [ 2. FastAPI: 웹 인증 로직 ] =================

@app.get("/")
async def oauth_main(request: Request):
    # 디스코드에서 보내주는 인증 코드와 우리가 넣은 state(서버ID)를 가져옴
    code = request.query_params.get("code")
    server_id = request.query_params.get("state") 
    
    if not code:
        return {"status": "error", "message": "인증 코드가 없습니다. 다시 시도해주세요."}
        
    async with aiohttp.ClientSession() as session:
        # 1. 코드를 Access Token으로 교환
        payload = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        async with session.post('https://discord.com/api/v10/oauth2/token', data=payload, headers=headers) as r:
            token_data = await r.json()
            access_token = token_data.get('access_token')
            
            if not access_token:
                return {"status": "error", "message": "토큰 획득에 실패했습니다."}

            # 2. 획득한 토큰으로 유저 고유 ID 확인
            user_headers = {'Authorization': f'Bearer {access_token}'}
            async with session.get('https://discord.com/api/v10/users/@me', headers=user_headers) as r2:
                user_info = await r2.json()
                user_id = user_info.get('id')
                
                # 3. DB에 유저 정보 및 해당 서버 ID 저장
                conn = sqlite3.connect('recovery.db')
                cur = conn.cursor()
                cur.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_id, server_id, access_token))
                conn.commit()
                conn.close()
                
    # 유저 브라우저에 표시될 메시지
    return {
        "status": "success", 
        "message": f"서버(ID: {server_id}) 복구 인증이 완료되었습니다! 이제 창을 닫으셔도 됩니다."
    }

# ================= [ 3. Discord: 명령어 로직 ] =================

@bot.tree.command(name="인증하기", description="모든 유저가 볼 수 있는 복구 인증 메뉴를 출력합니다.")
async def authenticate(it: discord.Interaction):
    # 사진에서 발생한 TypeError 방지를 위해 .add_item() 괄호 호출 사용
    res_con = ui.Container()
    res_con.accent_color = 0xffffff # 화이트 테마
    
    res_con.add_item(ui.TextDisplay("## 🛡️ 서버 보안 및 자동 복구 인증"))
    res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    res_con.add_item(ui.TextDisplay(
        "본 서버는 유저 보호를 위해 **자동 복구 시스템**을 운영 중입니다.\n"
        "아래 버튼을 눌러 승인하면 서버 이동 상황에서 자동으로 초대됩니다."
    ))
    
    # state에 현재 서버 ID를 담아서 보냅니다. (FastAPI에서 server_id로 활용됨)
    auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds.join"
        f"&state={it.guild_id}"
    )
    
    auth_btn = ui.Button(label="안전 인증 시작하기", url=auth_url, style=discord.ButtonStyle.link)
    res_con.add_item(ui.Action_Row(auth_btn))

    # ephemeral=False 로 설정하여 다른 유저들도 메시지를 볼 수 있게 함
    view = ui.LayoutView().add_item(res_con)
    await it.response.send_message(view=view, ephemeral=False)

@bot.tree.command(name="유저복구", description="현재 서버에 인증했던 유저들을 모두 이 서버로 초대합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def restore(it: discord.Interaction):
    await it.response.send_message("🔄 복구 프로세스를 가동합니다. 잠시만 기다려주세요...", ephemeral=True)
    
    conn = sqlite3.connect('recovery.db')
    cur = conn.cursor()
    # 현재 서버 ID로 인증된 데이터만 조회
    cur.execute("SELECT user_id, access_token FROM users WHERE server_id = ?", (str(it.guild_id),))
    all_users = cur.fetchall()
    conn.close()

    if not all_users:
        return await it.followup.send("❌ 복구할 유저 데이터가 존재하지 않습니다.")

    success, fail = 0, 0
    async with aiohttp.ClientSession() as session:
        for u_id, token in all_users:
            url = f"https://discord.com/api/v10/guilds/{it.guild_id}/members/{u_id}"
            headers = {
                "Authorization": f"Bot {TOKEN}",
                "Content-Type": "application/json"
            }
            # guilds.join 스코프를 이용한 멤버 추가
            async with session.put(url, headers=headers, json={"access_token": token}) as resp:
                if resp.status in [201, 204]:
                    success += 1
                else:
                    fail += 1
                # 디스코드 레이트 리밋 방지를 위한 미세 대기
                await asyncio.sleep(0.5)
                
    await it.followup.send(f"✅ 복구 완료! (성공: {success}명 / 실패: {fail}명)")

# ================= [ 4. 전체 실행 엔진 ] =================

def run_fastapi():
    # Cloudflare 터널이 바라보는 8080 포트로 웹 서버 실행
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

if __name__ == "__main__":
    # 1. FastAPI 웹 서버를 별도 스레드에서 시작
    api_thread = Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    
    # 2. 디스코드 봇 시작
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"봇 실행 중 오류 발생: {e}")
