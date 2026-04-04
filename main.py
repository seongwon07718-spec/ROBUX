if __name__ == "__main__":
    import sqlite3
    
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0] if row else None)
    user_id = 5725475  # Litozinnamon
    
    # details API로 전체 데이터 확인
    url = f"https://catalog.roblox.com/v1/search/items/details?Category=34&CreatorType=User&CreatorTargetId={user_id}&limit=30"
    resp = api.session.get(url)
    body = resp.json()
    
    print("전체 itemType 목록:")
    for item in body.get("data", []):
        print(f"  id={item.get('id')} itemType={item.get('itemType')} assetType={item.get('assetType')} name={item.get('name')} price={item.get('price')}")
