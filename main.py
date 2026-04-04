def get_place_gamepasses(self, universe_id: int) -> list[dict]:
    passes = []
    cursor = ""
    while True:
        url = (
            f"https://games.roblox.com/v1/games/{universe_id}/game-passes"
            f"?limit=100&sortOrder=Asc"
        )
        if cursor:
            url += f"&cursor={cursor}"
        resp = self.session.get(url)
        
        # ✅ 404 = 게임패스 없음, 정상 처리
        if resp.status_code == 404:
            break
        if resp.status_code != 200:
            print(f"[게임패스 오류] status={resp.status_code}")
            break
            
        body = resp.json()
        for p in body.get("data", []):
            passes.append({
                "id": p.get("id"),
                "name": p.get("name") or "이름 없음",
                "price": (
                    p.get("price")
                    or p.get("product", {}).get("priceInRobux")
                    or p.get("priceInRobux")
                    or 0
                ),
            })
        cursor = body.get("nextPageCursor") or ""
        if not cursor:
            break
    return passes
