import sqlite3
from datetime import datetime

conn = sqlite3.connect('verified_users.db')
cursor = conn.cursor()

# 테이블 생성 (한 번만)
cursor.execute('''
CREATE TABLE IF NOT EXISTS verified_users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    verified_at TEXT
)
''')
conn.commit()

def save_verified_user(user_id: int, username: str):
    verified_at = datetime.utcnow().isoformat()
    cursor.execute('''
    INSERT INTO verified_users(user_id, username, verified_at)
    VALUES (?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
    username=excluded.username,
    verified_at=excluded.verified_at
    ''', (user_id, username, verified_at))
    conn.commit()
