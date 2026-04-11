import os
import sqlite3
import hashlib
import secrets
from datetime import timedelta
from functools import wraps

from flask import (
    Flask, request, jsonify, session,
    send_from_directory, redirect
)
from flask_cors import CORS

# ── 설정 ─────────────────────────────────────────────────
app = Flask(__name__, static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.permanent_session_lifetime = timedelta(days=7)

CORS(app, supports_credentials=True, origins=["http://localhost:5000"])

DB_PATH = "sailormarket.db"

# 봇 ↔ 서버 내부 통신용 — Discord Client Secret 사용
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "")

# ── DB 초기화 ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT    UNIQUE NOT NULL,
                password   TEXT    NOT NULL,
                is_admin   INTEGER DEFAULT 0,
                created_at TEXT    DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
    print("[DB] 초기화 완료 →", DB_PATH)

# ── 비밀번호 해싱 ─────────────────────────────────────────
def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + pw).encode()).hexdigest()
    return f"{salt}:{hashed}"

def check_password(pw: str, stored: str) -> bool:
    try:
        salt, hashed = stored.split(":")
        return hashlib.sha256((salt + pw).encode()).hexdigest() == hashed
    except Exception:
        return False

# ── 데코레이터 ────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"message": "로그인이 필요합니다."}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"message": "로그인이 필요합니다."}), 401
        if not session.get("is_admin"):
            return jsonify({"message": "관리자 권한이 필요합니다."}), 403
        return f(*args, **kwargs)
    return decorated

# ── 페이지 서빙 ───────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return f"<h1>안녕하세요, {session.get('email')}님!</h1><a href='/api/logout'>로그아웃</a>"

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    return f"<h1>🔐 관리자 대시보드</h1><p>{session.get('email')}</p><a href='/api/logout'>로그아웃</a>"

# ── API: 로그인 ───────────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def api_login():
    data     = request.get_json()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"message": "이메일과 비밀번호를 입력하세요."}), 400

    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

    if not user or not check_password(password, user["password"]):
        return jsonify({"message": "이메일 또는 비밀번호가 올바르지 않습니다."}), 401

    session.permanent = True
    session["user_id"]  = user["id"]
    session["email"]    = user["email"]
    session["is_admin"] = bool(user["is_admin"])

    return jsonify({
        "message":  "로그인 성공",
        "email":    user["email"],
        "is_admin": bool(user["is_admin"]),
    })

# ── API: 로그아웃 ─────────────────────────────────────────
@app.route("/api/logout")
def api_logout():
    session.clear()
    return redirect("/")

# ── API: 세션 확인 ────────────────────────────────────────
@app.route("/api/me")
@login_required
def api_me():
    return jsonify({
        "email":    session.get("email"),
        "is_admin": session.get("is_admin"),
    })

# ── API: 관리자 유저 목록 ─────────────────────────────────
@app.route("/api/admin/users")
@admin_required
def admin_users():
    with get_db() as conn:
        users = conn.execute(
            "SELECT id, email, is_admin, created_at FROM users ORDER BY id"
        ).fetchall()
    return jsonify([dict(u) for u in users])

# ── 내부 API: 봇 → 관리자 계정 생성 ─────────────────────
# Discord Client Secret으로 인증
@app.route("/internal/create_admin", methods=["POST"])
def create_admin():
    auth = request.headers.get("X-Discord-Client-Secret", "")
    if not DISCORD_CLIENT_SECRET or auth != DISCORD_CLIENT_SECRET:
        return jsonify({"message": "인증 실패"}), 403

    data     = request.get_json()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"message": "이메일과 비밀번호를 입력하세요."}), 400

    hashed = hash_password(password)

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (email, password, is_admin) VALUES (?, ?, 1)",
                (email, hashed)
            )
            conn.commit()
        return jsonify({"message": f"관리자 계정 생성 완료: {email}"})
    except sqlite3.IntegrityError:
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET password = ?, is_admin = 1 WHERE email = ?",
                (hashed, email)
            )
            conn.commit()
        return jsonify({"message": f"기존 계정을 관리자로 업데이트: {email}"})

# ── 실행 ─────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"[서버] http://localhost:{port} 에서 실행 중")
    app.run(host="0.0.0.0", port=port, debug=True)
