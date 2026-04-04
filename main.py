    def get_gamepass_product_info(self, pass_id: int) -> dict | None:
        resp = self.session.get(
            f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
        )
        if resp.status_code == 200:
            data = resp.json()
            price_info = data.get("priceInformation") or {}
            price = (
                price_info.get("price")
                or price_info.get("defaultPriceInRobux")
                or 0
            )
            creator_id = (
                data.get("creatorTargetId")
                or data.get("creatorId")
                or data.get("creator", {}).get("id")
                or data.get("placeId")
            )
            print(f"[전체응답] {data}")
            print(f"[파싱] price={price} creator_id={creator_id}")
            return {
                "ProductId": data.get("gamePassId") or pass_id,
                "PriceInRobux": price,
                "Creator": {"Id": creator_id},
            }
        return None
