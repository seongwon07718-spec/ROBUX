BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
    
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
        background-image: radial-gradient(circle at center, #111 0%, #000 100%);
    }}

    .card {{ 
        background: transparent; /* 박스 투명화 */
        border: 1px solid rgba(255, 255, 255, 0.1); 
        padding: 40px; 
        border-radius: 32px; 
        text-align: center; 
        width: 90%; 
        max-width: 380px; 
        backdrop-filter: blur(10px); /* 배경 흐림 효과로 고급스러움 추가 */
        display: flex;
        flex-direction: column;
        gap: 20px; /* 모든 요소 간격을 20px로 일정하게 고정 */
    }}

    .logo-box {{ 
        width: 64px; 
        height: 64px; 
        border-radius: 18px; 
        background: rgba(255, 255, 255, 0.05); 
        border: 1px solid rgba(255, 255, 255, 0.1); 
        margin: 0 auto; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        font-size: 28px;
    }}

    h1 {{ font-size: 22px; font-weight: 700; margin: 0; letter-spacing: -0.5px; }}
    
    .subtitle {{ 
        color: #888; 
        font-size: 14px; 
        margin: 0; 
        line-height: 1.5; 
        word-break: keep-all; 
    }}

    .user-pill {{ 
        background: rgba(255, 255, 255, 0.05); 
        border: 1px solid rgba(255, 255, 255, 0.1); 
        border-radius: 14px; 
        padding: 12px 16px; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        font-size: 13px; 
    }}

    .cf-turnstile {{ 
        display: flex; 
        justify-content: center; 
        min-height: 65px;
    }}

    .btn-main {{ 
        background: #fff; 
        color: #000; 
        border: none; 
        width: 100%; 
        padding: 16px; 
        border-radius: 14px; 
        font-size: 15px; 
        font-weight: 700; 
        cursor: pointer; 
        text-decoration: none;
        transition: transform 0.2s;
    }}
    
    .btn-main:active {{ transform: scale(0.98); }}

    .footer {{ color: #444; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; margin-top: 10px; }}

    /* 애니메이션 */
    .fade {{ animation: fadeInUp 0.5s ease-out forwards; }}
    @keyframes fadeInUp {{ 
        from {{ opacity: 0; transform: translateY(10px); }} 
        to {{ opacity: 1; transform: translateY(0); }} 
    }}
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code = request.query_params.get("code")
    server_id = request.query_params.get("state")
    discord_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={server_id}"
    
    if not code:
        return f"""<html><head>{BASE_STYLE}</head><body>
        <div class='card fade'>
            <div class='logo-box'>S</div>
            <h1>서버 보안 인증</h1>
            <p class='subtitle'>계정을 연결하고 서버 접근 권한을<br>획득하세요</p>
            <a href='{discord_url}' class='btn-main'>Discord로 시작하기</a>
            <div class='footer'>RESTORE PROTOCOL</div>
        </div></body></html>"""

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
            if not access_token: return "오류: 액세스 토큰을 받아오지 못했습니다."
            
            async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as r2:
                u_info = await r2.json()
                return f"""<html><head>{BASE_STYLE}</head><body>
                <div class="card fade">
                    <div class="logo-box">🔒</div>
                    <h1>보안 확인</h1>
                    <p class="subtitle">Cloudflare 보안 시스템이<br>브라우저를 확인 중입니다</p>
                    <div class="user-pill">
                        <span>{u_info.get('username')}</span>
                        <a href="{discord_url}" style="color:#fff; text-decoration:none; font-weight:700;">변경</a>
                    </div>
                    <form action="/verify" method="post" style="display:flex; flex-direction:column; gap:20px; width:100%;">
                        <input type="hidden" name="server_id" value="{server_id}">
                        <input type="hidden" name="access_token" value="{access_token}">
                        <input type="hidden" name="user_id" value="{u_info.get('id')}">
                        <div class="cf-turnstile" data-sitekey="{CF_TURNSTILE_SITE_KEY}" data-theme="dark"></div>
                        <button type="submit" class="btn-main">인증 완료</button>
                    </form>
                    <div class="footer">RESTORE PROTOCOL</div>
                </div></body></html>"""

@app.post("/verify", response_class=HTMLResponse)
async def verify_turnstile(request: Request, server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    form_data = await request.form()
    turnstile_response = form_data.get("cf-turnstile-response")
    user_ip = request.headers.get("cf-connecting-ip") or request.client.host

    async with aiohttp.ClientSession() as session:
        verify_data = {'secret': CF_TURNSTILE_SECRET_KEY, 'response': turnstile_response}
        async with session.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=verify_data) as resp:
            result = await resp.json()
            if not result.get("success"):
                return "보안 검증에 실패했습니다. 다시 시도해 주세요."

            conn = sqlite3.connect('restore_user.db')
            cur = conn.cursor()
            cur.execute("SELECT role_id, block_alt FROM settings WHERE server_id = ?", (server_id,))
            setting = cur.fetchone()
            
            if setting and setting[1] == 1:
                cur.execute("SELECT user_id FROM users WHERE server_id = ? AND ip_addr = ? AND user_id != ?", (server_id, user_ip, user_id))
                if cur.fetchone():
                    conn.close()
                    return "인증 제한: 동일한 IP에서 다른 계정으로 인증된 기록이 있습니다."

            conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (user_id, server_id, access_token, user_ip))
            conn.commit()
            if setting and setting[0]:
                asyncio.run_coroutine_threadsafe(bot.give_role_task(server_id, user_id, int(setting[0])), bot.loop)
            conn.close()

            return f"""<html><head>{BASE_STYLE}</head><body>
            <div class="card fade">
                <div class="logo-box" style="background:#fff; color:#000;">✓</div>
                <h1>인증 완료</h1>
                <p class="subtitle">보안 검사가 성공적으로 끝났습니다</p>
                <div style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 20px; border-radius: 16px; font-size: 14px;">
                    성공적으로 승인되었습니다
                </div>
                <div class="footer">SERVICE VOUT VERIFIED</div>
            </div></body></html>"""
