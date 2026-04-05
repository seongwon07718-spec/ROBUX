    try:
        driver.get("https://www.roblox.com")
        time.sleep(2)

        clean_cookie = cookie.strip()
        if "=" in clean_cookie:
            clean_cookie = clean_cookie.split("=", 1)[-1]
        driver.add_cookie({
            "name": ".ROBLOSECURITY",
            "value": clean_cookie,
            "domain": ".roblox.com",
            "path": "/",
        })

        # ✅ Selenium 없이 API로 먼저 소유 여부 확인
        import requests
        session = requests.Session()
        session.cookies.set(".ROBLOSECURITY", clean_cookie, domain=".roblox.com")
        me = session.get("https://users.roblox.com/v1/users/authenticated").json()
        my_id = me.get("id")
        if my_id:
            own_resp = session.get(
                f"https://inventory.roblox.com/v1/users/{my_id}/items/GamePass/{pass_id}"
            ).json()
            if own_resp.get("data"):
                return {"purchased": False, "reason": "이미 소유 중인 게임패스"}

        driver.get(f"https://www.roblox.com/game-pass/{pass_id}/")
        time.sleep(4)
        # 나머지 코드...
