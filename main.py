import sqlite3
import time

DB_NAME = "vending_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # ... (기존 users, requests, charge_logs 테이블 코드는 동일)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                     (user_id TEXT PRIMARY KEY, 
                      money INTEGER DEFAULT 0, 
                      total_spent INTEGER DEFAULT 0, 
                      is_blacked INTEGER DEFAULT 0)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS requests 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      user_id TEXT, 
                      amount TEXT, 
                      status TEXT, 
                      timestamp REAL)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS charge_logs 
                     (user_id TEXT, 
                      amount INTEGER, 
                      date TEXT, 
                      method TEXT)''')
    
    # [수정] products 테이블에 stock_data 컬럼 추가
    cursor.execute("""CREATE TABLE IF NOT EXISTS products 
                     (category TEXT,
                      name TEXT PRIMARY KEY,
                      price INTEGER,
                      stock INTEGER,
                      stock_data TEXT DEFAULT '')""") # 이 줄을 추가했습니다.
    
    # [중요] 기존에 이미 DB가 생성된 경우를 위해 컬럼 존재 여부 확인 후 추가
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN stock_data TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        # 이미 컬럼이 존재하면 무시합니다.
        pass

    conn.commit()
    conn.close()

# 나머지 함수들(insert_request 등)은 그대로 두시면 됩니다.
init_db()
