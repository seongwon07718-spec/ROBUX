# helpers_db.py
import sqlite3, os, json
from datetime import datetime
from threading import Lock

DB_PATH = 'DB/buy_panel.db'
JSON_DUMP = 'db.json'
_lock = Lock()

def init_db():
    os.makedirs('DB', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS bank_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        bank_name TEXT,
        account_number TEXT,
        created_at TEXT
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS coin_addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        coin TEXT,
        address TEXT,
        created_at TEXT,
        UNIQUE(user_id, coin)
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        bank_id INTEGER,
        coin TEXT,
        address TEXT,
        txid TEXT,
        amount REAL,
        currency TEXT,
        status TEXT,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()
    dump_json()

def _connect():
    return sqlite3.connect(DB_PATH)

def _atomic_write_json(data):
    tmp = JSON_DUMP + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, JSON_DUMP)

def dump_json():
    with _lock:
        conn = _connect(); c = conn.cursor()
        out = {}
        c.execute('SELECT id, user_id, bank_name, account_number, created_at FROM bank_accounts')
        out['bank_accounts'] = [dict(zip(['id','user_id','bank_name','account_number','created_at'], r)) for r in c.fetchall()]
        c.execute('SELECT id, user_id, coin, address, created_at FROM coin_addresses')
        out['coin_addresses'] = [dict(zip(['id','user_id','coin','address','created_at'], r)) for r in c.fetchall()]
        c.execute('SELECT id, user_id, bank_id, coin, address, txid, amount, currency, status, created_at FROM purchases')
        out['purchases'] = [dict(zip(['id','user_id','bank_id','coin','address','txid','amount','currency','status','created_at'], r)) for r in c.fetchall()]
        conn.close()
        _atomic_write_json(out)

# CRUD
def save_bank_info(user_id, bank_name, account_number):
    conn = _connect(); c = conn.cursor()
    c.execute('INSERT INTO bank_accounts (user_id, bank_name, account_number, created_at) VALUES (?, ?, ?, ?)',
              (user_id, bank_name, account_number, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    bid = c.lastrowid
    conn.close()
    dump_json()
    return bid

def get_user_banks(user_id):
    conn = _connect(); c = conn.cursor()
    c.execute('SELECT id, bank_name, account_number, created_at FROM bank_accounts WHERE user_id = ? ORDER BY id DESC', (user_id,))
    rows = c.fetchall(); conn.close()
    return [{'id': r[0], 'bank_name': r[1], 'account_number': r[2], 'created_at': r[3]} for r in rows]

def set_coin_address(user_id, coin, address):
    conn = _connect(); c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO coin_addresses (user_id, coin, address, created_at) VALUES (?, ?, ?, ?)',
              (user_id, coin.upper(), address, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit(); conn.close(); dump_json()

def get_coin_address(user_id, coin):
    conn = _connect(); c = conn.cursor()
    c.execute('SELECT address FROM coin_addresses WHERE user_id = ? AND coin = ?', (user_id, coin.upper()))
    row = c.fetchone(); conn.close()
    return row[0] if row else None

def save_purchase(user_id, bank_id, coin, address, txid, amount, currency='KRW', status='pending'):
    conn = _connect(); c = conn.cursor()
    c.execute('INSERT INTO purchases (user_id, bank_id, coin, address, txid, amount, currency, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
              (user_id, bank_id, coin.upper() if coin else None, address, txid, amount, currency, status, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit(); rec = c.lastrowid; conn.close(); dump_json()
    return rec
