if __name__ == "__main__":
    import sqlite3
    
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    cookie = row[0] if row else None
    api = RobloxAPI(cookie)
    
    creator_id = 2837719  # asimo3089
    
    # 방법 1: 쿠키 세션으로 시도
    url = f"https://apis.roblox.com/game-passes/v1/users/{creator_id}/game-passes?count=100&exclusiveStartId="
    resp = api.session.get(url)
    print(f"[방법1] status: {resp.status_code} body: {resp.text[:400]}")
    
    # 방법 2: Authorization 헤더 추가
    headers = {
        "Cookie": f".ROBLOSECURITY={cookie}",
        "Authorization": f"Bearer {cookie}",
    }
    resp2 = api.session.get(url, headers=headers)
    print(f"[방법2] status: {resp2.status_code} body: {resp2.text[:400]}")
    
    # 방법 3: roproxy 경유
    url3 = f"https://apis.roproxy.com/game-passes/v1/users/{creator_id}/game-passes?count=100&exclusiveStartId="
    resp3 = api.session.get(url3)
    print(f"[방법3] status: {resp3.status_code} body: {resp3.text[:400]}")
