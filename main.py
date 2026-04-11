import os
import sqlite3
import hashlib
import secrets
import requests
from datetime import timedelta
from functools import wraps
from urllib.parse import urlencode

from flask import (
    Flask, request, jsonify, session,
    send_from_directory, redirect, url_for
)
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# ── 설정 ─────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key             = os.environ["SECRET_KEY"]
app.permanent_session_lifetime = timedelta(days=7)
CORS(app, supports_credentials=True)

DISCORD_CLIENT_ID     = os.environ["DISCORD_CLIENT_ID"]
DISCORD_CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
DISCORD_REDIRECT_URI  = os.environ.get("DISCORD_REDIRECT_URI", "http://localhost:5000/auth/discord/callback")

DB_PATH = "sailormarket.db"

# ── DB ───────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                email          TEXT    UNIQUE,
                password       TEXT,
                discord_id     TEXT    UNIQUE,
                discord_name   TEXT,
                discord_avatar TEXT,
                is_admin       INTEGER DEFAULT 0,
                created_at     TEXT    DEFAULT (datetime('now'))
            );
        """)
    print("[DB] 초기화 완료")

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

def set_session(user):
    session.permanent   = True
    session["user_id"]  = user["id"]
    session["email"]    = user["email"] or user["discord_name"]
    session["is_admin"] = bool(user["is_admin"])

# ── 정적 파일 ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return (
        f"<h2>👋 {session['email']} 님, 환영합니다!</h2>"
        f"<p><a href='/api/auth/logout'>로그아웃</a></p>"
    )

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    return (
        f"<h2>🔐 관리자 대시보드</h2>"
        f"<p>{session['email']}</p>"
        f"<p><a href='/api/auth/logout'>로그아웃</a></p>"
    )

# ── API: 회원가입 ─────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data     = request.get_json() or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"message": "이메일과 비밀번호를 입력하세요."}), 400
    if len(password) < 8:
        return jsonify({"message": "비밀번호는 8자 이상이어야 합니다."}), 400

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (email, password) VALUES (?, ?)",
                (email, hash_pw(password))
            )
            conn.commit()
        return jsonify({"message": "회원가입 완료"})
    except sqlite3.IntegrityError:
        return jsonify({"message": "이미 사용 중인 이메일입니다."}), 409

# ── API: 로그인 ───────────────────────────────────────────
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

# ── Discord OAuth: Step 1 — 인증 URL로 리다이렉트 ─────────
# (프론트에서 직접 discord.com으로 보내도 되지만 서버 경유도 지원)
@app.route("/auth/discord")
def discord_auth():
    state  = request.args.get("state", secrets.token_urlsafe(16))
    params = urlencode({
        "client_id":     DISCORD_CLIENT_ID,
        "redirect_uri":  DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope":         "identify email",
        "state":         state,
        "prompt":        "none",
    })
    return redirect(f"https://discord.com/oauth2/authorize?{params}")

# ── Discord OAuth: Step 2 — 콜백 처리 ────────────────────
@app.route("/auth/discord/callback")
def discord_callback():
    code  = request.args.get("code")
    error = request.args.get("error")

    if error or not code:
        return redirect("/?error=discord_cancelled")

    # ① code → access_token 교환
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
        return redirect("/?discord_error=" + requests.utils.quote("토큰 교환 실패"))

    token_data   = token_res.json()
    access_token = token_data.get("access_token")

    # ② access_token → 사용자 정보
    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if not user_res.ok:
        return redirect("/?discord_error=" + requests.utils.quote("유저 정보 조회 실패"))

    d           = user_res.json()
    discord_id  = d["id"]
    email       = d.get("email", "")
    username    = d.get("global_name") or d.get("username", "")
    avatar      = d.get("avatar", "")

    # ③ DB에 upsert (없으면 생성, 있으면 업데이트)
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE users SET discord_name=?, discord_avatar=?, email=COALESCE(NULLIF(email,''),?) WHERE discord_id=?",
                (username, avatar, email, discord_id)
            )
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE discord_id=?", (discord_id,)).fetchone()
        else:
            # 같은 이메일 계정이 이미 있으면 Discord와 연결
            if email:
                exists_by_email = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
                if exists_by_email:
                    conn.execute(
                        "UPDATE users SET discord_id=?, discord_name=?, discord_avatar=? WHERE email=?",
                        (discord_id, username, avatar, email)
                    )
                    conn.commit()
                    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
                else:
                    conn.execute(
                        "INSERT INTO users (email, discord_id, discord_name, discord_avatar) VALUES (?,?,?,?)",
                        (email, discord_id, username, avatar)
                    )
                    conn.commit()
                    user = conn.execute("SELECT * FROM users WHERE discord_id=?", (discord_id,)).fetchone()
            else:
                conn.execute(
                    "INSERT INTO users (discord_id, discord_name, discord_avatar) VALUES (?,?,?)",
                    (discord_id, username, avatar)
                )
                conn.commit()
                user = conn.execute("SELECT * FROM users WHERE discord_id=?", (discord_id,)).fetchone()

    set_session(user)

    if user["is_admin"]:
        return redirect("/admin/dashboard")
    return redirect("/dashboard")

# ── 내부 API: 봇 → 관리자 계정 생성 ─────────────────────
@app.route("/internal/create_admin", methods=["POST"])
def create_admin():
    auth = request.headers.get("X-Discord-Client-Secret", "")
    if auth != DISCORD_CLIENT_SECRET:
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
