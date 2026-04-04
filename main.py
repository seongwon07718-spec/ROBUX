if __name__ == "__main__":
    import sqlite3
    
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0] if row else None)
    universe_id = 606849621  # Jailbreak
    
    urls = [
        # ✅ 2025년 8월 이후 공식 새 엔드포인트
        f"https://apis.roblox.com/game-passes/v1/universes/{universe_id}/game-passes?passView=Full&limit=100",
        # ✅ roproxy 경유
        f"https://apis.roproxy.com/game-passes/v1/universes/{universe_id}/game-passes?passView=Full&limit=100",
    ]
    
    for url in urls:
        resp = api.session.get(url)
        print(f"\nURL: {url}")
        print(f"status: {resp.status_code}")
        print(f"body: {resp.text[:500]}")
