def get_user_places(self, user_id: int) -> list[dict]:
    games = []
    cursor = ""
    while True:
        url = f"https://games.roblox.com/v2/users/{user_id}/games?limit=50&sortOrder=Asc"
        if cursor:
            url += f"&cursor={cursor}"
        resp = self.session.get(url)
        if resp.status_code != 200:
            break
        body = resp.json()
        for g in body.get("data", []):
            root_place = g.get("rootPlace") or {}
            universe_id = g.get("id")          # ✅ Universe ID (게임패스 조회용)
            root_place_id = root_place.get("id")  # Place ID (다른 용도)
            print(f"[게임] name={g.get('name')} universe_id={universe_id} rootPlaceId={root_place_id}")
            games.append({
                "id": universe_id,             # ✅ 반드시 Universe ID여야 함
                "name": g.get("name") or "이름 없는 게임",
                "rootPlaceId": root_place_id,
            })
        cursor = body.get("nextPageCursor") or ""
        if not cursor:
            break
    return games
