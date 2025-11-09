from flask import Flask, redirect, request, session, render_template_string, jsonify
import requests
import sqlite3
import datetime

app = Flask(__name__)

# 직접 입력하는 환경 변수
CLIENT_ID = "여기에_OAuth2_클라이언트_ID_입력"
CLIENT_SECRET = "여기에_OAuth2_클라이언트_시크릿_입력"
FLASK_SECRET_KEY = "여기에_안전한_랜덤_문자열_입력"
BOT_TOKEN = "여기에_봇_토큰_입력"
WEB_BASE_URL = "http://localhost:5000"
REDIRECT_URI_VERIFY = f"{WEB_BASE_URL}/callback_verify"

app.secret_key = FLASK_SECRET_KEY
DISCORD_API_BASE = "https://discord.com/api/v10"

def get_db_connection():
    conn = sqlite3.connect('bot_data.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_guild_settings_web(guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,))
    settings = cursor.fetchone()
    conn.close()
    return settings

def record_verified_user(user_id, guild_id, username, access_token, refresh_token, expires_in, is_alt_account=False, is_vpn_user=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    verified_at = datetime.datetime.utcnow().isoformat()
    token_expires_at = (datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)).isoformat()
    cursor.execute("""
        INSERT OR REPLACE INTO verified_users
        (user_id, guild_id, username, verified_at, is_alt_account, is_vpn_user, access_token, refresh_token, token_expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, guild_id, username, verified_at, is_alt_account, is_vpn_user, access_token, refresh_token, token_expires_at))
    conn.commit()
    conn.close()

def get_verified_users_for_guild(guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, access_token, refresh_token, token_expires_at FROM verified_users WHERE guild_id = ?", (guild_id,))
    users = cursor.fetchall()
    conn.close()
    return users

def update_user_tokens_in_db(user_id, guild_id, access_token, refresh_token, expires_in):
    conn = get_db_connection()
    cursor = conn.cursor()
    token_expires_at = (datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)).isoformat()
    cursor.execute("""
        UPDATE verified_users SET access_token = ?, refresh_token = ?, token_expires_at = ?
        WHERE user_id = ? AND guild_id = ?
    """, (access_token, refresh_token, token_expires_at, user_id, guild_id))
    conn.commit()
    conn.close()

def log_to_discord_channel(guild_id, message=None, embed_data=None):
    settings = get_guild_settings_web(guild_id)
    if not settings or not settings['log_channel_id']:
        return
    log_channel_id = settings['log_channel_id']
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {}
    if message:
        payload['content'] = message
    if embed_data:
        payload['embeds'] = [embed_data]
    if payload:
        try:
            requests.post(f"{DISCORD_API_BASE}/channels/{log_channel_id}/messages", json=payload, headers=headers)
        except:
            pass

def add_role_to_member_api(guild_id, user_id, role_id):
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.put(f"{DISCORD_API_BASE}/guilds/{guild_id}/members/{user_id}/roles/{role_id}", headers=headers)
        return response.status_code
    except:
        return 500

def refresh_access_token(refresh_token):
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(f"{DISCORD_API_BASE}/oauth2/token", data=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except:
        return None

def add_user_to_guild(guild_id, user_id, user_access_token):
    add_member_data = {'access_token': user_access_token}
    add_member_headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.put(
            f"{DISCORD_API_BASE}/guilds/{guild_id}/members/{user_id}",
            json=add_member_data,
            headers=add_member_headers
        )
        response.raise_for_status()
        return True, response.status_code
    except:
        return False, 500

@app.route("/")
def index():
    return "Link Restore Bot 웹 서비스입니다."

@app.route("/verify")
def start_verify_auth():
    guild_id = request.args.get('guild_id')
    if not guild_id:
        return "길드 ID가 필요합니다.", 400
    session['guild_id'] = guild_id
    log_to_discord_channel(guild_id, f"유저가 웹 인증을 시도했습니다. (길드 ID: {guild_id})")
    scope = "identify guilds.join"
    discord_login_url = f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI_VERIFY}&response_type=code&scope={scope}"
    return redirect(discord_login_url)

@app.route("/callback_verify")
def callback_verify():
    code = request.args.get("code")
    if not code:
        return "인증 코드가 없습니다.", 400

    token_response = requests.post(f"{DISCORD_API_BASE}/oauth2/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI_VERIFY,
        "scope": "identify guilds.join"
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})

    token_json = token_response.json()
    access_token = token_json.get('access_token')
    refresh_token = token_json.get('refresh_token')
    expires_in = token_json.get('expires_in')

    if not access_token:
        log_to_discord_channel(session.get('guild_id'), f"OAuth 토큰 획득 실패: {token_json}")
        return "OAuth 토큰 획득 실패", 500

    user_response = requests.get(f"{DISCORD_API_BASE}/users/@me", headers={'Authorization': f'Bearer {access_token}'})
    user_data = user_response.json()
    user_id = user_data.get('id')
    username = user_data.get('username', '알 수 없는 유저')

    if not user_id:
        log_to_discord_channel(session.get('guild_id'), f"유저 정보 획득 실패: {user_data}")
        return "유저 정보 획득 실패", 500

    guild_id = session.pop('guild_id', None)
    if not guild_id:
        return "길드 정보가 없습니다.", 400

    settings = get_guild_settings_web(guild_id)
    if not settings:
        log_to_discord_channel(guild_id, f"{username}({user_id})님이 웹 인증 시도했으나 설정이 올바르지 않습니다.")
        return "서버 설정이 올바르지 않습니다.", 500

    # 필터링(부계정, VPN) 등 필요한 로직 넣기 가능

    added, status = add_user_to_guild(guild_id, user_id, access_token)
    if not added:
        log_to_discord_channel(guild_id, f"{username}({user_id}) 서버 참여 실패 (상태: {status})")
        return "서버 참여 실패", 500

    if settings['verified_role_id']:
        role_status = add_role_to_member_api(guild_id, user_id, settings['verified_role_id'])
        if role_status not in [201, 204]:
            log_to_discord_channel(guild_id, f"{username}({user_id}) 역할 부여 실패 (상태: {role_status})")

    record_verified_user(user_id, guild_id, username, access_token, refresh_token, expires_in)

    log_embed = {
        "title": username,
        "description": "웹 인증 완료 및 서버 참여 성공",
        "color": 0,
        "footer": {"text": f"유저 ID = {user_id}\n인증한 시간 = {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"}
    }
    log_to_discord_channel(guild_id, embed_data=log_embed)

    return render_template_string(f"""
        <h1>인증 및 서버 참여 성공</h1>
        <p>{username}님, 서버에 성공적으로 참여하고 인증 완료되었습니다.</p>
        <p>디스코드 앱으로 돌아가서 확인하세요.</p>
    """)

@app.route("/force_join_all", methods=["POST"])
def force_join_all():
    data = request.get_json()
    guild_id = data.get('guild_id')

    if not guild_id:
        return jsonify({"error": "guild_id 필요"}), 400

    users = get_verified_users_for_guild(guild_id)
    results = []

    for user in users:
        user_id = user['user_id']
        username = user['username']
        result = {"user_id": user_id, "username": username, "success": False, "message": ""}
        access_token = user['access_token']
        refresh_token = user['refresh_token']
        token_expires_at = datetime.datetime.fromisoformat(user['token_expires_at'])
        now = datetime.datetime.utcnow()

        if now >= token_expires_at:
            refreshed = refresh_access_token(refresh_token)
            if not refreshed:
                result["message"] = "만료 토큰 갱신 실패, 재인증 필요"
                results.append(result)
                continue
            access_token = refreshed['access_token']
            refresh_token = refreshed.get('refresh_token', refresh_token)
            expires_in = refreshed['expires_in']
            update_user_tokens_in_db(user_id, guild_id, access_token, refresh_token, expires_in)

        added, status = add_user_to_guild(guild_id, user_id, access_token)
        if not added:
            result["message"] = f"서버 추가 실패 (상태 {status})"
            results.append(result)
            continue

        settings = get_guild_settings_web(guild_id)
        if settings and settings['verified_role_id']:
            role_status = add_role_to_member_api(guild_id, user_id, settings['verified_role_id'])
            if role_status not in [201, 204]:
                result["message"] = f"서버 추가 성공, 역할 추가 실패 (상태 {role_status})"
                results.append(result)
                continue

        result["success"] = True
        result["message"] = "성공적으로 서버에 추가됨"
        results.append(result)

    return jsonify({"results": results}), 200

if __name__ == "__main__":
    init_db_web()
    app.run(debug=True, port=5000)
