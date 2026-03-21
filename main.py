import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp, sqlite3, uvicorn, asyncio, json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from threading import Thread

TOKEN = ""
CLIENT_ID = "1482041261111382066"
CLIENT_SECRET = "2IbFgl910fy8yd6WDCAvBGj9Asa-BsQi"
REDIRECT_URI = "https://restore.v0ut.com" 

CF_TURNSTILE_SITE_KEY = "0x4AAAAAACt7wUkh4DATyGf_"
CF_TURNSTILE_SECRET_KEY = "0x4AAAAAACt7wYg5nw0sXHF4URhhszJq_EA"

app = FastAPI()
intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        conn = sqlite3.connect('restore_user.db')
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, server_id TEXT, access_token TEXT, PRIMARY KEY(user_id, server_id))")
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"로그인 완료: {self.user}")

bot = RecoveryBot()

BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
    
    /* 1. 배경 및 전체 화면 중앙 정렬 */
    body {{ 
        background-color: #000; 
        color: #fff; 
        font-family: 'Inter', -apple-system, sans-serif; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        min-height: 100vh; 
        margin: 0; 
        padding: 0;
        box-sizing: border-box; 
    }}
    
    /* 2. 메인 카드 */
    .card {{ 
        background: #0a0a0a; 
        border: 1px solid #1a1a1a; 
        padding: 45px 30px; 
        border-radius: 28px; 
        text-align: center; 
        width: 90%; 
        max-width: 360px; 
        box-shadow: 0 25px 50px rgba(0,0,0,0.8); 
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        justify-content: center; 
        box-sizing: border-box;
    }}
    
    /* 3. 로고 박스 정렬 */
    .logo-box {{ 
        width: 70px; 
        height: 70px; 
        border-radius: 20px; 
        background: #111; 
        border: 1px solid #222; 
        margin: 0 auto 25px auto; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        font-size: 32px; 
    }}
    
    h1 {{ font-size: 24px; font-weight: 700; margin: 0 0 10px 0; letter-spacing: -0.5px; width: 100%; }}
    .subtitle {{ color: #666; font-size: 14px; margin: 0 0 30px 0; line-height: 1.5; width: 100%; word-break: keep-all; }}
    
    /* [수정] 캡차 위젯과 버튼 사이를 20px로 조정 (기존보다 절반 이상 줄임) */
    .cf-turnstile {{ 
        margin-bottom: 20px !important; 
        width: 100%; 
        display: flex; 
        justify-content: center; 
    }}
    
    /* 4. 상태 바 */
    .status-alert {{ 
        background: #111; 
        border: 1px solid #222; 
        border-left: 4px solid #fff; 
        padding: 18px 10px; 
        text-align: center; 
        font-size: 13px; 
        color: #ccc; 
        margin-bottom: 20px; 
        border-radius: 12px; 
        width: 100%; 
        box-sizing: border-box; 
        display: block;
    }}
    
    /* 5. 사용자 정보 및 로딩 바 */
    .user-pill {{ 
        background: #111; 
        border: 1px solid #222; 
        border-radius: 50px; 
        padding: 12px 20px; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin-bottom: 25px; 
        font-size: 13px; 
        width: 100%; 
        box-sizing: border-box; 
    }}
    
    .progress-wrap {{ width: 100%; margin-bottom: 15px; display: flex; flex-direction: column; align-items: center; }}
    .progress-bg {{ background: #1a1a1a; height: 6px; width: 100%; border-radius: 10px; overflow: hidden; margin-bottom: 10px; }}
    .progress-bar {{ background: #fff; height: 100%; width: 0%; transition: width 0.05s linear; }}
    
    .btn-main {{ 
        background: #fff; 
        color: #000; 
        border: none; 
        width: 100%; 
        padding: 18px; 
        border-radius: 16px; 
        font-size: 16px; 
        font-weight: 700; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        cursor: pointer;
        text-decoration: none;
    }}
    
    .footer {{ color: #333; font-size: 11px; margin-top: 35px; letter-spacing: 1px; width: 100%; }}
    
    .fade {{ animation: fadeInUp 0.6s ease-out; }}
    @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(15px); }} to {{ opacity: 1; transform: translateY(0); }} }}

    @media (max-width: 480px) {{
        .card {{ padding: 35px 25px; }}
        h1 {{ font-size: 22px; }}
    }}
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code = request.query_params.get("code")
    server_id = request.query_params.get("state")
    discord_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={server_id}"

    if not code:
        return f"<html><head>{BASE_STYLE}</head><body><div class='card fade'><div class='logo-box'>S</div><h1>서버 보안 인증</h1><p class='subtitle'>계정을 연결하고 서버 접근 권한을<br>획득하세요</p><a href='{discord_url}' class='btn-main'>Discord로 시작하기</a><div class='footer'>RESTORE PROTOCOL</div></div></body></html>"

    async with aiohttp.ClientSession() as session:
        payload = {
            'client_id': CLIENT_ID, 
            'client_secret': CLIENT_SECRET, 
            'grant_type': 'authorization_code', 
            'code': code, 
            'redirect_uri': REDIRECT_URI
        }
        async with session.post('https://discord.com/api/v10/oauth2/token', data=payload) as r:
            t_data = await r.json()
            access_token = t_data.get('access_token')
            if not access_token: return "인증 토큰을 가져오지 못했습니다"
            
            async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as r2:
                u_info = await r2.json()
                return f"""
                <html><head>{BASE_STYLE}</head>
                <body>
                    <div class="card fade">
                        <div class="logo-box">🔒</div>
                        <h1>보안 확인</h1>
                        <p class="subtitle">Cloudflare 보안 시스템이<br>브라우저를 확인 중입니다</p>
                        <div class="user-pill"><span>{u_info.get('username')}</span><a href="{discord_url}" style="color:#fff; text-decoration:none; font-weight:700;">변경</a></div>
                        <form action="/verify" method="post" style="width:100%;">
                            <input type="hidden" name="server_id" value="{server_id}"><input type="hidden" name="access_token" value="{access_token}"><input type="hidden" name="user_id" value="{u_info.get('id')}">
                            <div class="cf-turnstile" data-sitekey="{CF_TURNSTILE_SITE_KEY}" data-theme="dark"></div>
                            <button type="submit" class="btn-main">인증 완료</button>
                        </form>
                    </div>
                </body></html>
                """

@app.post("/verify", response_class=HTMLResponse)
async def verify_turnstile(request: Request, server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    form_data = await request.form()
    turnstile_response = form_data.get("cf-turnstile-response")

    async with aiohttp.ClientSession() as session:
        verify_data = {'secret': CF_TURNSTILE_SECRET_KEY, 'response': turnstile_response}
        async with session.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=verify_data) as resp:
            result = await resp.json()
            if result.get("success"):
                conn = sqlite3.connect('restore_user.db')
                conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_id, server_id, access_token))
                conn.commit()
                conn.close()
                
                return f"""
                <html><head>{BASE_STYLE}</head>
                <body>
                    <div class="card fade">
                        <div id="loading-area" style="width:100%;">
                            <div class="logo-box">🔒</div>
                            <h1>보안 승인 중</h1>
                            <p class="subtitle">서버 권한을 할당하고 있습니다<br>잠시만 기다려 주세요</p>
                            <div class="progress-wrap">
                                <div class="progress-bg"><div id="bar" class="progress-bar"></div></div>
                                <div id="pct" style="font-size:14px; font-weight:700;">0%</div>
                            </div>
                        </div>
                        <div id="success-area" style="display:none; width:100%;">
                            <div class="logo-box" style="background:#fff; color:#000;">✓</div>
                            <h1>인증 완료</h1>
                            <p class="subtitle">보안 검사가 성공적으로 끝났습니다</p>
                            <div class="status-alert">성공적으로 승인되었습니다</div>
                            <div class="footer">SERVICE VOUT VERIFIED</div>
                        </div>
                    </div>
                    <script>
                        let p = 0;
                        const b = document.getElementById('bar');
                        const t = document.getElementById('pct');
                        const l = document.getElementById('loading-area');
                        const s = document.getElementById('success-area');
                        const iv = setInterval(() => {{
                            p++;
                            b.style.width = p + '%';
                            t.innerText = p + '%';
                            if (p >= 100) {{
                                clearInterval(iv);
                                l.style.display = 'none';
                                s.style.display = 'block';
                            }}
                        }}, 40);
                    </script>
                </body></html>
                """
            else: return "보안 검증에 실패했습니다"

@bot.tree.command(name="인증하기", description="인증하기 컨테이너를 전송합니다")
async def authenticate(it: discord.Interaction):
    await it.response.send_message(content="**인증버튼이 전송되었습니다**", ephemeral=True)

    res_con = ui.Container()
    res_con.accent_color = 0xffffff
    
    res_con.add_item(ui.TextDisplay("## 서버 인증"))
    res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    res_con.add_item(ui.TextDisplay(
        "아래 버튼을 눌러 인증하셔야 이용이 가능합니다\n"
        "**`IP, 이메일, 통신사`** 등 일절 수집하지 않습니다"
    ))
    res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds.join"
        f"&state={it.guild_id}"
    )
    
    auth_btn = ui.Button(
        label="인증하기", 
        url=auth_url, 
        style=discord.ButtonStyle.link, 
        emoji="<:emoji_14:1484745886696476702>"
    )
    res_con.add_item(ui.ActionRow(auth_btn))

    view = ui.LayoutView().add_item(res_con)

    await it.channel.send(view=view)

@bot.tree.command(name="유저복구", description="인증했던 유저들을 서버에 복구하기")
@app_commands.checks.has_permissions(administrator=True)
async def restore(it: discord.Interaction):
    process_con = ui.Container()
    process_con.accent_color = 0xffa500
    process_con.add_item(ui.TextDisplay("## 유저 복구 가동"))
    process_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    process_con.add_item(ui.TextDisplay("DB에서 유저 정보를 조회중입니다"))
    
    process_view = ui.LayoutView().add_item(process_con)
    await it.response.send_message(view=process_view, ephemeral=True)
    
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id, access_token FROM users WHERE server_id = ?", (str(it.guild_id),))
    all_users = cur.fetchall()
    conn.close()

    if not all_users:
        error_con = ui.Container()
        error_con.accent_color = 0xff0000
        error_con.add_item(ui.TextDisplay("## 복구 불가"))
        error_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        error_con.add_item(ui.TextDisplay("복구할 유저 데이터가 존재하지 않습니다\n인증된 유저가 있는지 먼저 확인해 주세요"))
        return await it.edit_original_response(view=ui.LayoutView().add_item(error_con))

    success, fail = 0, 0
    async with aiohttp.ClientSession() as session:
        for u_id, token in all_users:
            url = f"https://discord.com/api/v10/guilds/{it.guild_id}/members/{u_id}"
            headers = {
                "Authorization": f"Bot {TOKEN}",
                "Content-Type": "application/json"
            }
            async with session.put(url, headers=headers, json={"access_token": token}) as resp:
                if resp.status in [201, 204]:
                    success += 1
                else:
                    fail += 1
                await asyncio.sleep(0.5)

    result_con = ui.Container()
    result_con.accent_color = 0x00ff00
    result_con.add_item(ui.TextDisplay("## 복구 작업 완료"))
    result_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    result_con.add_item(ui.TextDisplay(
        f"**복구 결과**\n"
        f"```성공: {success}명```\n"
        f"```실패: {fail}명```"
    ))
    
    result_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    result_con.add_item(ui.TextDisplay("-# 복구가 성공적으로 완료되었습니다"))
    
    final_view = ui.LayoutView().add_item(result_con)
    
    await it.edit_original_response(view=final_view)

@bot.tree.command(name="인증유저", description="인증 완료된 유저 수를 확인합니다")
async def total_users(it: discord.Interaction):
    loading_con = ui.Container()
    loading_con.accent_color = 0xffa500
    loading_con.add_item(ui.TextDisplay("## DB 조회 중"))
    loading_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    loading_con.add_item(ui.TextDisplay("인증 유저 정보를 불러오고 있습니다\n잠시만 기다려 주세요..."))
    loading_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    loading_con.add_item(ui.TextDisplay("-# DB는 365일 안전하게 보관됩니다"))
    
    loading_view = ui.LayoutView().add_item(loading_con)
    
    await it.response.send_message(view=loading_view, ephemeral=True)

    await asyncio.sleep(3)

    conn = sqlite3.connect('restore_user.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM users")
    user_count = cursor.fetchone()[0]
    conn.close()

    verify_con = ui.Container()
    verify_con.accent_color = 0xffffff 
    
    verify_con.add_item(ui.TextDisplay("## 인증 유저 통계"))
    verify_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    verify_con.add_item(ui.TextDisplay(f"**인증 완료된 유저수**\n```{user_count}명```"))
    verify_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    verify_con.add_item(ui.TextDisplay("-# DB는 365일 안전하게 보관됩니다"))
    
    final_view = ui.LayoutView().add_item(verify_con)

    await it.edit_original_response(view=final_view)

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

if __name__ == "__main__":
    api_thread = Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"봇 실행 중 오류 발생: {e}")
