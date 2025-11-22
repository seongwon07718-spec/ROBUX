# web_app.py
# Flask 앱: OAuth2 콜백 및 토큰 저장, 즉시 add_user 시도
from flask import Flask, request, redirect, render_template_string
import requests, sqlite3, uuid, time
from urllib.parse import quote_plus
import os

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())

# ----------------- 설정 (테스트용: 실제 값으로 변경하세요) -----------------
BOT_TOKEN = "여기에_BOT_TOKEN_입력"
CLIENT_ID = "1434868431064272907"
CLIENT_SECRET = "여기에_CLIENT_SECRET_입력"
API_ENDPOINT = "https://discord.com/api/v9"
# REDIRECT_URI는 Discord 개발자 포털에 등록한 값과 정확히 일치해야 합니다.
REDIRECT_URI = "https://btcclink.duckdns.org/join"
# 웹에서 생성되는 인증 링크의 기본 URL
BASE_URL = "https://btcclink.duckdns.org"
DB_PATH = "database.db"
STATE_EXPIRY_SECONDS = 600
# ----------------------------------------------------------------

SUCCESS_HTML = "<h2>인증 성공</h2><p>인증이 완료되었습니다. 잠시 후 처리됩니다.</p>"
FAIL_HTML = "<h2>실패</h2><p>인증 중 오류가 발생했습니다.</p>"

def start_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    return con, cur

def ensure_schema():
    con, cur = start_db()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guilds (
        id INTEGER PRIMARY KEY,
        token TEXT UNIQUE,
        expiredate TEXT,
        link TEXT,
        icon TEXT
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        token TEXT,
        guild_id INTEGER
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS licenses (
        key TEXT PRIMARY KEY,
        days INTEGER
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guild_settings (
        guild_id INTEGER PRIMARY KEY,
        log_channel_id INTEGER,
        auth_role_id INTEGER
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS state_nonce (
        state TEXT PRIMARY KEY,
        guild_id INTEGER,
        created_at INTEGER
    );""")
    con.commit()
    con.close()

def make_oauth_url(guild_id):
    nonce = uuid.uuid4().hex
    state = f"{guild_id}:{nonce}"
    con, cur = start_db()
    cur.execute("INSERT OR REPLACE INTO state_nonce (state, guild_id, created_at) VALUES (?, ?, ?);", (state, guild_id, int(time.time())))
    con.commit()
    con.close()
    scope = quote_plus("identify guilds.join")
    oauth_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={scope}&state={state}"
    return oauth_url

def exchange_code(code):
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = requests.post(f"{API_ENDPOINT}/oauth2/token", data=data, headers=headers, timeout=10)
    try:
        return r.json()
    except Exception:
        return None

def get_user_profile(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        r = requests.get(f"{API_ENDPOINT}/users/@me", headers=headers, timeout=10)
        if r.status_code != 200:
            print("get_user_profile failed:", r.status_code, r.text)
            return None
        return r.json()
    except Exception as e:
        print("get_user_profile exception:", e)
        return None

def add_user(access_token, guild_id, user_id):
    jsonData = {"access_token": access_token}
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    try:
        r = requests.put(f"{API_ENDPOINT}/guilds/{guild_id}/members/{user_id}", json=jsonData, headers=headers, timeout=10)
        if r.status_code in (201, 204):
            return True
        elif r.status_code == 429:
            info = r.json()
            retry = info.get("retry_after", 1)
            time.sleep(retry + 1)
            return add_user(access_token, guild_id, user_id)
        else:
            print("add_user failed:", r.status_code, r.text)
            return False
    except Exception as e:
        print("add_user exception:", e)
        return False

@app.route("/login/<int:guild_id>")
def login(guild_id):
    oauth_url = make_oauth_url(guild_id)
    return redirect(oauth_url)

@app.route("/join", methods=["GET"])
def join():
    code = request.args.get("code")
    state = request.args.get("state")
    if not code or not state:
        return FAIL_HTML, 400

    con, cur = start_db()
    cur.execute("SELECT guild_id, created_at FROM state_nonce WHERE state == ?;", (state,))
    row = cur.fetchone()
    if not row:
        con.close()
        return FAIL_HTML, 400
    guild_id_db, created_at = row
    con.close()
    if int(time.time()) - created_at > STATE_EXPIRY_SECONDS:
        return "<h2>만료된 인증 요청입니다.</h2>", 400

    token_resp = exchange_code(code)
    if not token_resp or "access_token" not in token_resp:
        print("token exchange failed:", token_resp)
        return FAIL_HTML, 500

    access_token = token_resp.get("access_token")
    refresh_token = token_resp.get("refresh_token")
    user = get_user_profile(access_token)
    if not user:
        return FAIL_HTML, 500

    user_id = user.get("id")
    guild_id = guild_id_db

    try:
        con, cur = start_db()
        cur.execute("INSERT OR REPLACE INTO users (id, token, guild_id) VALUES (?, ?, ?);", (str(user_id), refresh_token, guild_id))
        con.commit()
        con.close()
    except Exception as e:
        print("DB save error:", e)

    added = add_user(access_token, guild_id, user_id)
    if added:
        print(f"User {user_id} added to guild {guild_id}")
    else:
        print(f"User {user_id} add attempt failed; saved for later recovery")

    return render_template_string(SUCCESS_HTML)

@app.route("/<link>")
def public_link(link):
    try:
        con, cur = start_db()
        cur.execute("SELECT id FROM guilds WHERE link == ?;", (link,))
        row = cur.fetchone()
        con.close()
        if not row:
            return "<h2>404</h2><p>링크가 없습니다.</p>", 404
        gid = row[0]
        page = f"""
        <h2>서버 링크 복구</h2>
        <p>서버ID: {gid}</p>
        <a href="{BASE_URL}/login/{gid}">Discord로 인증(초대)하기</a>
        """
        return render_template_string(page)
    except Exception as e:
        print("public_link exception:", e)
        return "<h2>오류</h2>", 500

if __name__ == "__main__":
    ensure_schema()
    # 운영 시에는 443(https)로 리버스 프록시를 권장
    app.run(host="0.0.0.0", port=5000, debug=False)
