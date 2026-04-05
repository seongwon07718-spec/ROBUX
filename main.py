if __name__ == "__main__":
    import sqlite3
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0])
    
    resp = api.session.get(
        "https://apis.roblox.com/game-passes/v1/game-passes/1784490889/details"
    )
    data = resp.json()
    print(f"enabledFeatures: {data.get('enabledFeatures')}")
    print(f"priceInformation: {data.get('priceInformation')}")
    print(f"전체: {data}")
