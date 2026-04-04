if __name__ == "__main__":
    import sqlite3
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0])
    
    # Jailbreak VIP 게임패스 - RegionalPricing 없는 유명 게임패스
    test_passes = [
        109156388,  # Jailbreak VIP
        32750592,   # Jailbreak Criminal
    ]
    
    for pid in test_passes:
        resp = api.session.get(
            f"https://apis.roblox.com/game-passes/v1/game-passes/{pid}/details"
        )
        if resp.status_code == 200:
            data = resp.json()
            features = data.get("enabledFeatures", [])
            price_info = data.get("priceInformation") or {}
            price = price_info.get("defaultPriceInRobux") or price_info.get("price") or 0
            print(f"pass_id={pid} name={data.get('name')} price={price} features={features}")
        else:
            print(f"pass_id={pid} status={resp.status_code}")
