if __name__ == "__main__":
    import sqlite3
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0])
    
    # s_w0nx 게임패스 (RegionalPricing 있음)
    pass_id = 1784490889
    
    token = api.get_csrf_token()
    headers = {
        "x-csrf-token": token,
        "Content-Type": "application/json",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com",
    }
    
    resp = api.session.post(
        f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/purchase",
        json={"expectedPrice": 0},
        headers=headers,
    )
    print(f"status: {resp.status_code}")
    print(f"body: {resp.text}")
