def get_place_gamepasses(self, universe_id: int) -> list[dict]:
    """
    게임패스 조회 - marketplace API 사용
    """
    passes = []
    page = 1
    while True:
        url = (
            f"https://www.roblox.com/games/get-game-passes"
            f"?gameId={universe_id}&page={page}&pageSize=100"
        )
        resp = self.session.get(url)
        print(f"[게임패스] status={resp.status_code} body={resp.text[:500]}")
        
        if resp.status_code != 200:
            break
            
        body = resp.json()
        items = body if isinstance(body, list) else body.get("data", [])
        
        if not items:
            break
            
        for p in items:
            price = (
                p.get("Price")
                or p.get("price")
                or p.get("PriceInRobux")
                or 0
            )
            name = (
                p.get("Name")
                or p.get("name")
                or "이름 없음"
            )
            pid = p.get("PassId") or p.get("id") or p.get("Id")
            
            if pid and price > 0:
                passes.append({
                    "id": pid,
                    "name": name,
                    "price": price,
                })
        
        if len(items) < 100:
            break
        page += 1
    
    print(f"[게임패스 최종] {passes}")
    return passes
