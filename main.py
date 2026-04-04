    def get_gamepass_product_info(self, pass_id: int) -> dict | None:
        resp = self.session.get(
            f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        price_info = data.get("priceInformation") or {}
        price = (
            price_info.get("price")
            or price_info.get("defaultPriceInRobux")
            or 0
        )
        place_id = data.get("placeId")

        # ✅ placeId → universeId → 소유자 ID 조회
        creator_id = None
        if place_id:
            # place_id로 universe 정보 조회
            u_resp = self.session.get(
                f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
            )
            if u_resp.status_code == 200:
                universe_id = u_resp.json().get("universeId")
                if universe_id:
                    # universe 소유자 조회
                    g_resp = self.session.get(
                        f"https://games.roblox.com/v1/games?universeIds={universe_id}"
                    )
                    if g_resp.status_code == 200:
                        games = g_resp.json().get("data", [])
                        if games:
                            creator = games[0].get("creator", {})
                            creator_id = creator.get("id")

        print(f"[파싱] price={price} creator_id={creator_id}")
        return {
            "ProductId": data.get("gamePassId") or pass_id,
            "PriceInRobux": price,
            "Creator": {"Id": creator_id},
        }
