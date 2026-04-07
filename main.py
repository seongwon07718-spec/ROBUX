        cur.execute("""
            CREATE TABLE IF NOT EXISTS gift_queue (
                order_id TEXT PRIMARY KEY,
                target_id INTEGER,
                pass_id INTEGER,
                status TEXT DEFAULT 'processing',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
