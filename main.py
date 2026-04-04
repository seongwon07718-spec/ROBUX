class RobloxAPI:
    # ... 기존 코드 ...

    # ── 게임패스 상품 정보 ────────────────────────────────────────────────────
    def get_gamepass_product_info(self, pass_id: int) -> dict | None:
        resp = self.session.get(
            f"https://economy.roblox.com/v1/game-pass/{pass_id}/product-info"
        )
        if resp.status_code == 200:
            return resp.json()
        
        resp2 = self.session.get(
            f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}?passView=Full"
        )
        if resp2.status_code == 200:
            data = resp2.json()
            return {
                "ProductId": data.get("productId") or data.get("id"),
                "PriceInRobux": data.get("price", 0),
                "Creator": {"Id": data.get("creatorId")},
            }
        return None

    # ── 게임패스 구매 ─────────────────────────────────────────────────────────
    def buy_gamepass(self, pass_id: int) -> dict:
        info = self.get_gamepass_product_info(pass_id)
        if not info:
            return {"purchased": False, "reason": "상품 정보 조회 실패"}

        product_id = info.get("ProductId")
        price = info.get("PriceInRobux", 0)
        seller_id = (info.get("Creator") or {}).get("Id")

        print(f"[구매시도] pass_id={pass_id} product_id={product_id} price={price} seller_id={seller_id}")

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
        payload = {
            "expectedCurrency": 1,
            "expectedPrice": price,
            "expectedSellerId": seller_id,
        }
        resp = self.session.post(
            f"https://economy.roblox.com/v1/purchases/products/{product_id}",
            json=payload,
            headers=headers,
        )
        print(f"[구매결과] status={resp.status_code} body={resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"purchased": False, "reason": f"HTTP {resp.status_code}"}
