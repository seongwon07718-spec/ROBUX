from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Generator

DB_BASE_PATH = "DB"
USER_DB_BASE_PATH = "USER"


def _ensure_dirs(*paths: str) -> None:
    for p in paths:
        os.makedirs(p, exist_ok=True)


# ─────────────────────────────────────────────
# 서버 DB
# ─────────────────────────────────────────────
def get_server_db(guild_id: str) -> sqlite3.Connection:
    """서버별 DB 연결 반환. 사용 후 반드시 conn.close() 호출."""
    guild_dir = os.path.join(DB_BASE_PATH, str(guild_id))
    _ensure_dirs(guild_dir)

    conn = sqlite3.connect(os.path.join(guild_dir, "server.db"))
    conn.row_factory = sqlite3.Row  # 딕셔너리 방식 접근 지원
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS backups (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            backup_id   TEXT UNIQUE,
            backup_type TEXT,
            backup_name TEXT,
            created_at  TEXT,
            data        TEXT,
            item_count  INTEGER
        );
        CREATE TABLE IF NOT EXISTS auth_states (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    TEXT UNIQUE,
            state      TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS verified_members (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT UNIQUE,
            username    TEXT,
            verified_at TEXT
        );
        CREATE TABLE IF NOT EXISTS auth_roles (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id    TEXT UNIQUE,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS auth_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    TEXT,
            username   TEXT,
            action     TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS server_settings (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key   TEXT UNIQUE,
            setting_value TEXT,
            updated_at    TEXT
        );
    """)
    conn.commit()
    return conn


# ─────────────────────────────────────────────
# 유저 DB
# ─────────────────────────────────────────────
def get_user_db(guild_id: str, user_id: str) -> sqlite3.Connection:
    """유저별 DB 연결 반환. 사용 후 반드시 conn.close() 호출."""
    user_dir = os.path.join(USER_DB_BASE_PATH, str(guild_id))
    _ensure_dirs(user_dir)

    conn = sqlite3.connect(os.path.join(user_dir, f"user_{user_id}.db"))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_auth (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      TEXT UNIQUE,
            is_verified  INTEGER DEFAULT 0,
            verified_at  TEXT,
            access_token TEXT
        )
    """)
    conn.commit()
    return conn


# ─────────────────────────────────────────────
# 라이선스 DB
# ─────────────────────────────────────────────
def get_license_db() -> sqlite3.Connection:
    """라이선스 DB 연결 반환. 사용 후 반드시 conn.close() 호출."""
    _ensure_dirs(DB_BASE_PATH)
    conn = sqlite3.connect(os.path.join(DB_BASE_PATH, "licenses.db"))
    c = conn.cursor()
    c.execute("""
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


# ─────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────
def cleanup_expired_licenses() -> int:
    """만료된 라이선스를 비활성화. 비활성화된 수를 반환."""
    conn = get_license_db()
    try:
        c = conn.cursor()
        c.execute(
            "UPDATE licenses SET is_active = 0 WHERE expires_at IS NOT NULL AND expires_at < ? AND is_active = 1",
            (datetime.now().isoformat(),),
        )
        affected = c.rowcount
        conn.commit()
        return affected
    finally:
        conn.close()


def log_auth_action(guild_id: str, user_id: str, username: str, action: str) -> None:
    """인증 로그 기록"""
    conn = get_server_db(guild_id)
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO auth_logs (user_id, username, action, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, action, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
