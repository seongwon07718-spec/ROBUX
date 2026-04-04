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
            # isPublic 체크 제거 (API가 이미 공개 게임만 반환)
            root_place = g.get("rootPlace") or {}
            games.append({
                "id": g.get("id"),  # Universe ID
                "name": g.get("name") or "이름 없는 게임",
                "rootPlaceId": root_place.get("id"),  # ✅ 중첩 구조 수정
            })
        cursor = body.get("nextPageCursor") or ""
        if not cursor:
            break
    return games
