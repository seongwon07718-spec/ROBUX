from flask import Flask, redirect, request, session, render_template_string, jsonify
import requests
import os
from dotenv import load_dotenv
import sqlite3
import datetime
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# --- Discord OAuth2 설정 ---
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
# 반드시 Discord 개발자 포털에 등록된 "Redirect URI"와 일치해야 합니다!
REDIRECT_URI_VERIFY = os.getenv("WEB_BASE_URL", "http://localhost:5000") + "/callback_verify"

DISCORD_API_BASE = "https://discord.com/api/v10"
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN") 

# --- SQLite 유틸리티 함수 (웹 서버용) ---
def get_db_connection():
    conn = sqlite3.connect('bot_data.db')
    conn.row_factory = sqlite3.Row
    return conn

# DB 테이블 초기화 (필요한 테이블이 없으면 생성)
def init_db_web():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS joined_users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            joined_at TEXT,
            invite_code TEXT,
            invite_uses INTEGER,
            guild_id INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            log_channel_id INTEGER,
            verified_role_id INTEGER,
            allow_alt_accounts BOOLEAN DEFAULT 0,
            allow_vpn BOOLEAN DEFAULT 0,
            embed_title TEXT DEFAULT '서버 인증 안내',
            embed_description TEXT DEFAULT '서버의 모든 기능을 사용하려면 아래 버튼을 눌러 인증을 완료해주세요.'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verified_users (
            user_id INTEGER PRIMARY KEY,
            guild_id INTEGER,
            username TEXT,
            verified_at TEXT,
            is_alt_account BOOLEAN DEFAULT 0,
            is_vpn_user BOOLEAN DEFAULT 0,
            access_token TEXT,
            refresh_token TEXT,
            token_expires_at TEXT,
            FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id)
        )
    """)
    conn.commit()
    conn.close()

# 길드 설정 조회
def get_guild_settings_web(guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,))
    settings = cursor.fetchone()
    conn.close()
    return settings

# 웹 인증 성공 시 유저 정보 및 토큰 저장/업데이트
def record_verified_user(user_id, guild_id, username, access_token, refresh_token, expires_in, is_alt_account=False, is_vpn_user=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    verified_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    token_expires_at = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in)).isoformat()
    cursor.execute("""
        INSERT OR REPLACE INTO verified_users 
        (user_id, guild_id, username, verified_at, is_alt_account, is_vpn_user, access_token, refresh_token, token_expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, guild_id, username, verified_at, is_alt_account, is_vpn_user, access_token, refresh_token, token_expires_at))
    conn.commit()
    conn.close()

# 특정 길드의 모든 웹 인증 유저 정보 조회
def get_verified_users_for_guild(guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, access_token, refresh_token, token_expires_at FROM verified_users WHERE guild_id = ?", (guild_id,))
    users = cursor.fetchall()
    conn.close()
    return users

# 유저 토큰 정보 업데이트
def update_user_tokens_in_db(user_id, guild_id, access_token, refresh_token, expires_in):
    conn = get_db_connection()
    cursor = conn.cursor()
    token_expires_at = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in)).isoformat()
    cursor.execute("""
        UPDATE verified_users SET access_token = ?, refresh_token = ?, token_expires_at = ?
        WHERE user_id = ? AND guild_id = ?
    """, (access_token, refresh_token, token_expires_at, user_id, guild_id))
    conn.commit()
    conn.close()

# 로그 채널에 메시지 전송 (텍스트 또는 임베드)
def log_to_discord_channel(guild_id, message=None, embed_data=None):
    settings = get_guild_settings_web(guild_id)
    if not settings or not settings["log_channel_id"]:
        return

    log_channel_id = settings["log_channel_id"]
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {}
    if message:
        payload["content"] = message
    if embed_data:
        payload["embeds"] = [embed_data] # 임베드 데이터는 리스트 형태로

    if payload:
        try:
            requests.post(f"{DISCORD_API_BASE}/channels/{log_channel_id}/messages", json=payload, headers=headers)
        except requests.exceptions.RequestException as e:
            print(f"Failed to send log to Discord channel {log_channel_id}: {e}")

# 멤버에게 역할 부여
def add_role_to_member_api(guild_id, user_id, role_id):
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.put(f"{DISCORD_API_BASE}/guilds/{guild_id}/members/{user_id}/roles/{role_id}", headers=headers)
        return response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Failed to add role {role_id} to member {user_id}: {e}")
        return 500

# OAuth2 토큰 갱신
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
    except requests.exceptions.RequestException as e:
        print(f"Error refreshing token: {e}")
        return None

# 유저를 서버에 추가
def add_user_to_guild(guild_id, user_id, user_access_token):
    add_member_data = {"access_token": user_access_token}
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
    except requests.exceptions.RequestException as e:
        print(f"Failed to add user {user_id} to guild {guild_id}: {e.response.text if e.response else e}")
        return False, e.response.status_code if e.response else 500


# --- 웹 페이지 (시작점) ---
@app.route("/")
def index():
    return render_template_string("""
        <h1>Link Restore Bot 웹 서비스</h1>
        <p>환영합니다! 이 서비스는 Discord 서버 인증 및 복구 기능을 제공합니다.</p>
        <p>Discord 봇에서 제공된 링크를 통해 접속해주세요.</p>
    """)


# --- 일반 인증 흐름 시작 (/인증버튼 용) ---
@app.route("/verify")
def start_verify_auth():
    guild_id = request.args.get('guild_id')
    if not guild_id:
        return "길드 ID가 필요합니다.", 400
    
    session['guild_id'] = guild_id # 세션에 길드 ID 저장
    
    # 이 시점에서 유저가 인증을 시도했다고 간주하고 로그 남김 (username은 아직 모름)
    log_to_discord_channel(guild_id, f"유저가 웹 인증을 시도했습니다. (길드 ID: {guild_id})")

    scope = "identify guilds.join" # 필요한 스코프

    discord_login_url = (
        f"https://discord.com/oauth2/authorize?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI_VERIFY}&"
        f"response_type=code&"
        f"scope={scope}"
    )
    return redirect(discord_login_url)


# --- 일반 인증 콜백 (/인증버튼 용) ---
@app.route("/callback_verify")
def callback_verify():
    code = request.args.get("code")
    if not code:
        return "인증 코드 수신 실패", 400

    token_response = requests.post(f"{DISCORD_API_BASE}/oauth2/token", data={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "authorization_code",
        "code": code, "redirect_uri": REDIRECT_URI_VERIFY, "scope": "identify guilds.join"
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    
    token_json = token_response.json()
    access_token = token_json.get("access_token")
    refresh_token = token_json.get("refresh_token")
    expires_in = token_json.get("expires_in") # access_token 유효 시간 (초)
    
    if not access_token:
        log_to_discord_channel(session.get('guild_id'), f"Discord OAuth2 토큰 획득 실패: {token_json}")
        return "액세스 토큰 획득 실패", 500

    user_response = requests.get(f"{DISCORD_API_BASE}/users/@me", headers={"Authorization": f"Bearer {access_token}"})
    user_data = user_response.json()
    user_id = user_data.get("id")
    username = user_data.get("username", "알 수 없는 유저") # 유저 이름 획득

    if not user_id:
        log_to_discord_channel(session.get('guild_id'), f"Discord 유저 정보 획득 실패: {user_data}")
        return "유저 정보 획득 실패", 500

    guild_id = session.pop('guild_id', None) # 세션에서 길드 ID 가져오기
    if not guild_id:
        return "세션에서 길드 ID를 찾을 수 없습니다.", 400

    settings = get_guild_settings_web(guild_id)
    if not settings:
        log_to_discord_channel(guild_id, f"{username}({user_id})님이 웹 인증 시도했으나 서버 설정이 올바르지 않습니다.")
        return "서버 설정이 올바르지 않습니다. 관리자에게 문의해주세요.", 500

    # --- 1. 필터링 로직 ---
    is_alt_account = False
    is_vpn_user = False

    if not settings["allow_alt_accounts"]:
        user_created_at_str = user_data.get('created_at')
        if user_created_at_str:
            user_created_at = datetime.datetime.fromisoformat(user_created_at_str.replace('Z', '+00:00'))
            current_time = datetime.datetime.now(datetime.timezone.utc)
            account_age = current_time - user_created_at
            
            account_age_threshold_days = 7
            if account_age.days < account_age_threshold_days:
                log_to_discord_channel(guild_id, f"{username}({user_id})님 부계정 필터링으로 인증 실패 (생성일: {user_created_at.date()})")
                return render_template_string(f"<h1>인증 실패!</h1><p>{username}님, 계정 생성일이 너무 짧습니다. 부계정 정책에 따라 인증이 어렵습니다.</p><p>자세한 내용은 디스코드 서버에서 확인해주세요.</p>")

    if not settings["allow_vpn"]:
        # VPN 필터링 로직은 외부 IP API 연동이 필요하며, 웹 서버에서 클라이언트 IP를 받아 처리해야 합니다.
        pass # 현재 구현은 생략됨

    # --- 2. 유저를 서버에 추가 ---
    added_to_guild, status_code = add_user_to_guild(guild_id, user_id, access_token)
    if not added_to_guild:
        log_to_discord_channel(guild_id, f"{username}({user_id})님 서버 자동 참여 실패 (상태코드: {status_code}).")
        if status_code == 403: # Discord API 403 Forbidden - 권한 부족
             return render_template_string(f"<h1>서버 참여 실패!</h1><p>{username}님, 서버에 참여할 권한이 없거나, 이미 차단되었을 수 있습니다.</p><p>자세한 내용은 디스코드 서버 관리자에게 문의해주세요.</p>")
        return "서버 참여 실패", 500

    # --- 3. 인증 역할 부여 및 DB 기록 ---
    if settings["verified_role_id"]:
        role_status_code = add_role_to_member_api(guild_id, user_id, settings["verified_role_id"])
        if role_status_code not in [201, 204]: # 201 Created, 204 No Content - 성공
            log_to_discord_channel(guild_id, f"{username}({user_id})님 역할 부여 실패 (상태코드: {role_status_code}). 봇 권한 확인.")
            
    # DB에 웹 인증 유저 정보 및 토큰 저장/업데이트
    record_verified_user(user_id, guild_id, username, access_token, refresh_token, expires_in, is_alt_account, is_vpn_user)

    # 인증 로그 임베드 메시지 생성 및 전송
    log_embed = {
        "title": username,
        "description": "웹 인증 완료 및 서버 참여 성공",
        "color": 0, # 검정색 (Discord API는 10진수 색상 코드를 사용)
        "footer": {
            "text": f"유저 ID = {user_id}\n인증한 시간 = {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        }
    }
    log_to_discord_channel(guild_id, embed_data=log_embed)

    return render_template_string(f"""
        <h1>인증 및 서버 참여 성공!</h1>
        <p>{username}님, 성공적으로 서버에 참여 및 인증되었습니다.</p>
        <p>Discord 클라이언트로 돌아가 서버를 확인해주세요.</p>
        <p>브라우저를 닫으셔도 좋습니다.</p>
    """)


# --- `/복구` 명령어 처리 엔드포인트 --- (봇이 이 엔드포인트를 호출)
@app.route("/force_join_all", methods=["POST"])
def force_join_all_users_endpoint():
    data = request.get_json()
    guild_id = data.get("guild_id")
    
    if not guild_id:
        return jsonify({"error": "guild_id가 필요합니다."}), 400

    users_to_process = get_verified_users_for_guild(guild_id) # 해당 길드의 모든 웹 인증 유저 조회
    
    if not users_to_process:
        return jsonify({"results": [], "message": "복구 가능한 유저가 없습니다."}), 200

    results = []

    for user_info in users_to_process:
        user_id = user_info["user_id"]
        username = user_info["username"] # DB에서 username 사용

        result = {
            "user_id": user_id,
            "username": username,
            "success": False,
            "message": "초기화됨"
        }

        access_token = user_info["access_token"]
        refresh_token = user_info["refresh_token"]
        token_expires_at_str = user_info["token_expires_at"]

        token_expires_at = datetime.datetime.fromisoformat(token_expires_at_str)
        current_time = datetime.datetime.now(datetime.timezone.utc)

        # 토큰 만료 여부 확인 및 갱신
        if current_time >= token_expires_at:
            refreshed_tokens = refresh_access_token(refresh_token)
            if not refreshed_tokens:
                result["message"] = "만료된 토큰 갱신 실패. 유저에게 재인증 요청 필요."
                results.append(result)
                log_to_discord_channel(guild_id, f"유저 {user_id} ({username}) 토큰 갱신 실패: {result['message']}")
                continue
            
            access_token = refreshed_tokens["access_token"]
            refresh_token = refreshed_tokens.get("refresh_token", refresh_token) # refresh_token도 갱신될 수 있음
            expires_in = refreshed_tokens["expires_in"]
            update_user_tokens_in_db(user_id, guild_id, access_token, refresh_token, expires_in)
            
            log_to_discord_channel(guild_id, f"유저 {user_id} ({username}) OAuth2 토큰 갱신 성공.")


        # 유저를 서버에 추가
        added_to_guild, status_code = add_user_to_guild(guild_id, user_id, access_token)
        if not added_to_guild:
            error_msg = f"유저를 서버에 추가하는 데 실패 (Discord API 응답 코드: {status_code})."
            if status_code == 403:
                error_msg += " 봇에 권한이 없거나 유저가 서버에서 차단되었을 수 있습니다."
            result["message"] = error_msg
            results.append(result)
            log_to_discord_channel(guild_id, f"유저 {user_id} ({username}) 서버 참여 실패: {error_msg}")
            continue
        
        # 역할 부여 (인증 역할)
        settings = get_guild_settings_web(guild_id)
        if settings and settings["verified_role_id"]:
            role_status_code = add_role_to_member_api(guild_id, user_id, settings["verified_role_id"])
            if role_status_code not in [201, 204]: # 역할이 성공적으로 부여됨
                result["message"] = f"서버에 참여했으나 역할 부여에 실패 (코드: {role_status_code}). 봇 권한 확인."
                results.append(result)
                log_to_discord_channel(guild_id, f"유저 {user_id} ({username}) 역할 부여 실패: {result['message']}")
                continue
        
        result["success"] = True
        result["message"] = "서버에 성공적으로 참여했습니다."
        results.append(result)
        log_to_discord_channel(guild_id, f"유저 {user_id} ({username}) 서버 강제 참여 및 역할 부여 성공.")

    return jsonify({"results": results}), 200


if __name__ == "__main__":
    if not CLIENT_ID or not CLIENT_SECRET or not BOT_TOKEN or not app.secret_key:
        print("필수 환경 변수(CLIENT_ID, CLIENT_SECRET, BOT_TOKEN, FLASK_SECRET_KEY)를 모두 설정해주세요.")
        exit(1)
    
    init_db_web() # 웹 서버 시작 시 DB 초기화 (봇과 같은 DB 파일을 공유해야 함)

    # 실제 배포 시 debug=False로 변경하고, 적절한 웹 서버 (Gunicorn, uWSGI)로 실행해야 합니다.
    app.run(debug=True, port=5000)
