CLIENT_ID = "1482041261111382066"
CLIENT_SECRET = "2IbFgl910fy8yd6WDCAvBGj9Asa-BsQi"
REDIRECT_URI = "https://restore.v0ut.com" 

WEBHOOK_URL = "https://discord.com/api/webhooks/1484910080502530241/H_K88yZrBqktgmEuqLJXF4KYWJoUCN6xU7IC6sDSVVz5oSNwfil3Gr3O9bUSxdWZTHeW"
CF_TURNSTILE_SITE_KEY = "0x4AAAAAACt7wUkh4DATyGf_"
CF_TURNSTILE_SECRET_KEY = "0x4AAAAAACt7wYg5nw0sXHF4URhhszJq_EA"

app = FastAPI()
intents = discord.Intents.all()

class RecoveryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        conn = sqlite3.connect('restore_user.db')
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT, 
                server_id TEXT, 
                access_token TEXT, 
                ip_addr TEXT, 
                PRIMARY KEY(user_id, server_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                server_id TEXT PRIMARY KEY, 
                role_id TEXT, 
                block_alt INTEGER DEFAULT 0, 
                block_vpn INTEGER DEFAULT 0
            )
        """)
        try: conn.execute("ALTER TABLE settings ADD COLUMN block_alt INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN ip_addr TEXT")
        except: pass
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"Bot Login: {self.user}")

    async def give_role_task(self, server_id: str, user_id: str, role_id: int):
        try:
            guild = self.get_guild(int(server_id))
            if guild:
                member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                role = guild.get_role(role_id)
                if member and role: await member.add_roles(role)
        except: pass

    async def send_container_log(self, server_id: str, user_data: dict, ip: str):
        conn = sqlite3.connect('restore_user.db')
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE server_id = ?", (server_id,))
        total_count = cur.fetchone()[0]
        conn.close()

        if WEBHOOK_URL:
            log_con = ui.Container()
            log_con.accent_color = 0xffffff
            log_con.add_item(ui.TextDisplay("## 인증 완료"))
            log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_con.add_item(ui.TextDisplay(
                f"{total_count}명의 사용자가 인증했습니다\n"
                f"인증시간 {now}\n"))
            log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            log_con.add_item(f"<@{user_data['id']}> 님이 인증을 완료했습니다\n"
            )
            
            view = ui.LayoutView().add_item(log_con)
            
            async with aiohttp.ClientSession() as session:
                payload = {"components": view.to_dict()["components"]}
                await session.post(WEBHOOK_URL, json=payload)

bot = RecoveryBot()

BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* 화면 고정 설정 */
    html, body {{ 
        margin: 0; padding: 0; width: 100%; height: 100%; 
        overflow: hidden; /* 스크롤 차단 */
        position: fixed; /* 화면 고정 */
        touch-action: none; /* 터치 드래그 방지 */
        background: #000; color: #fff; font-family: 'Inter', sans-serif; 
    }}

    body {{ 
        display: flex; justify-content: center; align-items: center;
        background: radial-gradient(circle at center, #1c1c1c 0%, #000 100%);
    }}

    .card {{ 
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08); 
        padding: 40px 24px; border-radius: 34px; text-align: center;
        width: 82%; max-width: 310px; backdrop-filter: blur(30px); -webkit-backdrop-filter: blur(30px);
        display: flex; flex-direction: column; gap: 20px;
        box-shadow: 0 40px 120px rgba(0,0,0,0.85);
        animation: fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1);
    }}

    .logo-box {{
        width: 58px; height: 58px; background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1); border-radius: 19px;
        margin: 0 auto; display: flex; align-items: center; justify-content: center;
    }}

    .lock-icon {{ width: 24px; height: 24px; fill: #fff; opacity: 0.9; }}

    h1 {{ font-size: 19px; font-weight: 700; margin: 0; letter-spacing: -0.8px; }}
    .desc {{ color: #777; font-size: 13.5px; margin: 0; line-height: 1.6; word-break: keep-all; }}

    .user-pill {{
        background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
        padding: 12px 15px; border-radius: 15px; display: flex; justify-content: space-between;
        align-items: center; font-size: 13px; color: #aaa;
    }}

    /* 캡챠와 버튼 크기 동기화 핵심 */
    .form-container {{
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 16px;
        align-items: center;
    }}

    .cf-turnstile {{
        width: 100% !important;
        display: flex;
        justify-content: center;
    }}

    .btn-main {{
        background: rgba(255, 255, 255, 0.05); 
        color: #fff; border: 1px solid rgba(255, 255, 255, 0.12);
        width: 100%; padding: 0; border-radius: 14px;
        font-weight: 600; font-size: 15px; cursor: pointer; transition: all 0.4s ease;
        position: relative; overflow: hidden; display: flex; justify-content: center; align-items: center;
        height: 52px; text-decoration: none; box-sizing: border-box;
    }}

    .btn-main:hover {{ background: rgba(255, 255, 255, 0.08); border-color: rgba(255, 255, 255, 0.2); }}

    .progress-bar {{
        position: absolute; left: 0; top: 0; height: 100%; 
        background: rgba(255, 255, 255, 0.15); width: 0%;
        z-index: 1; transition: width 0.1s ease-out;
    }}

    .btn-text {{ position: relative; z-index: 2; letter-spacing: 0.2px; }}

    .footer {{ color: #222; font-size: 9px; letter-spacing: 3.5px; font-weight: 800; text-transform: uppercase; margin-top: 5px; }}

    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(25px); }} to {{ opacity: 1; transform: translateY(0); }} }}
</style>
<script>
    function handleVerify(event) {{
        event.preventDefault();
        const btn = document.getElementById('submit-btn');
        const text = document.getElementById('btn-txt');
        const form = document.getElementById('verify-form');
        
        btn.style.pointerEvents = 'none';
        
        const bar = document.createElement('div');
        bar.className = 'progress-bar';
        btn.appendChild(bar);
        
        let progress = 0;
        const interval = setInterval(() => {{
            progress += Math.random() * 2.5 + 1;
            if (progress >= 100) {{
                progress = 100;
                clearInterval(interval);
                text.innerText = "SUCCESS 100%";
                setTimeout(() => form.submit(), 300);
            }}
            bar.style.width = progress + '%';
            text.innerText = "확인중... " + Math.floor(progress) + "%";
        }}, 40);
    }}
</script>
"""

LOCK_SVG = '<svg class="lock-icon" viewBox="0 0 24 24"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zM9 6c0-1.66 1.34-3 3-3s3 1.34 3 3v2H9V6zm9 14H6V10h12v10zm-6-3c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2z"/></svg>'

@app.get("/", response_class=HTMLResponse)
async def oauth_main(request: Request):
    code = request.query_params.get("code")
    sid = request.query_params.get("state")
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join&state={sid}"
    
    if not code:
        return f"""<html><head>{BASE_STYLE}</head><body>
        <div class="card">
            <div class="logo-box">{LOCK_SVG}</div>
            <h1>서버 인증</h1>
            <p class="desc">계정 로그인하셔야 인증 가능합니다<br>로그인하여 인증을 완료해주세요</p>
            <a href="{url}" class="btn-main"><span class="btn-text">Discord 로그인</span></a>
            <div class="footer">SERVICE VOUT VERIFLY</div>
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
            res = await r.json()
            atk = res.get('access_token')
            if not atk: return "세션 만료 다시 인증해 주세요"
            
            async with session.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {atk}'}) as r2:
                u = await r2.json()
                return f"""<html><head>{BASE_STYLE}</head><body>
                <div class="card">
                    <div class="logo-box">{LOCK_SVG}</div>
                    <h1>인증 단계</h1>
                    <p class="desc">인증 완료 버튼을 눌려 인증해주세요<br>인증 안될 시 @sewwon_ 문의해주세요</p>
                    <div class="user-pill">
                        <span>{u.get('username')}</span>
                        <a href="{url}" style="color:#fff; text-decoration:none; font-weight:700; font-size:11px; opacity:0.6;">변경</a>
                    </div>
                    <form id="verify-form" action="/verify" method="post" onsubmit="handleVerify(event)" class="form-container">
                        <input type="hidden" name="server_id" value="{sid}">
                        <input type="hidden" name="access_token" value="{atk}">
                        <input type="hidden" name="user_id" value="{u.get('id')}">
                        <div class="cf-turnstile" data-sitekey="{CF_TURNSTILE_SITE_KEY}" data-theme="dark" data-width="flexible"></div>
                        <button type="submit" id="submit-btn" class="btn-main">
                            <span id="btn-txt" class="btn-text">인증 완료</span>
                        </button>
                    </form>
                </div></body></html>"""

@app.post("/verify", response_class=HTMLResponse)
async def verify_post(request: Request, server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    f = await request.form()
    c = f.get("cf-turnstile-response")
    ip = request.headers.get("cf-connecting-ip") or request.client.host

    async with aiohttp.ClientSession() as session:
        v = {'secret': CF_TURNSTILE_SECRET_KEY, 'response': c}
        async with session.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=v) as resp:
            vr = await resp.json()
            if not vr.get("success"): return "캡차 인증 실패"

            conn = sqlite3.connect('restore_user.db')
            cur = conn.cursor()
            cur.execute("SELECT role_id, block_alt FROM settings WHERE server_id = ?", (server_id,))
            st = cur.fetchone()
            
            if st and st[1] == 1:
                cur.execute("SELECT user_id FROM users WHERE server_id = ? AND ip_addr = ? AND user_id != ?", (server_id, ip, user_id))
                if cur.fetchone():
                    conn.close()
                    return "중복 계정 감지: 이미 인증된 IP입니다"

            conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (user_id, server_id, access_token, ip))
            conn.commit()
            if st and st[0]:
                asyncio.run_coroutine_threadsafe(bot.give_role_task(server_id, user_id, int(st[0])), bot.loop)
            conn.close()

            return f"""<html><head>{BASE_STYLE}</head><body>
            <div class="card">
                <div class="logo-box" style="background:#fff;">
                    <svg style="width:24px; height:24px; fill:#000;" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                </div>
                <h1>인증 완료</h1>
                <p class="desc">성공적으로 인증되었습니다<br>정상적으로 서버 이용이 가능합니다</p>
                <div style="background:rgba(255,255,255,0.04); padding:15px; border-radius:15px; font-size:12px; border:1px solid rgba(255,255,255,0.08);">
                    인증 여부: <span style="color:#00ff88; font-weight:700;">Success</span>
                </div>
                <div class="footer">SYSTEM SECURED</div>
            </div></body></html>"""

# [슬래시 명령어]
@bot.tree.command(name="지급역할", description="인증 완료 시 지급할 역할을 설정합니다")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(role="지급할 역할을 선택하세요")
async def set_role(it: discord.Interaction, role: discord.Role):
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO settings (server_id, role_id) VALUES (?, ?)", (str(it.guild_id), str(role.id)))
    conn.commit()
    conn.close()

    role_con = ui.Container()
    role_con.accent_color = 0xffffff
    role_con.add_item(ui.TextDisplay("## 역할 설정 완료"))
    role_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    role_con.add_item(ui.TextDisplay(f"인증을 완료한 유저에게 앞으로\n{role.mention} 역할이 자동 지급됩니다"))
    role_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    role_con.add_item(ui.TextDisplay("-# 365일 안전한 Vout Service"))
    
    view = ui.LayoutView().add_item(role_con)
    await it.response.send_message(view=view, ephemeral=True)

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

@bot.tree.command(name="인증제한", description="부계정 및 VPN 인증 제한 설정")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(부계정=[app_commands.Choice(name="상관있음 (차단)", value=1), app_commands.Choice(name="상관없음 (허용)", value=0)],
                      vpn=[app_commands.Choice(name="상관있음 (차단)", value=1), app_commands.Choice(name="상관없음 (허용)", value=0)])
async def restrict_auth(it: discord.Interaction, 부계정: int, vpn: int):
    conn = sqlite3.connect('restore_user.db')
    conn.execute("INSERT INTO settings (server_id, block_alt, block_vpn) VALUES (?, ?, ?) ON CONFLICT(server_id) DO UPDATE SET block_alt=excluded.block_alt, block_vpn=excluded.block_vpn", (str(it.guild_id), 부계정, vpn))
    conn.commit()
    conn.close()

    alt_status = "🚫 차단" if 부계정 == 1 else "✅ 허용"
    vpn_status = "🚫 차단" if vpn == 1 else "✅ 허용"
    
    con = ui.Container()
    con.accent_color = 0xffffff
    con.add_item(ui.TextDisplay("## 보안 설정 완료"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(f"부계정: `{alt_status}`\nVPN: `{vpn_status}`"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay("이 설정은 DB에 안전하게 저장됩니다"))
    await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

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
            headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
            async with session.put(url, headers=headers, json={"access_token": token}) as resp:
                if resp.status in [201, 204]: success += 1
                else: fail += 1
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
