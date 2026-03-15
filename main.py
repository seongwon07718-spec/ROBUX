import sqlite3
import time

DB_NAME = "vending_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
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
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS products 
                     (category TEXT,
                      name TEXT PRIMARY KEY,
                      price INTEGER,
                      stock INTEGER,
                      stock_data TEXT DEFAULT '')""")
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN stock_data TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""CREATE TABLE IF NOT EXISTS products 
                     (category TEXT,
                      name TEXT PRIMARY KEY,
                      price INTEGER,
                      stock INTEGER,
                      stock_data TEXT DEFAULT '',
                      sold_count INTEGER DEFAULT 0)""")
    
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN sold_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass 

    conn.commit()
    conn.close()

def process_purchase(user_id, product_name):
    """구매 성공 시 재고 차감 및 누적 판매량 증가"""
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()
    
    cur.execute("SELECT stock_data FROM products WHERE name = ?", (product_name,))
    res = cur.fetchone()
    if not res or not res[0]:
        return None 
    
    stock_list = res[0].split('\n')
    item_to_sell = stock_list[0]
    remaining_stock = "\n".join(stock_list[1:])
    
    cur.execute("""UPDATE products 
                   SET stock = stock - 1, 
                       sold_count = sold_count + 1, 
                       stock_data = ? 
                   WHERE name = ?""", (remaining_stock, product_name))
    
    conn.commit()
    conn.close()
    return item_to_sell

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

def get_history(user_id, limit=5):
    """최근 5개의 완료된 충전 내역을 가져옵니다."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT amount, date FROM charge_logs 
        WHERE user_id = ? 
        ORDER BY date DESC LIMIT ?
    """, (str(user_id), limit))
    res = cursor.fetchall()
    conn.close()
    return res

init_db()
