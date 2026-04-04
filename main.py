if __name__ == "__main__":
    import sqlite3
    
    with sqlite3.connect("robux_shop.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
    
    api = RobloxAPI(row[0])
    my_id = 7941150727  # amp_AlexisGod
    
    urls = [
        f"https://economy.roblox.com/v1/users/{my_id}/currency",
        f"https://economy.roblox.com/v2/users/{my_id}/transaction-totals?timeFrame=Year&transactionType=summary",
        "https://economy.roblox.com/v1/user/currency",
    ]
    
    for url in urls:
        resp = api.session.get(url)
        print(f"status={resp.status_code} body={resp.text[:200]}")
        print(f"URL: {url}\n")
