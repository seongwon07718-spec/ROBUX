# web.py - 수정된 최종본
import requests
from flask import Flask, request, render_template, redirect
import uuid
import sqlite3
import datetime
from json import JSONDecodeError

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())

# -----------------------------
# 여기 값들을 실제 값으로 바꿔주세요.
# 가능하면 .env로 관리하세요.
# -----------------------------
API_ENDPOINT = 'https://discord.com/api/v9'
CLIENT_ID = "1434868431064272907"  # Discord OAuth2 Client ID
CLIENT_SECRET = "여기에_CLIENT_SECRET을_넣으세요"
BOT_TOKEN = "여기에_BOT_TOKEN을_넣으세요"
# redirect_uri는 Discord 개발자 포털에 등록된 값과 정확히 일치해야 합니다.
# 예: https://your-domain.com/join 또는 http://localhost/join
REDIRECT_URI = "https://your-domain.com/join"
# -----------------------------

def start_db():
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    return con, cur

def geticon_url(guild_id):
    con, cur = start_db()
    cur.execute("SELECT icon FROM guilds WHERE id == ?", (guild_id,))
    row = cur.fetchone()
    con.close()
    if not row or not row[0]:
        return None
    icon_hash = row[0]
    return f'https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.png'

def get_user_profile(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        res = requests.get(f"{API_ENDPOINT}/users/@me", headers=headers, timeout=10)
        if res.status_code != 200:
            print("get_user_profile 실패:", res.status_code, res.text)
            return False
        return res.json()
    except Exception as e:
        print("get_user_profile 예외:", e)
        return False

def get_kr_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

def get_ip():
    return request.headers.get("CF-Connecting-IP", request.remote_addr)

def get_agent():
    return request.user_agent.string

def getguild(guild_id):
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    try:
        r = requests.get(f'{API_ENDPOINT}/guilds/{guild_id}', headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            print("getguild 실패:", r.status_code, r.text)
            return None
    except Exception as e:
        print("getguild 예외:", e)
        return None

def add_user(access_token, user_id, guild_id):
    json_data = {"access_token": access_token}
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    while True:
        try:
            r = requests.put(f'{API_ENDPOINT}/guilds/{guild_id}/members/{user_id}', json=json_data, headers=headers, timeout=10)
        except Exception as e:
            print("add_user 요청 예외:", e)
            return False

        if r.status_code == 429:
            # rate limit: 대기 후 재시도
            try:
                info = r.json()
                retry = info.get("retry_after", 1)
            except Exception:
                retry = 2
            print("rate limited, retry after", retry)
            import time
            time.sleep(retry + 1)
            continue

        # 201(추가됨), 204(성공/갱신됨) 등 처리
        if r.status_code in (201, 204):
            return True
        else:
            try:
                print("add_user 실패 응답:", r.status_code, r.json())
            except Exception:
                print("add_user 실패 응답 텍스트:", r.text)
            return False

def exchange_code(code):
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    try:
        r = requests.post(f"{API_ENDPOINT}/oauth2/token", data=data, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        print("exchange_code 예외:", e)
        return None

def get_guild_with_counts(guild_id):
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    try:
        r = requests.get(f'{API_ENDPOINT}/guilds/{guild_id}?with_counts=true', headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            print("get_guild_with_counts 실패:", r.status_code, r.text)
            return None
    except Exception as e:
        print("get_guild_with_counts 예외:", e)
        return None

@app.route('/<link>', methods=['GET'])
def join_page(link):
    try:
        con, cur = start_db()
        cur.execute("SELECT id FROM guilds WHERE link == ?", (link,))
        row = cur.fetchone()
        con.close()
        if not row:
            return render_template("fail.html"), 404

        gid = row[0]
        ginfo = getguild(gid)
        r = get_guild_with_counts(gid)
        # 안전하게 템플릿에 전달
        icon_url = ginfo.get('icon') if isinstance(ginfo, dict) else None
        member_count = r.get('approximate_member_count') if isinstance(r, dict) else None
        return render_template("s.html", link=link, id=gid, info=ginfo, icon=icon_url, member=member_count)
    except Exception as e:
        print("join_page 예외:", e)
        return render_template("fail.html"), 500

@app.route('/join', methods=['GET'])
def callback():
    code = request.args.get('code')
    state = request.args.get('state')  # state에 guild_id 등을 담아 보냈다면 그 값을 사용
    if not code or not state:
        return render_template("fail.html"), 400

    token_resp = exchange_code(code)
    if not token_resp or "access_token" not in token_resp:
        print("토큰 교환 실패:", token_resp)
        return render_template("fail.html"), 500

    access_token = token_resp.get('access_token')
    refresh_token = token_resp.get('refresh_token')

    user_data = get_user_profile(access_token)
    if not user_data:
        return render_template("fail.html"), 500

    # state가 guild id라 가정
    try:
        guild_id = int(state)
    except:
        return render_template("fail.html"), 400

    # 서버 정보 확인(선택적)
    guild_info = getguild(guild_id)
    # 멤버 추가 시도
    added = add_user(access_token, user_data['id'], guild_id)
    if not added:
        # 실패 시에도 DB 저장은 상황에 따라 다름. 여기서는 실패 로그만
        print("멤버 추가 실패:", user_data['id'], guild_id)

    # DB에 users 저장 (user_id, refresh_token, guild_id)
    try:
        con, cur = start_db()
        cur.execute("INSERT INTO users (id, token, guild_id) VALUES (?, ?, ?);", (str(user_data["id"]), refresh_token, guild_id))
        con.commit()
        con.close()
    except Exception as e:
        print("DB 저장 중 예외:", e)

    return render_template("success.html")

if __name__ == "__main__":
    # production 환경에서는 debug=False, 포트·호스트는 배포 환경에 맞게 설정하세요.
    app.run(debug=False, host='0.0.0.0', port=80)
