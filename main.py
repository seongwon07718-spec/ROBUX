def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id TEXT,
                amount INTEGER,
                robux INTEGER,
                status TEXT,
                roblox_name TEXT DEFAULT '',
                roblox_id TEXT DEFAULT '',
                gamepass_name TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE TABLE IF NOT EXISTS vending_messages (channel_id TEXT PRIMARY KEY, msg_id TEXT)")

        # 기존 DB 컬럼 추가 (없으면 추가)
        for col in ["roblox_name", "roblox_id", "gamepass_name"]:
            try:
                cur.execute(f"ALTER TABLE orders ADD COLUMN {col} TEXT DEFAULT ''")
            except Exception:
                pass

        conn.commit()

init_db()
