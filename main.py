    def get_gamepass_product_info(self, pass_id: int) -> dict | None:
        # ✅ v2/assets API로 정확한 ProductId 조회
        resp = self.session.get(
            f"https://economy.roblox.com/v2/assets/{pass_id}/details"
        )
        print(f"[v2/assets] status={resp.status_code} body={resp.text[:400]}")
        if resp.status_code == 200:
            data = resp.json()
            return {
                "ProductId": data.get("ProductId"),
                "PriceInRobux": data.get("PriceInRobux") or 0,
                "Creator": {
                    "Id": (data.get("Creator") or {}).get("CreatorTargetId")
                    or (data.get("Creator") or {}).get("Id")
                },
            }
        return None

    def buy_gamepass(self, pass_id: int) -> dict:
        info = self.get_gamepass_product_info(pass_id)
        if not info:
            return {"purchased": False, "reason": "상품 정보 조회 실패"}

        product_id = info.get("ProductId")
        price = int(info.get("PriceInRobux") or 0)
        seller_id = (info.get("Creator") or {}).get("Id")

        print(f"[구매시도] product_id={product_id} price={price} seller_id={seller_id}")

        if not product_id:
            return {"purchased": False, "reason": "ProductId 없음"}

        token = self.get_csrf_token()
        if not token:
            return {"purchased": False, "reason": "CSRF 토큰 획득 실패"}

        headers = {
            "x-csrf-token": token,
            "Content-Type": "application/json",
            "Referer": f"https://www.roblox.com/game-pass/{pass_id}",
            "Origin": "https://www.roblox.com",
        }
        resp = self.session.post(
            f"https://economy.roblox.com/v1/purchases/products/{product_id}",
            json={
                "expectedCurrency": 1,
                "expectedPrice": price,
                "expectedSellerId": seller_id,
                "saleLocationType": "Website",
            },
            headers=headers,
        )
        print(f"[구매결과] status={resp.status_code} body={resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"purchased": False, "reason": f"HTTP {resp.status_code}"}
