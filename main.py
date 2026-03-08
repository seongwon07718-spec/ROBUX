import sqlite3
import time

# 파일명을 하나로 통일하여 관리하는 것이 에러 방지에 좋습니다.
DB_NAME = "vending1.db" 

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 기존 유저 테이블
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                     (user_id TEXT PRIMARY KEY, 
                      money INTEGER DEFAULT 0, 
                      total_spent INTEGER DEFAULT 0, 
                      is_blacked INTEGER DEFAULT 0)''')
    
    # 충전 및 신청 기록 테이블
    cursor.execute('''CREATE TABLE IF NOT EXISTS requests 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      user_id TEXT, 
                      amount TEXT, 
                      status TEXT, 
                      timestamp REAL)''')
    conn.commit()
    conn.close()

def insert_request(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO requests (user_id, amount, status, timestamp) VALUES (?, ?, ?, ?)", 
                   (str(user_id), str(amount), "대기", time.time()))
    db_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return db_id

def update_status(db_id, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE requests SET status = ? WHERE id = ?", (status, db_id))
    conn.commit()
    conn.close()

def get_status(db_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM requests WHERE id = ?", (db_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def get_last_request_time(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp FROM requests WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (str(user_id),))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

# --- [정보 버튼 내역 조회를 위해 추가된 함수] ---

def get_history(user_id, limit=5):
    """최근 5개의 완료된 충전 내역을 가져옵니다."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # '완료'된 기록 중 최신순으로 정렬
    cursor.execute("""
        SELECT amount, timestamp FROM requests 
        WHERE user_id = ? AND status = '완료' 
        ORDER BY timestamp DESC LIMIT ?
    """, (str(user_id), limit))
    res = cursor.fetchall()
    conn.close()
    return res

init_db()
