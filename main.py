python -c "import sqlite3; conn = sqlite3.connect('robux_shop.db'); conn.execute('CREATE TABLE IF NOT EXISTS vending_messages (channel_id TEXT PRIMARY KEY, msg_id TEXT)'); conn.commit(); print('완료')"
