if __name__ == "__main__":
    import sqlite3
    
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0] if row else None)
    
    # Jailbreak universe_id = 606849621 (게임패스 많은 유명 게임)
    universe_id = 606849621
    
    urls = [
        f"https://games.roblox.com/v1/games/{universe_id}/game-passes?limit=100",
        f"https://www.roblox.com/games/{universe_id}/game-pass/get-game-passes?pageNumber=1",
        f"https://apis.roblox.com/universes/v1/{universe_id}/game-passes?limit=100",
    ]
    
    for url in urls:
        resp = api.session.get(url)
        print(f"\nURL: {url}")
        print(f"status: {resp.status_code}")
        print(f"body: {resp.text[:400]}")
