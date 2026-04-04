def get_place_gamepasses(self, universe_id: int) -> list[dict]:
    passes = []
    page_token = ""
    while True:
        url = (
            f"https://apis.roproxy.com/game-passes/v1/universes/{universe_id}/game-passes"
            f"?passView=Full&pageSize=100"
        )
        if page_token:
            url += f"&pageToken={page_token}"
        
        resp = self.session.get(url)
        if resp.status_code != 200:
            break
        
        body = resp.json()
        for p in body.get("gamePasses", []):
            price = p.get("price")
            pass_id = p.get("id")
            name = p.get("displayName") or p.get("name") or "이름 없음"
            
            if pass_id and price and price > 0:
                passes.append({
                    "id": pass_id,
                    "name": name,
                    "price": price,
                })
        
        page_token = body.get("nextPageToken") or ""
        if not page_token:
            break
    
    return passes
