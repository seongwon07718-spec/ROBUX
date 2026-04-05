if __name__ == "__main__":
    import sqlite3
    import requests

    # 브라우저에서 복사한 쿠키 직접 입력
    cookie = "여기에_복사한_쿠키_붙여넣기"
    
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    })
    
    # CSRF 토큰
    token = session.post("https://auth.roblox.com/v2/logout").headers.get("x-csrf-token")
    
    headers = {
        "x-csrf-token": token,
        "Content-Type": "application/json",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com",
    }
    
    resp = session.post(
        "https://apis.roblox.com/game-passes/v1/game-passes/1784490889/purchase",
        json={"expectedPrice": 5},
        headers=headers,
    )
    print(f"status: {resp.status_code}")
    print(f"body: {resp.text}")
