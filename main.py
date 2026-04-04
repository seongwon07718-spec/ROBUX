if __name__ == "__main__":
    import sqlite3
    
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0])
    
    # 쿠키 계정 잔액 확인
    resp = api.session.get("https://economy.roblox.com/v1/users/authenticated/robux-balance")
    print(f"잔액확인: {resp.status_code} {resp.text}")
    
    # 계정 정보 확인  
    resp2 = api.session.get("https://users.roblox.com/v1/users/authenticated")
    print(f"계정정보: {resp2.status_code} {resp2.text}")
