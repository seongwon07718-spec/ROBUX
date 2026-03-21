import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, uvicorn, asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from threading import Thread

# ================= [ 1. 필수 설정 정보 ] =================
# 본인의 정보로 반드시 교체하세요.
TOKEN = "YOUR_BOT_TOKEN"
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
# 디스코드 포털 OAuth2 -> Redirects에 등록한 주소와 100% 일치 필수
REDIRECT_URI = "https://restore.v0ut.com" 

app = FastAPI()
intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        # 1. 데이터베이스 초기화
        conn = sqlite3.connect('restore_user.db')
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
        # 2. 슬래시 명령어 동기화
        await self.tree.sync()
        print(f"로그인 완료: {self.user}")

bot = RecoveryBot()

# ================= [ 2. FastAPI: 블랙 & 화이트 웹 인증 디자인 ] =================

@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code = request.query_params.get("code")
    # 주소창의 ?server_id= 값을 우선적으로 가져옴 (요청하신 기능)
    server_id = request.query_params.get("server_id") or request.query_params.get("state")
    
    if not code:
        # 로그인 전 혹은 오류 시 기본 화면 (미니멀 디자인)
        return """
        <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>body{background:#000;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}
        .card{border:1px solid #333;padding:40px;border-radius:12px;text-align:center;max-width:350px;}
        h1{font-size:20px;letter-spacing:2px;}p{color:#666;font-size:13px;}</style></head>
        <body><div class="card"><h1>SESSION EXPIRED</h1><div style="width:20px;height:1px;background:#fff;margin:15px auto;"></div><p>다시 인증을 시도해주세요.</p></div></body></html>
        """

    async with aiohttp.ClientSession() as session:
        # 1. 코드를 Access Token으로 교환
        payload = {
            'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI
        }
        async with session.post('https://discord.com/api/v10/oauth2/token', data=payload) as r:
            token_data = await r.json()
            access_token = token_data.get('access_token')
            
            if access_token:
                # 2. 토큰으로 유저 고유 ID 확인
                async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as r2:
                    user_info = await r2.json()
                    
                    # 3. DB에 유저 정보 저장
                    conn = sqlite3.connect('restore_user.db')
                    cur = conn.cursor()
                    cur.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_info['id'], server_id, access_token))
                    conn.commit()
                    conn.close()
                
                # 인증 성공 화면: 보여주신 이미지 기반 블랙 & 화이트 레이아웃
                return f"""
                <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ background-color: #000; color: #fff; font-family: -apple-system, system-ui, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                    .container {{ text-align: center; border: 1px solid #222; padding: 50px; border-radius: 15px; background: #080808; animation: fadeIn 0.6s ease; max-width: 320px; }}
                    .icon {{ width: 60px; height: 60px; border: 1.5px solid #fff; border-radius: 50%; margin: 0 auto 30px; display: flex; justify-content: center; align-items: center; font-size: 28px; font-weight: bold; }}
                    h1 {{ font-size: 24px; font-weight: 600; letter-spacing: 3px; margin: 10px 0; }}
                    .divider {{ width: 30px; height: 1px; background: #fff; margin: 25px auto; opacity: 0.7; }}
                    .info {{ color: #666; font-size: 13px; margin-top: 20px; }}
                    @keyframes fadeIn {{ from{{opacity:0; transform:translateY(15px);}} to{{opacity:1; transform:translateY(0);}} }}
                </style></head>
                <body><div class="container"><div class="icon">V</div><h1>VERIFIED</h1><div class="divider"></div>
                <p style="font-size:14px; color:#aaa;">SERVER ID: {server_id}</p>
                <p class="info">인증이 성공적으로 완료되었습니다.<br>이 창을 닫으셔도 좋습니다.</p></div></body></html>
                """
    return "인증 실패"

# ================= [ 3. Discord: 명령어 & 컨테이너 ] =================

@bot.tree.command(name="인증하기", description="복구 인증 메뉴를 출력합니다 (공개 메시지).")
async def authenticate(it: discord.Interaction):
    view = ui.View()
    # 요청하신 `?server_id=` 파라미터를 유지하기 위한 URL 구조
    auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds.join"
        f"&state={it.guild_id}" # 보안용 state에도 서버ID 포함
        f"&server_id={it.guild_id}" # 주소창 유지용 파라미터
    )
    
    # [수정] TypeError 방지를 위해 .add_item() 괄호 호출 사용
    auth_btn = ui.Button(label="SECURITY VERIFY", url=auth_url, style=discord.ButtonStyle.link)
    view.add_item(auth_btn)

    embed = discord.Embed(title="RESTORE SYSTEM", description="서버 보안 및 자동 복구 인증을 시작합니다.", color=0x000000)
    embed.set_footer(text=f"Verified by v0ut.com")
    
    # ephemeral=False 로 설정하여 모든 유저가 볼 수 있게 함
    await it.response.send_message(embed=embed, view=view, ephemeral=False)

@bot.tree.command(name="유저복구", description="인증된 유저들을 현재 서버로 초대합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def restore(it: discord.Interaction):
    await it.response.send_message("🔄 복구 프로세스 가동...", ephemeral=True)
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id, access_token FROM users WHERE server_id = ?", (str(it.guild_id),))
    users = cur.fetchall()
    conn.close()

    if not users:
        return await it.followup.send("❌ 복구할 데이터가 존재하지 않습니다.")

    success, fail = 0, 0
    async with aiohttp.ClientSession() as session:
        for u_id, token in users:
            url = f"https://discord.com/api/v10/guilds/{it.guild_id}/members/{u_id}"
            async with session.put(url, headers={"Authorization": f"Bot {TOKEN}"}, json={"access_token": token}) as r:
                if r.status in [201, 204]: success += 1
                else: fail += 1
                await asyncio.sleep(0.5) # 레이트 리밋 방지
                
    await it.followup.send(f"✅ 복구 완료 (성공: {success} / 실패: {fail})")

# ================= [ 4. 실행 통합 ] =================

def run_fastapi():
    # Cloudflare 터널이 바라보는 8080 포트 실행
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    # 1. FastAPI 웹 서버를 별도 스레드에서 시작
    Thread(target=run_fastapi, daemon=True).start()
    # 2. 디스코드 봇 시작
    bot.run(TOKEN)
