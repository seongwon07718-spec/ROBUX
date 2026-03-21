import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, uvicorn, asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from threading import Thread

# [1. 필수 설정]
TOKEN = "YOUR_BOT_TOKEN"
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
REDIRECT_URI = "https://restore.v0ut.com" # HTTPS로 설정

app = FastAPI()
intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        conn = sqlite3.connect('restore_user.db')
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, PRIMARY KEY(user_id, server_id))")
        conn.commit()
        conn.close()
        await self.tree.sync()

bot = RecoveryBot()

# [2. FastAPI: 블랙&화이트 웹 디자인 반영]
@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code = request.query_params.get("code")
    server_id = request.query_params.get("server_id") or request.query_params.get("state")
    
    if not code:
        # 초기 접속 시 혹은 에러 시 화면
        return """
        <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body { background-color: #000; color: #fff; font-family: 'Inter', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                    .card { border: 1px solid #333; padding: 40px; border-radius: 12px; text-align: center; max-width: 400px; width: 90%; }
                    h1 { font-size: 24px; margin-bottom: 20px; font-weight: 700; }
                    p { color: #888; line-height: 1.6; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>ACCESS DENIED</h1>
                    <p>인증 코드가 올바르지 않거나 만료되었습니다.</p>
                </div>
            </body>
        </html>
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
                
                # 인증 성공 화면 (Black & White 디자인)
                return f"""
                <html>
                    <head>
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <style>
                            body {{ background-color: #000; color: #fff; font-family: -apple-system, system-ui, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                            .container {{ text-align: center; animation: fadeIn 0.8s ease-in-out; }}
                            .logo {{ width: 80px; height: 80px; border: 2px solid #fff; border-radius: 50%; margin: 0 auto 30px; display: flex; justify-content: center; align-items: center; font-size: 30px; font-weight: bold; }}
                            h1 {{ font-size: 28px; letter-spacing: -1px; margin-bottom: 10px; }}
                            .status {{ color: #aaa; font-size: 14px; margin-bottom: 40px; }}
                            .line {{ width: 50px; height: 1px; background: #fff; margin: 20px auto; }}
                            @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="logo">V</div>
                            <h1>VERIFIED</h1>
                            <div class="line"></div>
                            <p class="status">SERVER ID: {server_id}</p>
                            <p style="font-size: 13px; color: #666;">인증이 완료되었습니다. 창을 닫아주세요.</p>
                        </div>
                    </body>
                </html>
                """
    return "인증 처리 중 오류가 발생했습니다."

# [3. Discord: 명령어 설정]
@bot.tree.command(name="인증하기")
async def authenticate(it: discord.Interaction):
    view = ui.View()
    # 주소창에 ?server_id= 가 남도록 하기 위해 redirect_uri를 가공하여 링크 생성
    auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds.join"
        f"&state={it.guild_id}"
        f"&server_id={it.guild_id}" # 주소창 유지용 파라미터
    )
    
    auth_btn = ui.Button(label="SECURITY VERIFY", url=auth_url, style=discord.ButtonStyle.link)
    view.add_item(auth_btn)

    embed = discord.Embed(title="RESTORE SYSTEM", description="서버 보안 및 자동 복구 인증을 시작합니다.", color=0x000000)
    embed.set_footer(text="Verified by restore.v0ut.com")
    
    await it.response.send_message(embed=embed, view=view, ephemeral=False)

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    bot.run(TOKEN)
