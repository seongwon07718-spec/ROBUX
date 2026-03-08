import sqlite3
import time

DB_NAME = "charge_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS requests 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      user_id INTEGER, 
                      amount TEXT, 
                      status TEXT, 
                      timestamp REAL)''')
    conn.commit()
    conn.close()

def insert_request(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO requests (user_id, amount, status, timestamp) VALUES (?, ?, ?, ?)", 
                   (user_id, amount, "대기", time.time()))
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
    cursor.execute("SELECT timestamp FROM requests WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

init_db()
