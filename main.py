# data/database.py
import sqlite3

DATABASE_NAME = 'bot_data.db'

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # users 테이블: 사용자 계좌 정보 관리
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            depositor_name TEXT NOT NULL,
            account_number TEXT NOT NULL
        )
    ''')

    # user_coin_addresses 테이블: 관리자가 설정한 사용자별 코인 주소
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_coin_addresses (
            user_id INTEGER,
            coin_type TEXT NOT NULL,
            address TEXT NOT NULL,
            PRIMARY KEY (user_id, coin_type)
        )
    ''')

    # transactions 테이블: 매입 거래 내역 관리
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            coin_type TEXT NOT NULL,
            amount_coin REAL,           -- 실제 입금된 코인량
            amount_krw REAL,            -- 코인량을 KRW로 환산한 금액
            txid TEXT,                  -- 유저가 제출한 TXID
            deposit_txid TEXT,          -- API로 감지된 실제 입금 TXID
            status TEXT NOT NULL,       -- 'pending_account', 'pending_coin_select', 'pending_txid', 'txid_submitted', 'deposit_detected', 'completed', 'cancelled'
            discord_dm_message_id INTEGER, -- 유저 DM에 보내진 임베드 메시지 ID
            discord_admin_message_id INTEGER, -- 관리자 채널에 보내진 임베드 메시지 ID
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    conn.commit()
    conn.close()

# 데이터베이스 연결 함수
def get_db_connection():
    return sqlite3.connect(DATABASE_NAME)

# 스크립트 로드 시 데이터베이스 초기화
init_db()

print("데이터베이스 초기화 스크립트 로드 완료.")
