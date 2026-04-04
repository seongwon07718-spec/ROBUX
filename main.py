if __name__ == "__main__":
    import sqlite3
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0])
    result = api.buy_gamepass(113083961)
    print(f"결과: {result}")
