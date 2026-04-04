if __name__ == "__main__":
    import sqlite3
    
    # DB에서 쿠키 꺼내서 인증된 세션으로 시도
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    cookie = row[0] if row else None
    print(f"쿠키 있음: {bool(cookie)}")
    
    api = RobloxAPI(cookie)  # 인증된 세션
    test_universe = 29407759
    
    urls = [
        f"https://games.roblox.com/v1/games/{test_universe}/game-passes?limit=100",
        f"https://www.roblox.com/games/get-game-passes?gameId={test_universe}&page=1&pageSize=100",
    ]
    
    for url in urls:
        resp = api.session.get(url)
        print(f"\nURL: {url}")
        print(f"status: {resp.status_code}")
        print(f"body: {resp.text[:400]}")
