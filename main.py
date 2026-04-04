if __name__ == "__main__":
    import sqlite3
    
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0] if row else None)
    test_universe = 29407759
    
    urls = [
        # 최신 API 후보들
        f"https://games.roblox.com/v1/games/{test_universe}/game-passes?limit=100&sortOrder=Asc",
        f"https://apis.roblox.com/game-passes/v1/games/{test_universe}/game-passes?limit=100",
        f"https://economy.roblox.com/v2/game-passes?universeId={test_universe}&limit=100",
        f"https://itemconfiguration.roblox.com/v1/creations/get-assets?assetType=GamePass&isArchived=false&groupId={test_universe}&limit=100",
        f"https://www.roblox.com/api/game-pass/game/{test_universe}/game-pass-page?pageNumber=1",
    ]
    
    for url in urls:
        resp = api.session.get(url)
        print(f"\nURL: {url}")
        print(f"status: {resp.status_code}")
        print(f"body: {resp.text[:300]}")
