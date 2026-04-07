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
