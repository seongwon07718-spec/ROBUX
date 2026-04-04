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
        print(f"[게임패스] status={resp.status_code} body={resp.text}")  # 디버그
        if resp.status_code != 200:
            break
        body = resp.json()
        for p in body.get("data", []):
            print(f"[패스항목] {p}")  # 구조 확인용
            # price가 없어도 일단 전부 추가해서 확인
            passes.append({
                "id": p.get("id"),
                "name": p.get("name") or "이름 없음",
                # price 중첩 가능성 대비 - 여러 경로 시도
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
    print(f"[게임패스 최종] {passes}")
    return passes
