def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # ... 다른 테이블 생성 코드들 ...

    # buy_log 테이블 수정 (web_key 추가)
    cursor.execute('''CREATE TABLE IF NOT EXISTS buy_log 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT, 
                      product_name TEXT, 
                      stock_data TEXT, 
                      date TEXT,
                      web_key TEXT)''') 
    conn.commit()
    conn.close()
