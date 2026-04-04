if __name__ == "__main__":
    import sqlite3
    
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0] if row else None)
    
    # 게임패스 있는 유명 유저들
    test_users = ["Badimo", "asimo3089"]
    
    for username in test_users:
        uid = api.get_user_id(username)
        print(f"\n{username} ID: {uid}")
        
        url = f"https://catalog.roblox.com/v1/search/items/details?Category=34&CreatorType=User&CreatorTargetId={uid}&limit=30"
        resp = api.session.get(url)
        body = resp.json()
        
        for item in body.get("data", []):
            at = item.get("assetType")
            if at == 34:  # GamePass만
                print(f"  ✅ 게임패스! id={item.get('id')} name={item.get('name')} price={item.get('price')}")
            else:
                print(f"  ❌ assetType={at} name={item.get('name')}")
