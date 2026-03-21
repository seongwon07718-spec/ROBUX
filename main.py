import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, uvicorn, asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from threading import Thread

# ================= [ 1. 설정 정보 ] =================
TOKEN = "YOUR_BOT_TOKEN"
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
# 디스코드 포털 OAuth2 -> Redirects에 등록한 주소와 100% 일치해야 함
REDIRECT_URI = "https://restore.v0ut.com" 

app = FastAPI()
intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
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
        await self.tree.sync()

bot = RecoveryBot()

# ================= [ 2. 블랙 & 화이트 웹 디자인 ] =================

@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code = request.query_params.get("code")
    # 주소창의 ?server_id= 값을 우선적으로 가져옴
    server_id = request.query_params.get("server_id") or request.query_params.get("state")
    
    if not code:
        return """
        <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>body{background:#000;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}
        .card{border:1px solid #333;padding:40px;border-radius:8px;text-align:center;}</style></head>
        <body><div class="card"><h1>INVALID ACCESS</h1><p>인증 코드가 누락되었습니다.</p></div></body></html>
        """

    async with aiohttp.ClientSession() as session:
        payload = {
            'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI
        }
        async with session.post('https://discord.com/api/v10/oauth2/token', data=payload) as r:
            token_data = await r.json()
            access_token = token_data.get('access_token')
            
            if access_token:
                async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as r2:
                    user_info = await r2.json()
                    conn = sqlite3.connect('restore_user.db')
                    cur = conn.cursor()
                    cur.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_info['id'], server_id, access_token))
                    conn.commit()
                    conn.close()
                
                # 성공 화면: 5entinal 스타일의 블랙 & 화이트 레이아웃
                return f"""
                <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ background-color: #000; color: #fff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                    .container {{ text-align: center; border: 1px solid #222; padding: 50px 30px; border-radius: 15px; background: #050505; box-shadow: 0 10px 30px rgba(0,0,0,0.5); animation: fadeIn 0.8s ease; }}
                    .icon {{ width: 70px; height: 70px; border: 1.5px solid #fff; border-radius: 50%; margin: 0 auto 25px; display: flex; justify-content: center; align-items: center; font-size: 32px; font-weight: 200; }}
                    h1 {{ font-size: 26px; font-weight: 600; letter-spacing: 3px; margin: 10px 0; }}
                    .divider {{ width: 40px; height: 1px; background: #fff; margin: 25px auto; opacity: 0.8; }}
                    .details {{ color: #666; font-size: 13px; margin-top: 20px; text-transform: uppercase; letter-spacing: 1px; }}
                    @keyframes fadeIn {{ from{{opacity:0; transform:translateY(20px);}} to{{opacity:1; transform:translateY(0);}} }}
                </style></head>
                <body><div class="container"><div class="icon">✓</div><h1>VERIFIED</h1><div class="divider"></div>
                <p style="font-size:15px; color:#ccc;">SERVER ID: {server_id}</p>
                <p class="details">인증이 성공적으로 완료되었습니다.<br>이 창을 닫으셔도 됩니다.</p></div></body></html>
                """
    return "인증 실패"

# ================= [ 3. 디스코드 명령어 ] =================

@bot.tree.command(name="인증하기", description="복구 인증 메뉴를 출력합니다 (공개 메시지).")
async def authenticate(it: discord.Interaction):
    view = ui.View()
    
    # 주소창에 server_id 파라미터를 강제로 남기기 위한 URL 구조
    auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds.join"
        f"&state={it.guild_id}"
        f"&server_id={it.guild_id}"
    )
    
    # [오류 수정] Action_Row 대신 ActionRow 또는 직접 View에 추가
    auth_btn = ui.Button(label="SECURITY VERIFY", url=auth_url, style=discord.ButtonStyle.link)
    view.add_item(auth_btn)

    embed = discord.Embed(title="RESTORE SYSTEM", description="서버 보안 및 자동 복구 인증을 위해 아래 버튼을 클릭하세요.", color=0x000000)
    embed.set_footer(text=f"Verified by restore.v0ut.com")
    
    # ephemeral=False로 설정하여 모든 유저가 메시지를 볼 수 있게 함
    await it.response.send_message(embed=embed, view=view, ephemeral=False)

@bot.tree.command(name="유저복구", description="인증된 유저들을 초대합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def restore(it: discord.Interaction):
    await it.response.send_message("🔄 복구 시작...", ephemeral=True)
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id, access_token FROM users WHERE server_id = ?", (str(it.guild_id),))
    users = cur.fetchall()
    conn.close()

    success, fail = 0, 0
    async with aiohttp.ClientSession() as session:
        for u_id, token in users:
            url = f"https://discord.com/api/v10/guilds/{it.guild_id}/members/{u_id}"
            async with session.put(url, headers={"Authorization": f"Bot {TOKEN}"}, json={"access_token": token}) as r:
                if r.status in [201, 204]: success += 1
                else: fail += 1
                await asyncio.sleep(0.5)
                
    await it.followup.send(f"✅ 완료 (성공: {success} / 실패: {fail})")

# ================= [ 4. 실행 ] =================

def run_fastapi():
    # Cloudflare 터널이 바라보는 8080 포트 실행
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    bot.run(TOKEN)
