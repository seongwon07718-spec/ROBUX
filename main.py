import sqlite3, secrets, string, hashlib
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
                guild_id TEXT PRIMARY KEY, guild_name TEXT,
                status TEXT NOT NULL DEFAULT 'invited',
                joined_at TEXT, expires_at TEXT, license_key TEXT);
        """); self.c.commit()

    def upsert(self, guild_id: int, name: str, status="invited", expires_at=None, license_key=None):
        self.c.execute("""
            INSERT INTO servers(guild_id,guild_name,status,joined_at,expires_at,license_key)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(guild_id) DO UPDATE SET guild_name=excluded.guild_name,
            status=excluded.status,
            expires_at=COALESCE(excluded.expires_at,expires_at),
            license_key=COALESCE(excluded.license_key,license_key)""",
            (str(guild_id), name, status, _iso(_now()), expires_at, license_key))
        self.c.commit()

    def delete(self, guild_id: int) -> Optional[dict]:
        row = self.c.execute("SELECT * FROM servers WHERE guild_id=?", (str(guild_id),)).fetchone()
        if not row: return None
        data = dict(zip(_cols(self.c, "servers"), row))
        self.c.execute("DELETE FROM servers WHERE guild_id=?", (str(guild_id),)); self.c.commit()
        return data

    def get_all(self, status=None) -> list[dict]:
        if status:
            rows = self.c.execute("SELECT * FROM servers WHERE status=? ORDER BY joined_at DESC", (status,)).fetchall()
        else:
            rows = self.c.execute("SELECT * FROM servers ORDER BY joined_at DESC").fetchall()
        return _rows(self.c, "servers", rows)

    def set_active(self, guild_id: int, expires_at: str, license_key: str):
        self.c.execute("UPDATE servers SET status='active',expires_at=?,license_key=? WHERE guild_id=?",
                       (expires_at, license_key, str(guild_id))); self.c.commit()

    def set_expired(self, guild_id: int):
        self.c.execute("UPDATE servers SET status='expired' WHERE guild_id=?", (str(guild_id),)); self.c.commit()


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

    # 설정
    def set_cfg(self, k, v): self.c.execute("INSERT OR REPLACE INTO guild_config VALUES(?,?)",(k,v)); self.c.commit()
    def get_cfg(self, k, d=None):
        r = self.c.execute("SELECT value FROM guild_config WHERE key=?", (k,)).fetchone()
        return r[0] if r else d
    def all_cfg(self) -> dict:
        return {r[0]:r[1] for r in self.c.execute("SELECT key,value FROM guild_config").fetchall()}

    # 역할
    def set_role(self, rtype, rid, amt=0, disc=0.0):
        self.c.execute("INSERT OR REPLACE INTO roles VALUES(?,?,?,?)",(rtype,rid,amt,disc)); self.c.commit()
    def get_roles(self) -> list[dict]:
        return [{"role_type":r[0],"role_id":r[1],"min_amount":r[2],"discount_rate":r[3]}
                for r in self.c.execute("SELECT * FROM roles").fetchall()]

    # 카테고리
    def add_cat(self, name: str) -> bool:
        try: self.c.execute("INSERT INTO categories(name) VALUES(?)",(name,)); self.c.commit(); return True
        except sqlite3.IntegrityError: return False
    def del_cat(self, cid: int):
        for r in self.c.execute("SELECT id FROM products WHERE category_id=?",(cid,)).fetchall():
            self.c.execute("DELETE FROM stock WHERE product_id=?",(r[0],))
        self.c.execute("DELETE FROM products WHERE category_id=?",(cid,))
        self.c.execute("DELETE FROM categories WHERE id=?",(cid,)); self.c.commit()
    def get_cats(self) -> list[dict]:
        return [{"id":r[0],"name":r[1]} for r in self.c.execute("SELECT id,name FROM categories ORDER BY id").fetchall()]

    # 상품
    def add_prod(self, cid: int, name: str, price: int) -> int:
        cur = self.c.execute("INSERT INTO products(category_id,name,price) VALUES(?,?,?)",(cid,name,price))
        pid = cur.lastrowid
        self.c.execute("INSERT OR IGNORE INTO stock(product_id,items) VALUES(?,'')",(pid,))
        self.c.commit(); return pid
    def del_prod(self, pid: int):
        self.c.execute("DELETE FROM stock WHERE product_id=?",(pid,))
        self.c.execute("DELETE FROM products WHERE id=?",(pid,)); self.c.commit()
    def get_prods(self, cid: int) -> list[dict]:
        rows = self.c.execute(
            "SELECT p.id,p.name,p.price,COALESCE(s.items,'') FROM products p LEFT JOIN stock s ON p.id=s.product_id WHERE p.category_id=? ORDER BY p.id",
            (cid,)).fetchall()
        return [{"id":r[0],"name":r[1],"price":r[2],"stock":len([x for x in r[3].split("\n") if x.strip()])} for r in rows]
    def get_prod(self, pid: int) -> Optional[dict]:
        r = self.c.execute("SELECT id,name,price,category_id FROM products WHERE id=?",(pid,)).fetchone()
        return {"id":r[0],"name":r[1],"price":r[2],"cat_id":r[3]} if r else None
    def all_prods(self) -> list[dict]:
        rows = self.c.execute(
            "SELECT p.id,p.name,p.price,p.category_id,c.name,COALESCE(s.items,'') FROM products p JOIN categories c ON p.category_id=c.id LEFT JOIN stock s ON p.id=s.product_id ORDER BY p.id"
        ).fetchall()
        return [{"id":r[0],"name":r[1],"price":r[2],"cat_id":r[3],"cat_name":r[4],
                 "stock":len([x for x in r[5].split("\n") if x.strip()])} for r in rows]

    # 재고
    def add_stock(self, pid: int, raw: str) -> int:
        row = self.c.execute("SELECT items FROM stock WHERE product_id=?",(pid,)).fetchone()
        old = [x for x in (row[0] if row else "").split("\n") if x.strip()]
        new = [x for x in raw.split("\n") if x.strip()]
        self.c.execute("INSERT OR REPLACE INTO stock(product_id,items) VALUES(?,?)",(pid,"\n".join(old+new)))
        self.c.commit(); return len(new)
    def stock_cnt(self, pid: int) -> int:
        r = self.c.execute("SELECT items FROM stock WHERE product_id=?",(pid,)).fetchone()
        return len([x for x in r[0].split("\n") if x.strip()]) if r and r[0].strip() else 0
    def stock_preview(self, pid: int) -> str:
        r = self.c.execute("SELECT items FROM stock WHERE product_id=?",(pid,)).fetchone()
        if not r or not r[0].strip(): return "(없음)"
        lines = [x for x in r[0].split("\n") if x.strip()]
        return "\n".join(lines[:3]) + (f"\n... 외 {len(lines)-3}개" if len(lines)>3 else "")
    def pop_stock(self, pid: int, qty: int) -> list[str]:
        r = self.c.execute("SELECT items FROM stock WHERE product_id=?",(pid,)).fetchone()
        if not r or not r[0].strip(): return []
        lines = [x for x in r[0].split("\n") if x.strip()]
        if len(lines) < qty: return []
        taken, rest = lines[:qty], lines[qty:]
        self.c.execute("UPDATE stock SET items=? WHERE product_id=?",("\n".join(rest),pid)); self.c.commit()
        return taken

    # 유저
    def ensure_user(self, uid: int):
        self.c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)",(str(uid),)); self.c.commit()
    def get_user(self, uid: int) -> dict:
        self.ensure_user(uid)
        r = self.c.execute("SELECT user_id,balance,total_spent,discount_rate FROM users WHERE user_id=?",(str(uid),)).fetchone()
        return {"user_id":r[0],"balance":r[1],"total_spent":r[2],"discount_rate":r[3]}
    def add_balance(self, uid: int, delta: int):
        self.ensure_user(uid)
        self.c.execute("UPDATE users SET balance=MAX(0,balance+?) WHERE user_id=?",(delta,str(uid))); self.c.commit()
    def set_balance(self, uid: int, amt: int):
        self.ensure_user(uid)
        self.c.execute("UPDATE users SET balance=? WHERE user_id=?",(max(0,amt),str(uid))); self.c.commit()
    def add_spent(self, uid: int, amt: int):
        self.ensure_user(uid)
        self.c.execute("UPDATE users SET total_spent=total_spent+? WHERE user_id=?",(amt,str(uid))); self.c.commit()
        self._refresh_discount(uid)
    def _refresh_discount(self, uid: int):
        u = self.get_user(uid)
        best = 0.0
        for r in sorted(self.get_roles(), key=lambda x: x["min_amount"], reverse=True):
            if u["total_spent"] >= r["min_amount"] and r["discount_rate"] > best:
                best = r["discount_rate"]; break
        self.c.execute("UPDATE users SET discount_rate=? WHERE user_id=?",(best,str(uid))); self.c.commit()

    # 충전
    def new_charge(self, uid: int, amt: int, method: str, dep=None) -> int:
        cur = self.c.execute(
            "INSERT INTO charge_history(user_id,amount,method,depositor,status,created_at) VALUES(?,?,?,?,?,?)",
            (str(uid),amt,method,dep,"pending",_iso(_now())))
        self.c.commit(); return cur.lastrowid
    def confirm_charge(self, cid: int) -> Optional[dict]:
        r = self.c.execute("SELECT * FROM charge_history WHERE id=? AND status='pending'",(cid,)).fetchone()
        if not r: return None
        data = dict(zip(_cols(self.c,"charge_history"),r))
        self.c.execute("UPDATE charge_history SET status='confirmed',confirmed_at=? WHERE id=?",(_iso(_now()),cid))
        self.c.commit(); return data
    def cancel_charge(self, cid: int):
        self.c.execute("UPDATE charge_history SET status='cancelled' WHERE id=? AND status='pending'",(cid,)); self.c.commit()
    def recent_charges(self, uid: int, n=10) -> list[dict]:
        rows = self.c.execute(
            "SELECT id,amount,method,depositor,status,created_at FROM charge_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (str(uid),n)).fetchall()
        return [{"id":r[0],"amount":r[1],"method":r[2],"depositor":r[3],"status":r[4],"date":r[5]} for r in rows]
    def pending_by_dep(self, dep: str, amt: int) -> Optional[dict]:
        r = self.c.execute(
            "SELECT * FROM charge_history WHERE depositor=? AND amount=? AND status='pending' ORDER BY created_at DESC LIMIT 1",
            (dep,amt)).fetchone()
        return dict(zip(_cols(self.c,"charge_history"),r)) if r else None
    def all_pending(self) -> list[dict]:
        rows = self.c.execute(
            "SELECT id,user_id,amount,depositor,created_at FROM charge_history WHERE status='pending' ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        return [{"id":r[0],"user_id":r[1],"amount":r[2],"depositor":r[3],"date":r[4]} for r in rows]

    # 구매
    def new_purchase(self, uid: int, pid: int, pname: str, price: int, qty: int) -> int:
        cur = self.c.execute(
            "INSERT INTO purchase_history(user_id,product_id,product_name,price,quantity,created_at) VALUES(?,?,?,?,?,?)",
            (str(uid),pid,pname,price,qty,_iso(_now())))
        self.c.commit(); return cur.lastrowid
    def recent_purchases(self, uid: int, n=10) -> list[dict]:
        rows = self.c.execute(
            "SELECT id,product_name,price,quantity,created_at FROM purchase_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (str(uid),n)).fetchall()
        return [{"id":r[0],"name":r[1],"price":r[2],"qty":r[3],"date":r[4]} for r in rows]

    # 후기
    def new_review(self, uid: int, purchase_id: int, stars: int, content: str) -> int:
        cur = self.c.execute(
            "INSERT INTO reviews(user_id,purchase_id,stars,content,created_at) VALUES(?,?,?,?,?)",
            (str(uid),purchase_id,stars,content,_iso(_now())))
        self.c.commit(); return cur.lastrowid

    # 웹훅
    def set_wh(self, log_type: str, url: str): self.c.execute("INSERT OR REPLACE INTO webhooks VALUES(?,?)",(log_type,url)); self.c.commit()
    def get_wh(self, log_type: str) -> Optional[str]:
        r = self.c.execute("SELECT webhook_url FROM webhooks WHERE log_type=?",(log_type,)).fetchone()
        return r[0] if r else None

    # 자판기 메시지
    def save_vmsg(self, ch_id: int, msg_id: int): self.c.execute("INSERT OR REPLACE INTO vending_messages VALUES(?,?)",(str(ch_id),str(msg_id))); self.c.commit()
    def get_vmsg(self, ch_id: int) -> Optional[int]:
        r = self.c.execute("SELECT message_id FROM vending_messages WHERE channel_id=?",(str(ch_id),)).fetchone()
        return int(r[0]) if r else None
