if __name__ == "__main__":
    import sqlite3
    
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0] if row else None)
    user_id = 5725475  # Litozinnamon
    
    url = f"https://catalog.roblox.com/v1/search/items?Category=34&SubCategory=40&CreatorType=User&CreatorTargetId={user_id}&limit=30"
    resp = api.session.get(url)
    print(f"status: {resp.status_code}")
    print(f"body: {resp.text}")
