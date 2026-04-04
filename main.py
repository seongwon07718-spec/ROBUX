if __name__ == "__main__":
    import sqlite3
    
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0] if row else None)
    
    # itemconfiguration - creatorId 방식으로 시도
    # Litozinnamon 유저 ID로 직접 조회
    creator_id = 55516750  # Litozinnamon 유저ID
    
    urls = [
        f"https://itemconfiguration.roblox.com/v1/creations/get-assets?assetType=GamePass&isArchived=false&limit=100",
        f"https://apis.roblox.com/toolbox-service/v1/marketplace?assetType=GamePass&creatorType=User&creatorTargetId={creator_id}&limit=100",
        f"https://catalog.roblox.com/v1/search/items?Category=34&CreatorType=User&CreatorTargetId={creator_id}&limit=30",
    ]
    
    for url in urls:
        resp = api.session.get(url)
        print(f"\nURL: {url}")
        print(f"status: {resp.status_code}")
        print(f"body: {resp.text[:400]}")
