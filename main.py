if __name__ == "__main__":
    import sqlite3
    
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0] if row else None)
    
    # 1. 실제 유저ID 먼저 확인
    user_id = api.get_user_id("Litozinnamon")
    print(f"Litozinnamon 유저ID: {user_id}")
    
    # 2. 게임 목록에서 universe_id 확인
    places = api.get_user_places(user_id)
    for p in places:
        print(f"게임: {p['name']} universe_id={p['id']}")
    
    # 3. 첫번째 게임으로 itemconfiguration 시도
    if places:
        uid = places[0]['id']
        url = f"https://itemconfiguration.roblox.com/v1/creations/get-assets?assetType=GamePass&isArchived=false&limit=100"
        resp = api.session.get(url)
        print(f"\nitemconfig status: {resp.status_code}")
        print(f"body: {resp.text[:500]}")
        
        # catalog도 유저ID로 시도
        url2 = f"https://catalog.roblox.com/v1/search/items?Category=34&CreatorType=User&CreatorTargetId={user_id}&limit=30"
        resp2 = api.session.get(url2)
        print(f"\ncatalog status: {resp2.status_code}")
        print(f"body: {resp2.text[:500]}")
