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

        # ✅ price 필드 추가
        resp = self.session.post(
            f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/purchase",
            json={
                "expectedPrice": price,
                "price": price,          # ✅ 이거 추가
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
