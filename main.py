if __name__ == "__main__":
    import sqlite3
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0])
    
    # x-bound-auth-token 먼저 가져오기
    auth_resp = api.session.post(
        "https://apis.roblox.com/hba-service/v1/getServerNonce"
    )
    print(f"nonce: {auth_resp.status_code} {auth_resp.text}")
    
    bound_resp = api.session.post(
        "https://apis.roblox.com/hba-service/v1/getBoundAuthToken",
        json={"serverNonce": auth_resp.text.strip('"')}
    )
    print(f"bound: {bound_resp.status_code} {bound_resp.text}")
