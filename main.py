import os
import json
import sqlite3
import hashlib
import secrets
import requests
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import Flask, request, jsonify, session, send_from_directory, redirect
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# ── 설정 ─────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key                 = os.environ["SECRET_KEY"]
app.permanent_session_lifetime = timedelta(days=7)
CORS(app, supports_credentials=True)

DISCORD_CLIENT_ID     = os.environ["DISCORD_CLIENT_ID"]
DISCORD_CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
DISCORD_REDIRECT_URI  = os.environ.get("DISCORD_REDIRECT_URI", "http://localhost:5000/auth/discord/callback")

# 봇 내부 API 주소 (봇이 실행 중인 주소)
BOT_INTERNAL_URL = os.environ.get("BOT_INTERNAL_URL", "http://localhost:6000")

DB_PATH   = "sailormarket.db"
JSON_PATH = "user_id_pw.json"   # 가입 계정 저장 파일

# ── DB ───────────────────────────────────────────────────
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
                is_admin       INTEGER DEFAULT 0,
                created_at     TEXT    DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        # 마이그레이션
        existing = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
        for col, sql in {
            "discord_id":     "ALTER TABLE users ADD COLUMN discord_id TEXT",
            "discord_name":   "ALTER TABLE users ADD COLUMN discord_name TEXT",
            "discord_avatar": "ALTER TABLE users ADD COLUMN discord_avatar TEXT",
            "is_admin":       "ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0",
        }.items():
            if col not in existing:
                conn.execute(sql)
                print(f"[DB] 컬럼 추가: {col}")
        conn.commit()
    print("[DB] 초기화 완료")

# ── JSON 저장 ─────────────────────────────────────────────
def save_user_json(email: str, password_raw: str, method: str, discord_name: str = ""):
    """user_id_pw.json 에 가입 계정 저장 (비밀번호는 해시로 저장)"""
    data = []
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []

    # 중복 체크
    for u in data:
        if u.get("email") == email:
            return  # 이미 있으면 스킵

    entry = {
        "email":        email,
        "password":     hash_pw(password_raw) if password_raw else "(Discord 로그인)",
        "method":       method,
        "discord_name": discord_name,
        "created_at":   datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    data.append(entry)

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[JSON] 저장 완료: {email}")

# ── 비밀번호 ─────────────────────────────────────────────
def hash_pw(pw: str) -> str:
    salt   = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + pw).encode()).hexdigest()
    return f"{salt}:{hashed}"

def check_pw(pw: str, stored: str) -> bool:
    try:
        salt, hashed = stored.split(":")
        return hashlib.sha256((salt + pw).encode()).hexdigest() == hashed
    except Exception:
        return False

# ── 세션 ─────────────────────────────────────────────────
def set_session(user):
    session.permanent   = True
    session["user_id"]  = user["id"]
    session["email"]    = user["email"] or user["discord_name"] or "유저"
    session["is_admin"] = bool(user["is_admin"])

# ── 데코레이터 ────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def deco(*a, **kw):
        if "user_id" not in session:
            return jsonify({"message": "로그인이 필요합니다."}), 401
        return f(*a, **kw)
    return deco

def admin_required(f):
    @wraps(f)
    def deco(*a, **kw):
        if "user_id" not in session:
            return jsonify({"message": "로그인이 필요합니다."}), 401
        if not session.get("is_admin"):
            return jsonify({"message": "관리자 권한이 필요합니다."}), 403
        return f(*a, **kw)
    return deco

# ── 봇에 알림 전송 ────────────────────────────────────────
def notify_bot_signup(email: str, method: str, discord_name: str = ""):
    """봇 내부 API 호출 → 봇이 채널에 ui.Container 로 전송"""
    try:
        requests.post(
            f"{BOT_INTERNAL_URL}/notify/signup",
            json={"email": email, "method": method, "discord_name": discord_name},
            headers={"X-Discord-Client-Secret": DISCORD_CLIENT_SECRET},
            timeout=5,
        )
        print(f"[알림] 봇에 전송 완료: {email}")
    except Exception as e:
        print(f"[알림] 봇 전송 실패: {e}")

# ── 페이지 ────────────────────────────────────────────────
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

# ── API: 이메일 회원가입 ──────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data     = request.get_json() or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"message": "이메일과 비밀번호를 입력하세요."}), 400
    if len(password) < 8:
        return jsonify({"message": "비밀번호는 8자 이상이어야 합니다."}), 400

    # ── 중복 체크 (DB) ──
    with get_db() as conn:
        exists = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
    if exists:
        return jsonify({"message": "이미 가입된 이메일입니다."}), 409

    # ── DB 저장 ──
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (email, password) VALUES (?, ?)",
                (email, hash_pw(password))
            )
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"message": "이미 가입된 이메일입니다."}), 409

    # ── JSON 저장 ──
    save_user_json(email, password, "이메일")

    # ── 봇 알림 ──
    notify_bot_signup(email, "이메일 가입")

    print(f"[가입] 이메일: {email}")
    return jsonify({"message": "회원가입 완료"})

# ── API: 이메일 로그인 ────────────────────────────────────
@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data     = request.get_json() or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"message": "이메일과 비밀번호를 입력하세요."}), 400

    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not user or not user["password"] or not check_pw(password, user["password"]):
        return jsonify({"message": "이메일 또는 비밀번호가 올바르지 않습니다."}), 401

    set_session(user)
    print(f"[로그인] {email}")
    return jsonify({"message": "로그인 성공", "is_admin": bool(user["is_admin"])})

# ── API: 로그아웃 ─────────────────────────────────────────
@app.route("/api/auth/logout")
def api_logout():
    session.clear()
    return redirect("/")

# ── API: 세션 확인 ────────────────────────────────────────
@app.route("/api/auth/me")
@login_required
def api_me():
    return jsonify({"email": session["email"], "is_admin": session["is_admin"]})

# ── Discord OAuth 콜백 ────────────────────────────────────
@app.route("/auth/discord/callback")
def discord_callback():
    code  = request.args.get("code")
    error = request.args.get("error")

    if error or not code:
        return redirect("/?error=discord_cancelled")

    # code → access_token
    token_res = requests.post(
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
    if not token_res.ok:
        print("[Discord] 토큰 교환 실패:", token_res.text)
        return redirect("/?discord_error=토큰+교환+실패")

    access_token = token_res.json().get("access_token")

    # access_token → 유저 정보
    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if not user_res.ok:
        return redirect("/?discord_error=유저+정보+조회+실패")

    d          = user_res.json()
    discord_id = d["id"]
    email      = d.get("email", "")
    username   = d.get("global_name") or d.get("username", "")
    avatar     = d.get("avatar", "")
    is_new     = False

    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE users SET discord_name=?, discord_avatar=? WHERE discord_id=?",
                (username, avatar, discord_id)
            )
            conn.commit()
            user = conn.execute(
                "SELECT * FROM users WHERE discord_id=?", (discord_id,)
            ).fetchone()

        else:
            is_new = True
            by_email = conn.execute(
                "SELECT * FROM users WHERE email=?", (email,)
            ).fetchone() if email else None

            if by_email:
                # 같은 이메일 → Discord 연결만
                conn.execute(
                    "UPDATE users SET discord_id=?, discord_name=?, discord_avatar=? WHERE email=?",
                    (discord_id, username, avatar, email)
                )
                conn.commit()
                user   = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
                is_new = False
            else:
                conn.execute(
                    "INSERT INTO users (email, discord_id, discord_name, discord_avatar) VALUES (?,?,?,?)",
                    (email, discord_id, username, avatar)
                )
                conn.commit()
                user = conn.execute(
                    "SELECT * FROM users WHERE discord_id=?", (discord_id,)
                ).fetchone()

    if is_new:
        save_user_json(email, "", "Discord", username)
        notify_bot_signup(email, "Discord 가입", username)
        print(f"[가입] Discord: {username} ({email})")

    set_session(user)
    return redirect("/admin/dashboard" if user["is_admin"] else "/dashboard")

# ── 내부 API: 봇 → 관리자 계정 생성 ─────────────────────
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
        save_user_json(email, password, "관리자")
        return jsonify({"message": f"관리자 생성 완료: {email}"})
    except sqlite3.IntegrityError:
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET password=?, is_admin=1 WHERE email=?",
                (hash_pw(password), email)
            )
            conn.commit()
        return jsonify({"message": f"관리자 권한 업데이트: {email}"})

# ── 실행 ─────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"[서버] http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
