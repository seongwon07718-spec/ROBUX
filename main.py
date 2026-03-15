def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # [임시 추가] 기존 테이블을 삭제해서 구조를 새로 잡습니다.
    cursor.execute("DROP TABLE IF EXISTS buy_log") 
    
    # 다시 테이블 생성 (여기에 web_key가 포함되어 있어야 함)
    cursor.execute('''CREATE TABLE IF NOT EXISTS buy_log 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT, 
                      product_name TEXT, 
                      stock_data TEXT, 
                      date TEXT,
                      web_key TEXT)''')
    conn.commit()
    conn.close()
