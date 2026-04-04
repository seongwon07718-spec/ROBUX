def get_gamepass_product_info(self, pass_id: int) -> dict | None:
    # 새 API details 조회
    resp = self.session.get(
        f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
    )
    print(f"[상품조회] status={resp.status_code} body={resp.text[:400]}")
    
    if resp.status_code == 200:
        data = resp.json()
        price_info = data.get("priceInformation") or {}
        price = (
            price_info.get("price")
            or price_info.get("defaultPriceInRobux")
            or data.get("price")
            or 0
        )
        creator_id = (
            data.get("creatorTargetId")
            or data.get("creatorId")
            or data.get("ownerId")
        )
        # productId 없으면 gamePassId 자체를 product로 사용
        product_id = (
            data.get("productId")
            or data.get("gamePassId")
            or pass_id
        )
        print(f"[파싱결과] product_id={product_id} price={price} creator_id={creator_id}")
        return {
            "ProductId": product_id,
            "PriceInRobux": price,
            "Creator": {"Id": creator_id},
        }

    # 구 economy API 폴백
    resp2 = self.session.get(
        f"https://economy.roblox.com/v1/game-pass/{pass_id}/product-info"
    )
    print(f"[상품조회-폴백] status={resp2.status_code} body={resp2.text[:300]}")
    if resp2.status_code == 200:
        return resp2.json()

    return None
