import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, uvicorn
from fastapi import FastAPI, Request
from threading import Thread

# ================= [ 1. 설정 영역 ] =================
TOKEN = "YOUR_BOT_TOKEN"
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
# 주소 뒤에 /callback을 붙이지 않고 메인 도메인으로 설정 (디스코드 포털과 일치 필수)
REDIRECT_URI = "http://restore.v0ut.com" 

app = FastAPI()
intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        # 데이터베이스 초기화 (서버별 유저 구분 저장)
        conn = sqlite3.connect('recovery.db')
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, PRIMARY KEY(user_id, server_id))")
        conn.commit()
        conn.close()
        await self.tree.sync()

bot = RecoveryBot()

# ================= [ 2. FastAPI: ?code=...&state=... 처리 ] =================

@app.get("/")
async def oauth_main(request: Request):
    # 디스코드 인증 후 주소창에 붙는 파라미터를 가져옵니다.
    code = request.query_params.get("code")
    # 우리가 state에 넣어 보낸 서버 ID가 여기로 들어옵니다.
    server_id = request.query_params.get("state") 
    
    if not code:
        return {"status": "error", "message": "인증 코드가 누락되었습니다."}
        
    async with aiohttp.ClientSession() as session:
        # 토큰 교환 요청
        payload = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        }
        async with session.post('https://discord.com/api/v10/oauth2/token', data=payload) as r:
            token_data = await r.json()
            access_token = token_data.get('access_token')
            
            if not access_token:
                return {"status": "error", "message": "토큰 발급에 실패했습니다."}

            # 유저 정보 확인
            headers = {'Authorization': f'Bearer {access_token}'}
            async with session.get('https://discord.com/api/v10/users/@me', headers=headers) as r2:
                user_info = await r2.json()
                user_id = user_info.get('id')
                
                # DB 저장 (어느 서버에서 인증했는지 server_id 기록)
                conn = sqlite3.connect('recovery.db')
                cur = conn.cursor()
                cur.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_id, server_id, access_token))
                conn.commit()
                conn.close()
                
    return {"status": "success", "message": f"서버(ID: {server_id}) 인증이 완료되었습니다!"}

# ================= [ 3. Discord: 컨테이너 명령어 ] =================

@bot.tree.command(name="인증하기", description="복구 인증 컨테이너를 출력합니다.")
async def authenticate(it: discord.Interaction):
    # [오류 해결] 모든 add_item은 반드시 괄호() 형식을 사용해야 합니다.
    res_con = ui.Container()
    res_con.accent_color = 0xffffff # 화이트 테마
    
    res_con.add_item(ui.TextDisplay("## 🛡️ 멤버 보안 및 복구 인증"))
    res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    res_con.add_item(ui.TextDisplay(
        "본 서버는 유저 보호를 위해 **자동 복구 시스템**을 운영 중입니다.\n"
        "아래 버튼을 눌러 승인하면 서버 이동 시 자동으로 복구됩니다."
    ))
    
    # URL 구성 (state 파라미터에 현재 서버 ID를 담습니다)
    auth_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={it.guild_id}"
    
    # 버튼 추가
    btn = ui.Button(label="지금 보안 인증하기", url=auth_url, style=discord.ButtonStyle.link)
    res_con.add_item(ui.ActionRow(btn))

    # [오류 해결] LayoutView().add_item(res_con) 괄호 사용
    await it.response.send_message(view=ui.LayoutView().add_item(res_con), ephemeral=True)

@bot.tree.command(name="유저복구", description="현재 서버에 인증했던 유저들을 모두 불러옵니다.")
@app_commands.checks.has_permissions(administrator=True)
async def restore(it: discord.Interaction):
    conn = sqlite3.connect('recovery.db')
    cur = conn.cursor()
    # 현재 서버 ID와 일치하는 유저만 조회
    cur.execute("SELECT user_id, access_token FROM users WHERE server_id = ?", (str(it.guild_id),))
    all_users = cur.fetchall()
    conn.close()

    if not all_users:
        return await it.response.send_message("❌ 복구할 유저 데이터가 없습니다.", ephemeral=True)

    await it.response.send_message(f"🔄 총 {len(all_users)}명의 복구를 시작합니다...", ephemeral=True)
    
    success, fail = 0, 0
    async with aiohttp.ClientSession() as session:
        for u_id, token in all_users:
            url = f"https://discord.com/api/v10/guilds/{it.guild_id}/members/{u_id}"
            headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
            async with session.put(url, headers=headers, json={"access_token": token}) as resp:
                if resp.status in [201, 204]: success += 1
                else: fail += 1
                
    await it.followup.send(f"✅ 복구 완료! (성공: {success} / 실패: {fail})")

# ================= [ 4. 실행부 ] =================

def run_fastapi():
    # 8080 포트 실행 (클라우드플레어 설정과 일치 필수)
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    api_thread = Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    bot.run(TOKEN)
