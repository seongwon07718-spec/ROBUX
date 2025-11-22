import sqlite3
import os
from datetime import datetime

os.makedirs('DB', exist_ok=True)
conn = sqlite3.connect('DB/buy_panel.db')
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS bank_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    bank_name TEXT,
    account_number TEXT,
    created_at TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS coin_addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    coin TEXT,
    address TEXT,
    created_at TEXT,
    UNIQUE(user_id, coin)
)
''')

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
)
''')

conn.commit()
conn.close()
print(f"DB 초기화 완료: DB/buy_panel.db (생성 시간: {datetime.now().isoformat()})")
