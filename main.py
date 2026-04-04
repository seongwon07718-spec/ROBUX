def get_place_gamepasses(self, universe_id: int) -> list[dict]:
    """
    catalog v2 API - GamePass만 필터링해서 조회
    """
    passes = []
    cursor = ""
    while True:
        url = (
            f"https://catalog.roblox.com/v2/search/items/details"
            f"?Category=34&universeId={universe_id}&limit=30"
        )
        if cursor:
            url += f"&cursor={cursor}"
        resp = self.session.get(url)
        print(f"[게임패스v2] status={resp.status_code} body={resp.text[:500]}")
        
        if resp.status_code != 200:
            break
            
        body = resp.json()
        for p in body.get("data", []):
            # GamePass만 필터
            if p.get("itemType") != "GamePass":
                continue
            passes.append({
                "id": p.get("id"),
                "name": p.get("name") or "이름 없음",
                "price": p.get("price") or 0,
            })
        cursor = body.get("nextPageCursor") or ""
        if not cursor:
            break
    
    print(f"[게임패스 최종] {passes}")
    return passes
