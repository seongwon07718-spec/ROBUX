from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

web_app = FastAPI(title="VOUT SERVICE", docs_url=None, redoc_url=None)

# ─────────────────────────────────────────────
# 환경 설정 (실제 배포 시 환경변수로 관리)
# ─────────────────────────────────────────────
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "1501926340213870722")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "ny1lsPEegPFoMRC_O4ITvf7231nISP4-")
DISCORD_REDIRECT_URI = os.environ.get("DISCORD_REDIRECT_URI", "https://v0ut.com/auth/callback")
DISCORD_BOT_REDIRECT_URI = os.environ.get("DISCORD_BOT_REDIRECT_URI", "https://v0ut.com/auth/bot_callback")

# 관리자 비밀번호 — 환경변수 필수
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "CHANGE_THIS_PASSWORD")

# 관리자 Discord ID 목록 — 비어있으면 보안 위험! 반드시 설정하세요.
_raw_ids = os.environ.get("ADMIN_USER_IDS", "")
ADMIN_USER_IDS: list[int] = [int(x) for x in _raw_ids.split(",") if x.strip().isdigit()]

DB_BASE_PATH = "DB"
TEMPLATES_PATH = Path(__file__).parent / "templates"

# ─────────────────────────────────────────────
# 세션 저장 (메모리, 단일 프로세스용)
# 프로덕션에서는 Redis 등 외부 저장소 사용 권장
# ─────────────────────────────────────────────
_sessions: dict[str, dict[str, Any]] = {}
SESSION_TTL = 3600  # 1시간


def _purge_expired_sessions() -> None:
    now = time.time()
    expired = [k for k, v in _sessions.items() if now - v.get("ts", 0) > SESSION_TTL]
    for k in expired:
        del _sessions[k]


def _set_session(token: str, data: dict[str, Any]) -> None:
    _purge_expired_sessions()
    _sessions[token] = {**data, "ts": time.time()}


def _get_session(token: str) -> dict[str, Any] | None:
    session = _sessions.get(token)
    if not session:
        return None
    if time.time() - session.get("ts", 0) > SESSION_TTL:
        del _sessions[token]
        return None
    return session


# ─────────────────────────────────────────────
# 임시 OAuth state 저장 (CSRF 방지)
# ─────────────────────────────────────────────
_oauth_states: dict[str, dict[str, Any]] = {}
OAUTH_STATE_TTL = 300  # 5분


def _new_oauth_state(extra: dict | None = None) -> str:
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {"ts": time.time(), **(extra or {})}
    return state


def _pop_oauth_state(state: str) -> dict[str, Any] | None:
    data = _oauth_states.pop(state, None)
    if not data:
        return None
    if time.time() - data["ts"] > OAUTH_STATE_TTL:
        return None
    return data


# ─────────────────────────────────────────────
# DB 헬퍼
# ─────────────────────────────────────────────
def _get_license_db() -> sqlite3.Connection:
    os.makedirs(DB_BASE_PATH, exist_ok=True)
    conn = sqlite3.connect(os.path.join(DB_BASE_PATH, "licenses.db"))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key   TEXT UNIQUE,
            tier          TEXT,
            guild_id      TEXT,
            guild_name    TEXT,
            issued_by     TEXT,
            issued_at     TEXT,
            expires_at    TEXT,
            duration_days INTEGER,
            is_active     INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    return conn


def _get_server_db(guild_id: str) -> sqlite3.Connection:
    path = os.path.join(DB_BASE_PATH, str(guild_id))
    os.makedirs(path, exist_ok=True)
    conn = sqlite3.connect(os.path.join(path, "server.db"))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS auth_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE,
            state TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS verified_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE,
            username TEXT,
            verified_at TEXT
        )
    """)
    conn.commit()
    return conn


# ─────────────────────────────────────────────
# 템플릿 로드
# ─────────────────────────────────────────────
def _read_template(name: str) -> str:
    p = TEMPLATES_PATH / name
    if p.exists():
        return p.read_text(encoding="utf-8")
    return f"<h1>404 — {name} not found</h1>"


def _is_admin(user_id: int) -> bool:
    """ADMIN_USER_IDS가 비어 있으면 아무도 관리자가 아님 (보안 강화)"""
    if not ADMIN_USER_IDS:
        # 설정되지 않았을 때는 경고 로그 출력
        print("[경고] ADMIN_USER_IDS가 설정되지 않았습니다. 관리자 접근이 차단됩니다.")
        return False
    return user_id in ADMIN_USER_IDS


def _check_admin_password(password: str) -> bool:
    """상수 시간 비교로 타이밍 공격 방지"""
    return hmac.compare_digest(password, ADMIN_PASSWORD)


# ─────────────────────────────────────────────
# 관리자 라우트
# ─────────────────────────────────────────────
@web_app.get("/admin/restore")
async def admin_login_page() -> HTMLResponse:
    return HTMLResponse(_read_template("admin_login.html"))


@web_app.get("/auth/discord")
async def auth_discord_start() -> RedirectResponse:
    """관리자용 Discord OAuth2 시작"""
    state = _new_oauth_state({"purpose": "admin"})
    url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
        f"&state={state}"
    )
    return RedirectResponse(url)


@web_app.get("/auth/callback")
async def auth_callback(code: str = "", state: str = "", error: str = "") -> HTMLResponse | RedirectResponse:
    """Discord OAuth2 콜백 (관리자용)"""
    if error:
        return HTMLResponse(_read_template("admin_forbidden.html"), status_code=403)

    state_data = _pop_oauth_state(state)
    if not state_data:
        return HTMLResponse(_read_template("admin_forbidden.html"), status_code=403)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 액세스 토큰 교환
        token_resp = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            },
        )
        token_json = token_resp.json()

        if "access_token" not in token_json:
            return HTMLResponse(_read_template("admin_forbidden.html"), status_code=403)

        # 유저 정보 조회
        user_resp = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {token_json['access_token']}"},
        )
        user_data = user_resp.json()

    user_id = int(user_data.get("id", 0))
    if not _is_admin(user_id):
        return HTMLResponse(_read_template("admin_forbidden.html"), status_code=403)

    session_token = secrets.token_urlsafe(32)
    _set_session(session_token, {
        "user_id": user_id,
        "username": user_data.get("username", "Unknown"),
        "avatar": user_data.get("avatar"),
    })
    return RedirectResponse(f"/admin/dashboard?token={session_token}")


@web_app.get("/admin/dashboard")
async def admin_dashboard(token: str = "") -> HTMLResponse:
    session = _get_session(token)
    if not session:
        return RedirectResponse("/admin/restore")

    html = _read_template("admin_dashboard.html")
    html = html.replace("{{USERNAME}}", session.get("username", "Admin"))
    html = html.replace("{{USER_ID}}", str(session.get("user_id", "")))
    html = html.replace("{{AVATAR}}", session.get("avatar") or "")
    html = html.replace("{{TOKEN}}", token)
    return HTMLResponse(html)


# ─────────────────────────────────────────────
# 봇 인증 라우트 (디스코드 봇 → 웹 OAuth)
# ─────────────────────────────────────────────
@web_app.get("/auth/login")
async def auth_login_start(state: str = "", guild_id: str = "", user_id: str = "") -> HTMLResponse | RedirectResponse:
    """봇에서 보내는 인증 링크 진입점"""
    if not state or not guild_id or not user_id:
        return HTMLResponse(_read_template("auth_fail.html"), status_code=400)

    # state 유효성 검증
    conn = _get_server_db(guild_id)
    try:
        c = conn.cursor()
        c.execute("SELECT state FROM auth_states WHERE user_id = ? AND state = ?", (user_id, state))
        row = c.fetchone()
    finally:
        conn.close()

    if not row:
        return HTMLResponse(_read_template("auth_fail.html"), status_code=403)

    # Discord OAuth2로 리디렉션 (guilds.join 스코프 포함)
    oauth_state = _new_oauth_state({"guild_id": guild_id, "user_id": user_id, "bot_state": state})
    url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_BOT_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds.join"
        f"&state={oauth_state}"
    )
    return RedirectResponse(url)


@web_app.get("/auth/bot_callback")
async def auth_bot_callback(code: str = "", state: str = "", error: str = "") -> HTMLResponse:
    """봇 인증 OAuth2 콜백"""
    if error:
        return HTMLResponse(_read_template("auth_fail.html"), status_code=400)

    state_data = _pop_oauth_state(state)
    if not state_data:
        return HTMLResponse(_read_template("auth_fail.html"), status_code=403)

    guild_id = state_data.get("guild_id")
    user_id = state_data.get("user_id")

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_resp = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_BOT_REDIRECT_URI,
            },
        )
        token_json = token_resp.json()

        if "access_token" not in token_json:
            return HTMLResponse(_read_template("auth_fail.html"), status_code=403)

        user_resp = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {token_json['access_token']}"},
        )
        user_data = user_resp.json()

    actual_user_id = user_data.get("id")
    if actual_user_id != user_id:
        # 다른 계정으로 인증 시도 차단
        return HTMLResponse(_read_template("auth_fail.html"), status_code=403)

    # 인증 완료 처리
    username = user_data.get("username", "Unknown")
    conn = _get_server_db(guild_id)
    try:
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO verified_members (user_id, username, verified_at) VALUES (?, ?, ?)",
            (actual_user_id, username, datetime.now().isoformat()),
        )
        # 사용된 state 삭제
        c.execute("DELETE FROM auth_states WHERE user_id = ?", (actual_user_id,))
        conn.commit()
    finally:
        conn.close()

    return HTMLResponse(_read_template("auth_success.html"))


# ─────────────────────────────────────────────
# 관리자 API
# ─────────────────────────────────────────────
@web_app.post("/admin/api/issue")
async def api_issue_license(request: Request) -> dict:
    data = await request.json()

    if not _check_admin_password(data.get("password", "")):
        raise HTTPException(status_code=401, detail="비밀번호가 올바르지 않습니다")

    tier = data.get("tier", "").upper()
    if tier not in ("FREE", "PRO"):
        raise HTTPException(status_code=400, detail="tier는 FREE 또는 PRO만 허용됩니다")

    duration = max(1, min(int(data.get("duration", 30)), 3650))  # 1일 ~ 10년
    key = f"{tier}_{secrets.token_hex(12).upper()}"
    issued_at = datetime.now()
    expires_at = issued_at + timedelta(days=duration)

    conn = _get_license_db()
    try:
        conn.execute(
            "INSERT INTO licenses (license_key, tier, issued_by, issued_at, expires_at, duration_days, is_active) "
            "VALUES (?, ?, 'admin', ?, ?, ?, 1)",
            (key, tier, issued_at.isoformat(), expires_at.isoformat(), duration),
        )
        conn.commit()
    finally:
        conn.close()

    return {"success": True, "license_key": key, "expires_at": expires_at.isoformat()}


@web_app.get("/admin/api/licenses")
async def api_list_licenses(password: str = "") -> list[dict]:
    if not _check_admin_password(password):
        raise HTTPException(status_code=401, detail="인증 실패")

    conn = _get_license_db()
    try:
        rows = conn.execute(
            "SELECT license_key, tier, guild_id, guild_name, issued_at, expires_at, is_active "
            "FROM licenses ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "license_key": r[0],
            "tier": r[1],
            "guild_id": r[2] or "-",
            "guild_name": r[3] or "-",
            "issued_at": r[4],
            "expires_at": r[5],
            "is_active": bool(r[6]),
        }
        for r in rows
    ]


@web_app.delete("/admin/api/license/{license_key}")
async def api_delete_license(license_key: str, password: str = "") -> dict:
    if not _check_admin_password(password):
        raise HTTPException(status_code=401, detail="인증 실패")

    conn = _get_license_db()
    try:
        conn.execute("UPDATE licenses SET is_active = 0 WHERE license_key = ?", (license_key,))
        conn.commit()
    finally:
        conn.close()

    return {"success": True}


@web_app.post("/admin/api/logout")
async def api_logout(request: Request) -> dict:
    data = await request.json()
    token = data.get("token", "")
    _sessions.pop(token, None)
    return {"success": True}


@web_app.get("/admin/api/servers")
async def api_list_servers(password: str = "") -> list[dict]:
    if not _check_admin_password(password):
        raise HTTPException(status_code=401, detail="인증 실패")

    conn = _get_license_db()
    try:
        rows = conn.execute(
            "SELECT guild_id, guild_name, tier, expires_at, is_active FROM licenses "
            "WHERE guild_id IS NOT NULL AND guild_id != '' ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()

    return [
        {"guild_id": r[0], "guild_name": r[1] or f"ID:{r[0]}", "tier": r[2], "expires_at": r[3], "is_active": bool(r[4])}
        for r in rows
    ]


# ─────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────
def run_web() -> None:
    uvicorn.run(web_app, host="0.0.0.0", port=8065, log_level="warning")


if __name__ == "__main__":
    run_web()
