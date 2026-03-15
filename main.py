def init_db():
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()
    
    # 제품 테이블 생성 (sold_count 추가)
    cur.execute("""CREATE TABLE IF NOT EXISTS products 
                     (category TEXT,
                      name TEXT PRIMARY KEY,
                      price INTEGER,
                      stock INTEGER,
                      stock_data TEXT DEFAULT '',
                      sold_count INTEGER DEFAULT 0)""")
    
    # 기존 DB 파일에 sold_count 컬럼이 없는 경우 강제 추가
    try:
        cur.execute("ALTER TABLE products ADD COLUMN sold_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass 

    conn.commit()
    conn.close()
