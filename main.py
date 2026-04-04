    def get_gamepass_product_info(self, pass_id: int) -> dict | None:
        # ✅ 새 API로 price 조회
        resp = self.session.get(
            f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        features = data.get("enabledFeatures", [])
        
        # ✅ RegionalPricing 있으면 거부
        if "RegionalPricing" in features:
            return {"purchased": False, "reason": "RegionalPricing 게임패스는 구매 불가"}

        price_info = data.get("priceInformation") or {}
        price = int(
            price_info.get("price")
            or price_info.get("defaultPriceInRobux")
            or 0
        )

        return {
            "ProductId": pass_id,
            "PriceInRobux": price,
            "Creator": {"Id": None},
        }

    def buy_gamepass(self, pass_id: int) -> dict:
        info = self.get_gamepass_product_info(pass_id)
        if not info:
            return {"purchased": False, "reason": "상품 정보 조회 실패"}
        
        # RegionalPricing 체크
        if info.get("reason"):
            return {"purchased": False, "reason": info["reason"]}

        price = int(info.get("PriceInRobux") or 0)

        token = self.get_csrf_token()
        if not token:
            return {"purchased": False, "reason": "CSRF 토큰 획득 실패"}

        headers = {
            "x-csrf-token": token,
            "Content-Type": "application/json",
            "Referer": "https://www.roblox.com/",
            "Origin": "https://www.roblox.com",
        }

        resp = self.session.post(
            f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/purchase",
            json={"expectedPrice": price},
            headers=headers,
        )
        print(f"[구매결과] status={resp.status_code} body={resp.text}")

        try:
            result = resp.json()
            # ✅ purchased 체크 - 새 API는 purchased 필드 다를 수 있음
            if result.get("purchased") or result.get("reason") == "Success":
                result["purchased"] = True
            return result
        except Exception:
            return {"purchased": False, "reason": f"HTTP {resp.status_code}"}
