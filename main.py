import os, json, sqlite3, hashlib, secrets, requests
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import Flask, request, jsonify, session, send_from_directory, redirect
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key                 = os.environ["SECRET_KEY"]
app.permanent_session_lifetime = timedelta(days=7)
CORS(app, supports_credentials=True)

DISCORD_CLIENT_ID     = os.environ["DISCORD_CLIENT_ID"]
DISCORD_CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
DISCORD_REDIRECT_URI  = os.environ.get("DISCORD_REDIRECT_URI", "http://localhost:5000/auth/discord/callback")
DISCORD_WEBHOOK_URL   = os.environ.get("DISCORD_WEBHOOK_URL", "")

DB_PATH   = "sailormarket.db"
JSON_PATH = "user_id_pw.json"

# ─────────────────────────────────────────────
# DB
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                email          TEXT,
                password       TEXT,
                discord_id     TEXT,
                discord_name   TEXT,
                discord_avatar TEXT,
                ip             TEXT,
                is_admin       INTEGER DEFAULT 0,
                created_at     TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        # 마이그레이션
        cols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
        for col, sql in {
            "discord_id":     "ALTER TABLE users ADD COLUMN discord_id TEXT",
            "discord_name":   "ALTER TABLE users ADD COLUMN discord_name TEXT",
            "discord_avatar": "ALTER TABLE users ADD COLUMN discord_avatar TEXT",
            "ip":             "ALTER TABLE users ADD COLUMN ip TEXT",
            "is_admin":       "ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0",
        }.items():
            if col not in cols:
                conn.execute(sql)
        conn.commit()
    print("[DB] 초기화 완료")

# ─────────────────────────────────────────────
# 비밀번호
# ─────────────────────────────────────────────
def hash_pw(pw):
    salt = secrets.token_hex(16)
    return salt + ":" + hashlib.sha256((salt + pw).encode()).hexdigest()

def check_pw(pw, stored):
    try:
        salt, h = stored.split(":")
        return hashlib.sha256((salt + pw).encode()).hexdigest() == h
    except:
        return False

# ─────────────────────────────────────────────
# 세션
# ─────────────────────────────────────────────
def set_session(user):
    session.permanent  = True
    session["user_id"] = user["id"]
    session["email"]   = user["email"] or user["discord_name"] or "유저"
    session["is_admin"]= bool(user["is_admin"])

def login_required(f):
    @wraps(f)
    def d(*a, **k):
        if "user_id" not in session:
            return jsonify({"message": "로그인이 필요합니다."}), 401
        return f(*a, **k)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a, **k):
        if "user_id" not in session:
            return jsonify({"message": "로그인이 필요합니다."}), 401
        if not session.get("is_admin"):
            return jsonify({"message": "관리자 권한이 필요합니다."}), 403
        return f(*a, **k)
    return d

# ─────────────────────────────────────────────
# IP 가져오기
# ─────────────────────────────────────────────
def get_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()

# ─────────────────────────────────────────────
# 중복/다계정 체크
# ─────────────────────────────────────────────
def check_duplicate(email: str, ip: str):
    """
    중복 가입 방지:
    1. 이메일 중복
    2. 같은 IP로 이미 계정 있음 (다계정 방지)
    """
    with get_db() as conn:
        # 이메일 중복
        if email:
            row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if row:
                return "이미 가입된 이메일입니다."
        # IP 다계정
        if ip:
            row = conn.execute("SELECT id FROM users WHERE ip = ?", (ip,)).fetchone()
            if row:
                return "이미 해당 네트워크에서 가입된 계정이 있습니다."
    return None  # 통과

# ─────────────────────────────────────────────
# JSON 저장
# ─────────────────────────────────────────────
def save_to_json(email: str, pw_raw: str, method: str, discord_name: str = ""):
    data = []
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = []

    # 중복 스킵
    if any(u.get("email") == email for u in data):
        return

    data.append({
        "email":        email,
        "password":     hash_pw(pw_raw) if pw_raw else "(Discord)",
        "method":       method,
        "discord_name": discord_name,
        "created_at":   datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    })
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────
# 웹훅 알림 (Components V2 — flags:32)
# ─────────────────────────────────────────────
def send_webhook(email: str, method: str, discord_name: str = ""):
    if not DISCORD_WEBHOOK_URL:
        print("[웹훅] URL 미설정 — 알림 스킵")
        return

    now     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    account = discord_name if discord_name else email

    payload = {
        "flags": 32,
        "components": [{
            "type": 17,
            "accent_color": 0x5865F2,
            "components": [
                {"type": 10, "content": "### 🎉 새 회원 가입\n-# SailorMarket"},
                {"type": 14, "divider": True, "spacing": 1},
                {"type": 10, "content": (
                    f"-# **계정** : {account}\n"
                    f"-# **이메일** : {email or '*(Discord 전용)*'}\n"
                    f"-# **가입 방식** : {method}\n"
                    f"-# **가입 시각** : {now}"
                )},
                {"type": 14, "divider": True, "spacing": 1},
                {"type": 9, "components": [{
                    "type": 2, "style": 5,
                    "label": "관리자 대시보드",
                    "url": "https://sailor-piece.shop/admin/dashboard"
                }]}
            ]
        }]
    }

    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5, params={"wait": "true"})
        print(f"[웹훅] {r.status_code}")
        if not r.ok:
            print(f"[웹훅] 오류: {r.text[:300]}")
    except Exception as e:
        print(f"[웹훅] 전송 실패: {e}")

# ─────────────────────────────────────────────
# 페이지
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return f"<h2>👋 {session['email']} 님!</h2><a href='/api/auth/logout'>로그아웃</a>"

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    return f"<h2>🔐 관리자 대시보드</h2><p>{session['email']}</p><a href='/api/auth/logout'>로그아웃</a>"

# ─────────────────────────────────────────────
# 이메일 회원가입
# ─────────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data     = request.get_json() or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    ip       = get_ip()

    if not email or not password:
        return jsonify({"message": "이메일과 비밀번호를 입력하세요."}), 400
    if len(password) < 8:
        return jsonify({"message": "비밀번호는 8자 이상이어야 합니다."}), 400

    # 중복 / 다계정 체크
    err = check_duplicate(email, ip)
    if err:
        print(f"[가입 거절] {email} / IP:{ip} → {err}")
        return jsonify({"message": err}), 409

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (email, password, ip) VALUES (?,?,?)",
                (email, hash_pw(password), ip)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"message": "이미 가입된 이메일입니다."}), 409

    save_to_json(email, password, "이메일")
    send_webhook(email, "이메일 가입")
    print(f"[가입 완료] {email} / IP:{ip}")
    return jsonify({"message": "회원가입 완료"})

# ─────────────────────────────────────────────
# 이메일 로그인
# ─────────────────────────────────────────────
@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data     = request.get_json() or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"message": "이메일과 비밀번호를 입력하세요."}), 400

    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

    if not user or not user["password"] or not check_pw(password, user["password"]):
        print(f"[로그인 실패] {email}")
        return jsonify({"message": "이메일 또는 비밀번호가 올바르지 않습니다."}), 401

    set_session(user)
    print(f"[로그인 성공] {email}")
    return jsonify({"message": "로그인 성공", "is_admin": bool(user["is_admin"])})

# ─────────────────────────────────────────────
# 로그아웃 / 세션
# ─────────────────────────────────────────────
@app.route("/api/auth/logout")
def api_logout():
    session.clear()
    return redirect("/")

@app.route("/api/auth/me")
@login_required
def api_me():
    return jsonify({"email": session["email"], "is_admin": session["is_admin"]})

# ─────────────────────────────────────────────
# Discord OAuth 콜백
# ─────────────────────────────────────────────
@app.route("/auth/discord/callback")
def discord_callback():
    code  = request.args.get("code")
    error = request.args.get("error")
    ip    = get_ip()

    if error or not code:
        return redirect("/?error=discord_cancelled")

    # code → token
    tr = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id":     DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  DISCORD_REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    if not tr.ok:
        print("[Discord] 토큰 실패:", tr.text)
        return redirect("/?discord_error=토큰+교환+실패")

    token = tr.json().get("access_token")

    # token → 유저 정보
    ur = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if not ur.ok:
        return redirect("/?discord_error=유저+정보+실패")

    d          = ur.json()
    discord_id = d["id"]
    email      = d.get("email", "")
    username   = d.get("global_name") or d.get("username", "")
    avatar     = d.get("avatar", "")
    is_new     = False

    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM users WHERE discord_id=?", (discord_id,)
        ).fetchone()

        if existing:
            # 기존 유저 — 정보만 업데이트
            conn.execute(
                "UPDATE users SET discord_name=?, discord_avatar=? WHERE discord_id=?",
                (username, avatar, discord_id)
            )
            conn.commit()
            user = conn.execute(
                "SELECT * FROM users WHERE discord_id=?", (discord_id,)
            ).fetchone()
            print(f"[Discord 로그인] {username}")

        else:
            # 신규 — 중복/다계정 체크
            err = check_duplicate(email, ip)
            if err:
                print(f"[Discord 가입 거절] {username} / IP:{ip} → {err}")
                return redirect(f"/?discord_error={requests.utils.quote(err)}")

            is_new = True

            # 같은 이메일 계정 있으면 연결
            by_email = conn.execute(
                "SELECT * FROM users WHERE email=?", (email,)
            ).fetchone() if email else None

            if by_email:
                conn.execute(
                    "UPDATE users SET discord_id=?, discord_name=?, discord_avatar=? WHERE email=?",
                    (discord_id, username, avatar, email)
                )
                conn.commit()
                user   = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
                is_new = False
            else:
                conn.execute(
                    "INSERT INTO users (email, discord_id, discord_name, discord_avatar, ip) VALUES (?,?,?,?,?)",
                    (email, discord_id, username, avatar, ip)
                )
                conn.commit()
                user = conn.execute(
                    "SELECT * FROM users WHERE discord_id=?", (discord_id,)
                ).fetchone()

    if is_new:
        save_to_json(email, "", "Discord", username)
        send_webhook(email, "Discord 가입", username)
        print(f"[Discord 가입 완료] {username} / IP:{ip}")

    set_session(user)
    return redirect("/admin/dashboard" if user["is_admin"] else "/dashboard")

# ─────────────────────────────────────────────
# 봇 → 관리자 생성
# ─────────────────────────────────────────────
@app.route("/internal/create_admin", methods=["POST"])
def create_admin():
    if request.headers.get("X-Discord-Client-Secret") != DISCORD_CLIENT_SECRET:
        return jsonify({"message": "인증 실패"}), 403

    data     = request.get_json() or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"message": "이메일과 비밀번호를 입력하세요."}), 400

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (email, password, is_admin) VALUES (?,?,1)",
                (email, hash_pw(password))
            )
            conn.commit()
        save_to_json(email, password, "관리자")
        print(f"[관리자 생성] {email}")
        return jsonify({"message": f"관리자 생성 완료: {email}"})
    except sqlite3.IntegrityError:
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET password=?, is_admin=1 WHERE email=?",
                (hash_pw(password), email)
            )
            conn.commit()
        print(f"[관리자 업데이트] {email}")
        return jsonify({"message": f"관리자 권한 업데이트: {email}"})

# ─────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"[서버] http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
