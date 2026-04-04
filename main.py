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
            if resp.status_code != 200:
                break
            body = resp.json()
            for p in body.get("data", []):
                if p.get("price") is not None:
                    passes.append(p)
            cursor = body.get("nextPageCursor") or ""
            if not cursor:
                break
        return passes

    # ── 게임패스 상품 정보 ────────────────────────────────────────────────────
    def get_gamepass_product_info(self, pass_id: int) -> dict | None:
        resp = self.session.get(
            f"https://economy.roblox.com/v1/game-pass/{pass_id}/product-info"
        )
        return resp.json() if resp.status_code == 200 else None
