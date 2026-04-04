if __name__ == "__main__":
    import sqlite3
    
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0] if row else None)
    user_id = 5725475  # Litozinnamon
    
    # GamePass = assetType 34
    urls = [
        f"https://catalog.roblox.com/v1/search/items/details?Category=34&CreatorType=User&CreatorTargetId={user_id}&limit=30",
        f"https://catalog.roblox.com/v1/search/items?assetType=GamePass&CreatorType=User&CreatorTargetId={user_id}&limit=30",
        f"https://economy.roblox.com/v1/assets?assetType=34&userId={user_id}&limit=100",
    ]
    
    for url in urls:
        resp = api.session.get(url)
        print(f"\nURL: {url}")
        print(f"status: {resp.status_code}")
        print(f"body: {resp.text[:400]}")
