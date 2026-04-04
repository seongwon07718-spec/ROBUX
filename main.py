    def get_gamepass_product_info(self, pass_id: int) -> dict | None:
        resp = self.session.get(
            f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        price_info = data.get("priceInformation") or {}

        # ✅ RegionalPricing 있으면 regionalPrice 우선
        price = int(
            price_info.get("regionalPrice")
            or price_info.get("price")
            or price_info.get("defaultPriceInRobux")
            or 0
        )

        # price가 0이면 economy API로 폴백
        if price == 0:
            resp2 = self.session.get(
                f"https://economy.roblox.com/v1/game-pass/{pass_id}/product-info"
            )
            if resp2.status_code == 200:
                data2 = resp2.json()
                price = int(data2.get("PriceInRobux") or 0)
                return {
                    "ProductId": data2.get("ProductId") or pass_id,
                    "PriceInRobux": price,
                    "Creator": {"Id": (data2.get("Creator") or {}).get("Id")},
                }

        place_id = data.get("placeId")
        creator_id = None
        if place_id:
            u_resp = self.session.get(
                f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
            )
            if u_resp.status_code == 200:
                universe_id = u_resp.json().get("universeId")
                if universe_id:
                    g_resp = self.session.get(
                        f"https://games.roblox.com/v1/games?universeIds={universe_id}"
                    )
                    if g_resp.status_code == 200:
                        games = g_resp.json().get("data", [])
                        if games:
                            creator_id = games[0].get("creator", {}).get("id")

        print(f"[상품정보] price={price} creator_id={creator_id}")
        return {
            "ProductId": data.get("gamePassId") or pass_id,
            "PriceInRobux": price,
            "Creator": {"Id": creator_id},
        }
