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
                      stock_data TEXT DEFAULT '',
                      sold_count INTEGER DEFAULT 0)""")
    
    columns = [row[1] for row in cursor.execute("PRAGMA table_info(products)")]
    if "stock_data" not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN stock_data TEXT DEFAULT ''")
    if "sold_count" not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN sold_count INTEGER DEFAULT 0")

    cursor.execute("DROP TABLE IF EXISTS buy_log") 
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS buy_log 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT, 
                      product_name TEXT, 
                      stock_data TEXT, 
                      date TEXT,
                      web_key TEXT)''')
    
    conn.commit()
    conn.close()

def process_purchase(user_id, product_name, buy_count=1):
    """
    구매 성공 시 재고 차감, 판매량 증가 및 구매 로그 저장
    (기존 함수를 확장하여 buy_log 저장까지 한 번에 처리하도록 수정 가능)
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    cur.execute("SELECT stock_data FROM products WHERE name = ?", (product_name,))
    res = cur.fetchone()
    if not res or not res[0]:
        conn.close()
        return None 
    
    stock_list = res[0].split('\n')
    if len(stock_list) < buy_count:
        conn.close()
        return None

    delivery_items = stock_list[:buy_count]
    purchased_text = "\n".join(delivery_items)
    remaining_stock = "\n".join(stock_list[buy_count:])
    
    cur.execute("""UPDATE products 
                   SET stock = stock - ?, 
                       sold_count = sold_count + ?, 
                       stock_data = ? 
                   WHERE name = ?""", (buy_count, buy_count, remaining_stock, product_name))

    cur.execute("INSERT INTO buy_log (user_id, product_name, stock_data, date) VALUES (?, ?, ?, ?)",
                (str(user_id), product_name, purchased_text, time.strftime('%Y-%m-%d %H:%M')))
    
    buy_id = cur.lastrowid
    conn.commit()
    conn.close()
    return buy_id, purchased_text

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
