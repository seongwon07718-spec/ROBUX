    def get_gamepass_product_info(self, pass_id: int) -> dict | None:
        # 새 game-passes API로 price/creator 조회
        resp = self.session.get(
            f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        price_info = data.get("priceInformation") or {}
        price = int(
            price_info.get("price")
            or price_info.get("defaultPriceInRobux")
            or 0
        )

        # creator_id는 v2/assets에서 가져오기
        resp2 = self.session.get(
            f"https://economy.roblox.com/v2/assets/{pass_id}/details"
        )
        creator_id = None
        if resp2.status_code == 200:
            d2 = resp2.json()
            creator_id = (d2.get("Creator") or {}).get("CreatorTargetId")
            # ✅ ProductId 대신 pass_id 직접 사용
            # economy API의 ProductId는 게임패스엔 없음

        print(f"[상품정보] price={price} creator_id={creator_id}")
        return {
            "ProductId": pass_id,  # ✅ pass_id 그대로 사용
            "PriceInRobux": price,
            "Creator": {"Id": creator_id},
        }

    def buy_gamepass(self, pass_id: int) -> dict:
        info = self.get_gamepass_product_info(pass_id)
        if not info:
            return {"purchased": False, "reason": "상품 정보 조회 실패"}

        price = int(info.get("PriceInRobux") or 0)
        seller_id = (info.get("Creator") or {}).get("Id")

        token = self.get_csrf_token()
        if not token:
            return {"purchased": False, "reason": "CSRF 토큰 획득 실패"}

        headers = {
            "x-csrf-token": token,
            "Content-Type": "application/json",
            "Referer": f"https://www.roblox.com/game-pass/{pass_id}",
            "Origin": "https://www.roblox.com",
        }

        # ✅ 게임패스 전용 구매 API 사용
        resp = self.session.post(
            f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/purchase",
            json={
                "expectedPrice": price,
                "expectedCurrency": 1,
                "expectedSellerId": seller_id,
            },
            headers=headers,
        )
        print(f"[구매결과] status={resp.status_code} body={resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"purchased": False, "reason": f"HTTP {resp.status_code}"}
