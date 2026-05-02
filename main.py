import sqlite3, secrets, string, hashlib, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

Path("SERVER").mkdir(exist_ok=True)
KST = timezone(timedelta(hours=9))

def _now() -> datetime: return datetime.now(KST)
def _iso(dt: datetime) -> str: return dt.isoformat()
def _hash(v: str) -> str: return hashlib.sha256(v.encode()).hexdigest()

def _gen_key() -> str:
    ab = string.ascii_uppercase + string.digits
    return "VND-" + "-".join("".join(secrets.choice(ab) for _ in range(4)) for _ in range(3))

def _cols(conn, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]

def _rows(conn, table: str, rows) -> list[dict]:
    c = _cols(conn, table)
    return [dict(zip(c, r)) for r in rows]


# ─── LicenseDB ────────────────────────────────────────────────
class LicenseDB:
    PATH = "SERVER/license.db"
    def __init__(self):
        self.c = sqlite3.connect(self.PATH, check_same_thread=False)
        self.c.execute("PRAGMA journal_mode=WAL")
        self.c.executescript("""
            CREATE TABLE IF NOT EXISTS licenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_plain TEXT NOT NULL UNIQUE,
                key_hash  TEXT NOT NULL UNIQUE,
                period_days INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'unused',
                created_at TEXT NOT NULL,
                activated_at TEXT, expires_at TEXT, guild_id TEXT);
        """); self.c.commit()

    def create(self, count: int, days: int) -> list[str]:
        keys, now = [], _iso(_now())
        for _ in range(count):
            k = _gen_key()
            self.c.execute("INSERT INTO licenses(key_plain,key_hash,period_days,status,created_at) VALUES(?,?,?,?,?)",
                           (k, _hash(k), days, "unused", now))
            keys.append(k)
        self.c.commit(); return keys

    def delete(self, key: str) -> bool:
        r = self.c.execute("DELETE FROM licenses WHERE key_plain=?", (key,))
        self.c.commit(); return r.rowcount > 0

    def get_all(self, status=None) -> list[dict]:
        if status:
            rows = self.c.execute("SELECT * FROM licenses WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
        else:
            rows = self.c.execute("SELECT * FROM licenses ORDER BY created_at DESC").fetchall()
        return _rows(self.c, "licenses", rows)

    def activate(self, key: str, guild_id: int) -> Optional[dict]:
        row = self.c.execute("SELECT * FROM licenses WHERE key_plain=? AND status='unused'", (key,)).fetchone()
        if not row: return None
        data = dict(zip(_cols(self.c, "licenses"), row))
        now = _now(); exp = now + timedelta(days=data["period_days"])
        self.c.execute("UPDATE licenses SET status='active',activated_at=?,expires_at=?,guild_id=? WHERE key_plain=?",
                       (_iso(now), _iso(exp), str(guild_id), key))
        self.c.commit(); data["expires_at"] = _iso(exp); return data

    def expire_check(self) -> list[str]:
        now = _iso(_now())
        rows = self.c.execute("SELECT guild_id FROM licenses WHERE status='active' AND expires_at<=?", (now,)).fetchall()
        self.c.execute("UPDATE licenses SET status='expired' WHERE status='active' AND expires_at<=?", (now,))
        self.c.commit(); return [r[0] for r in rows if r[0]]

    def get_by_guild(self, guild_id: int) -> Optional[dict]:
        row = self.c.execute("SELECT * FROM licenses WHERE guild_id=? AND status='active'", (str(guild_id),)).fetchone()
        return dict(zip(_cols(self.c, "licenses"), row)) if row else None


# ─── ServerListDB ─────────────────────────────────────────────
class ServerListDB:
    PATH = "SERVER/server_list.db"
    def __init__(self):
        self.c = sqlite3.connect(self.PATH, check_same_thread=False)
        self.c.execute("PRAGMA journal_mode=WAL")
        self.c.executescript("""
            CREATE TABLE IF NOT EXISTS servers(
                guild_id TEXT PRIMARY KEY, 
                guild_name TEXT,
                status TEXT NOT NULL DEFAULT 'invited',
                joined_at TEXT, 
                expires_at TEXT, 
                license_key TEXT);
        """); self.c.commit()

    def upsert(self, guild_id: int, name: str, status="invited", expires_at=None, license_key=None):
        self.c.execute("""
            INSERT INTO servers(guild_id,guild_name,status,joined_at,expires_at,license_key)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                guild_name=excluded.guild_name,
                status=excluded.status,
                expires_at=COALESCE(excluded.expires_at,expires_at),
                license_key=COALESCE(excluded.license_key,license_key)
        """, (str(guild_id), name, status, _iso(_now()), expires_at, license_key))
        self.c.commit()

    def delete(self, guild_id: int) -> Optional[dict]:
        """서버 완전 삭제"""
        row = self.c.execute("SELECT * FROM servers WHERE guild_id=?", (str(guild_id),)).fetchone()
        if not row: return None
        data = dict(zip(_cols(self.c, "servers"), row))
        
        self.c.execute("DELETE FROM servers WHERE guild_id=?", (str(guild_id),))
        self.c.commit()
        return data

    def get_all(self, status=None) -> list[dict]:
        if status:
            rows = self.c.execute("SELECT * FROM servers WHERE status=? ORDER BY joined_at DESC", (status,)).fetchall()
        else:
            rows = self.c.execute("SELECT * FROM servers ORDER BY joined_at DESC").fetchall()
        return _rows(self.c, "servers", rows)

    def set_expired(self, guild_id: int):
        self.c.execute("UPDATE servers SET status='expired' WHERE guild_id=?", (str(guild_id),))
        self.c.commit()


# ─── GuildDB ──────────────────────────────────────────────────
class GuildDB:
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.c = sqlite3.connect(f"SERVER/{guild_id}.db", check_same_thread=False)
        self.c.execute("PRAGMA journal_mode=WAL")
        self.c.execute("PRAGMA foreign_keys=ON")
        self.c.executescript("""
            CREATE TABLE IF NOT EXISTS guild_config(key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS roles(role_type TEXT PRIMARY KEY, role_id TEXT,
                min_amount INTEGER DEFAULT 0, discount_rate REAL DEFAULT 0.0);
            CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE);
            CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL, name TEXT NOT NULL, price INTEGER NOT NULL,
                FOREIGN KEY(category_id) REFERENCES categories(id));
            CREATE TABLE IF NOT EXISTS stock(product_id INTEGER PRIMARY KEY, items TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(product_id) REFERENCES products(id));
            CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0,
                total_spent INTEGER NOT NULL DEFAULT 0,
                discount_rate REAL NOT NULL DEFAULT 0.0);
            CREATE TABLE IF NOT EXISTS charge_history(id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, amount INTEGER NOT NULL, method TEXT NOT NULL,
                depositor TEXT, status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL, confirmed_at TEXT);
            CREATE TABLE IF NOT EXISTS purchase_history(id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, product_id INTEGER NOT NULL, product_name TEXT NOT NULL,
                price INTEGER NOT NULL, quantity INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, purchase_id INTEGER NOT NULL,
                stars INTEGER NOT NULL, content TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS webhooks(log_type TEXT PRIMARY KEY, webhook_url TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS vending_messages(channel_id TEXT PRIMARY KEY, message_id TEXT NOT NULL);
        """); self.c.commit()

    # ... (나머지 메서드들은 기존과 동일) ...

    def delete_all_data(self):
        """서버 DB 완전 초기화 (필요시 사용)"""
        tables = [
            "guild_config", "roles", "categories", "products", "stock",
            "users", "charge_history", "purchase_history", "reviews",
            "webhooks", "vending_messages"
        ]
        for table in tables:
            self.c.execute(f"DELETE FROM {table}")
        self.c.commit()
