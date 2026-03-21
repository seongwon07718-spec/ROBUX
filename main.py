import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, uvicorn, asyncio, json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from threading import Thread

# ================= [ 1. 설정 정보 ] =================
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
        print(f"로그인 완료: {self.user}")

bot = RecoveryBot()

# ================= [ 2. FastAPI: 3단계 웹 디자인 & 로직 ] =================

# 모든 단계에서 공통으로 사용할 블랙 & 화이트 베이스 스타일
BASE_STYLE = """
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    body { background-color: #000; color: #fff; font-family: -apple-system, system-ui, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
    .card { background: #080808; border: 1px solid #1a1a1a; padding: 40px 30px; border-radius: 16px; text-align: center; width: 90%; max-width: 360px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .secure-badge { background: #111; border: 1px solid #222; color: #888; font-size: 11px; padding: 5px 10px; border-radius: 20px; display: inline-flex; align-items: center; gap: 5px; margin-bottom: 20px; }
    .server-logo { width: 65px; height: 65px; border-radius: 15px; background: #111; border: 1px solid #222; margin: 0 auto 20px; display: flex; justify-content: center; align-items: center; font-size: 28px; font-weight: bold; }
    h1 { font-size: 22px; font-weight: 600; margin: 0 0 10px 0; letter-spacing: -0.5px; }
    .subtitle { color: #666; font-size: 13px; margin-bottom: 30px; }
    .footer-text { color: #444; font-size: 11px; margin-top: 30px; }
    /* 애니메이션 */
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .fade { animation: fadeIn 0.5s ease-out; }
</style>
"""

# 메인 엔드포인트: 단계별 화면 전환 로직 포함
@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code = request.query_params.get("code")
    server_id = request.query_params.get("state")
    
    # [설정] 디스코드 로그인 URL
    discord_login_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds.join"
        f"&state={server_id}"
    )

    # --------------------------------------------------
    # 단계 1: 디스코드 로그인 대기 (사진 12번 디자인)
    # --------------------------------------------------
    if not code:
        return f"""
        <html><head>{BASE_STYLE}</head>
        <body>
            <div class="card fade">
                <div class="secure-badge">🔒 안전한 인증</div>
                <div class="server-logo">S</div>
                <h1>서버 인증</h1>
                <p class="subtitle">계정을 확인하고 역할을 지급받으세요</p>
                
                <div style="background:#111; border: 1px solid #222; border-left: 3px solid #007bff; padding: 15px; text-align: left; font-size: 13px; color: #ccc; margin-bottom: 20px; border-radius: 4px;">
                    디스코드 계정 로그인 후 인증을 진행할 수 있습니다.
                </div>
                
                <a href="{discord_login_url}" style="text-decoration: none;">
                    <button style="background: #28a745; color: #fff; border: none; width: 100%; padding: 12px; border-radius: 4px; font-size: 14px; font-weight: 600; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 8px;">
                        🚀 Discord로 로그인
                    </button>
                </a>
                
                <p class="footer-text">문제가 계속되면 서버 관리자에게 문의하세요.</p>
            </div>
        </body></html>
        """

    # --------------------------------------------------
    # 로직: 디스코드 로그인 후 토큰 처리
    # --------------------------------------------------
    async with aiohttp.ClientSession() as session:
        payload = {
            'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI
        }
        async with session.post('https://discord.com/api/v10/oauth2/token', data=payload) as r:
            token_data = await r.json()
            access_token = token_data.get('access_token')
            
            if not access_token:
                return "인증 실패 (토큰 오류)"

            async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as r2:
                user_info = await r2.json()
                username = user_info.get('username')
                
                # DB 저장
                conn = sqlite3.connect('restore_user.db')
                conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_info['id'], server_id, access_token))
                conn.commit()
                conn.close()

                # --------------------------------------------------
                # 단계 2: 캡차/최종 승인 대기 (사진 13번 디자인)
                # --------------------------------------------------
                # 실제 hCaptcha를 적용하려면 사이트키가 필요하므로, 여기서는 디자인만 구현했습니다.
                return f"""
                <html><head>{BASE_STYLE}</head>
                <body>
                    <div class="card fade">
                        <div class="secure-badge">🔒 안전한 인증</div>
                        <div class="server-logo">S</div>
                        <h1>서버 인증</h1>
                        <p class="subtitle">계정을 확인하고 역할을 지급받으세요</p>
                        
                        <div style="background:#111; border: 1px solid #222; padding: 10px; text-align: center; font-size: 12px; color: #888; margin-bottom: 15px; border-radius: 4px;">
                            Captcha required.
                        </div>

                        <div style="background:#111; border: 1px solid #222; border-radius: 4px; padding: 15px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <span style="font-size: 13px; color: #aaa;">로그인: {username}</span>
                            <a href="{discord_login_url}" style="text-decoration: none;">
                                <button style="background: #222; color: #fff; border: 1px solid #333; padding: 5px 10px; border-radius: 4px; font-size: 12px; cursor: pointer;">계정 바꾸기</button>
                            </a>
                        </div>

                        <p style="color: #666; font-size: 12px; margin-bottom: 10px;">자동 프로그램이 아닌지 확인해 주세요.</p>
                        
                        <div style="background: #fff; color: #000; padding: 15px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div style="width: 20px; height: 20px; border: 2px solid #ccc;"></div>
                                <span style="font-size: 14px;">사람입니다</span>
                            </div>
                            <div style="text-align: right; font-size: 10px; color: #888;">hCaptcha<br>개인정보 보호 - 약관</div>
                        </div>

                        <form action="/success" method="get">
                            <input type="hidden" name="state" value="{server_id}">
                            <button type="submit" style="background: #28a745; color: #fff; border: none; width: 100%; padding: 12px; border-radius: 4px; font-size: 14px; font-weight: 600; cursor: pointer;">
                                ✅ 인증하기
                            </button>
                        </form>
                        
                        <p class="footer-text">문제가 계속되면 서버 관리자에게 문의하세요.</p>
                    </div>
                </body></html>
                """

# --------------------------------------------------
# 단계 3: 인증 완료 화면 (사진 14번 디자인)
# --------------------------------------------------
@app.get("/success", response_class=HTMLResponse)
async def oauth_success(request: Request):
    server_id = request.query_params.get("state")
    # 로그인 URL (재인증용)
    discord_login_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={server_id}"

    return f"""
    <html><head>{BASE_STYLE}</head>
    <body>
        <div class="card fade">
            <div class="secure-badge">🔒 안전한 인증</div>
            <div class="server-logo">S</div>
            <h1>서버 인증</h1>
            <p class="subtitle">계정을 확인하고 역할을 지급받으세요</p>
            
            <div style="background:#111; border: 1px solid #222; padding: 15px; text-align: center; font-size: 13px; color: #aaa; margin-bottom: 15px; border-radius: 4px;">
                인증이 완료되었습니다.
            </div>

            <div style="background:#111; border: 1px solid #222; border-left: 3px solid #007bff; padding: 15px; text-align: center; font-size: 13px; color: #fff; margin-bottom: 15px; border-radius: 4px; display: flex; justify-content: center; align-items: center; gap: 8px;">
                ✅ 이미 인증하셨습니다.
            </div>

            <a href="{discord_login_url}" style="text-decoration: none;">
                <button style="background: #1a1a1a; color: #fff; border: 1px solid #333; width: 100%; padding: 10px; border-radius: 4px; font-size: 13px; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 8px;">
                    🔄 재인증 하기
                </button>
            </a>
            
            <p class="footer-text">문제가 계속되면 서버 관리자에게 문의하세요.</p>
        </div>
    </body></html>
    """

# ================= [ 3. Discord: 명령어 ] =================

@bot.tree.command(name="인증하기", description="복구 인증 메뉴를 출력합니다.")
async def authenticate(it: discord.Interaction):
    view = ui.View()
    # OAuth2 주소 (여기로 접속하면 단계 1 화면이 뜸)
    auth_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={it.guild_id}"
    
    view.add_item(ui.Button(label="SECURITY VERIFY", url=auth_url, style=discord.ButtonStyle.link))
    await it.response.send_message(embed=discord.Embed(title="RESTORE SYSTEM", description="서버 보안 인증을 위해 버튼을 누르세요.", color=0x000000), view=view)

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    bot.run(TOKEN)
