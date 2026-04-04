def get_place_gamepasses(self, universe_id: int) -> list[dict]:
    """
    catalog API를 통해 게임패스 조회 (v1 games API 대체)
    """
    passes = []
    cursor = ""
    while True:
        url = (
            f"https://catalog.roblox.com/v1/search/items"
            f"?category=GamePass&creatorType=Group&limit=30"
            f"&universeId={universe_id}"
        )
        if cursor:
            url += f"&cursor={cursor}"
        resp = self.session.get(url)
        print(f"[catalog 시도] status={resp.status_code} body={resp.text[:300]}")
        
        if resp.status_code != 200:
            # 두번째 방법: itemdetails API 시도
            url2 = (
                f"https://games.roblox.com/v1/games/{universe_id}/game-passes"
                f"?limit=100"
            )
            resp2 = self.session.get(url2)
            print(f"[v1 시도] status={resp2.status_code} body={resp2.text[:300]}")
            break
            
        body = resp.json()
        for p in body.get("data", []):
            passes.append({
                "id": p.get("id"),
                "name": p.get("name") or "이름 없음",
                "price": p.get("price") or 0,
            })
        cursor = body.get("nextPageCursor") or ""
        if not cursor:
            break
    return passes
