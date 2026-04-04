if __name__ == "__main__":
    import sqlite3
    
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0] if row else None)
    
    # asimo3089 유저ID = 2837719
    creator_id = 2837719
    start_id = ""
    
    url = f"https://apis.roblox.com/game-passes/v1/users/{creator_id}/game-passes?count=100&exclusiveStartId={start_id}"
    resp = api.session.get(url)
    print(f"status: {resp.status_code}")
    print(f"body: {resp.text[:800]}")
