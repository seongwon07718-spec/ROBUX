import sqlite3
from datetime import datetime

# 데이터베이스 초기화 (테이블이 없으면 생성)
def init_db():
    conn = sqlite3.connect('accounts.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            channel_id INTEGER PRIMARY KEY,
            seller_nick TEXT,
            buyer_nick TEXT,
            status TEXT DEFAULT 'ready',
            created_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# 거래 정보 저장 또는 업데이트
def save_trade_info(channel_id, seller, buyer):
    conn = sqlite3.connect('accounts.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO trades (channel_id, seller_nick, buyer_nick, created_at)
        VALUES (?, ?, ?, ?)
    ''', (channel_id, seller, buyer, datetime.now()))
    conn.commit()
    conn.close()

# 특정 채널의 거래 정보 가져오기
def get_trade_info(channel_id):
    conn = sqlite3.connect('accounts.db')
    cursor = conn.cursor()
    cursor.execute('SELECT seller_nick, buyer_nick, status FROM trades WHERE channel_id = ?', (channel_id,))
    result = cursor.fetchone()
    conn.close()
    return result
