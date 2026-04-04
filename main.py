def get_gamepass_product_info(self, pass_id: int) -> dict | None:
    # 방법 1: 새 API로 details 조회
    resp = self.session.get(
        f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
    )
    print(f"[상품조회-방법1] status={resp.status_code} body={resp.text[:300]}")
    if resp.status_code == 200:
        data = resp.json()
        # 새 API 응답을 구 형식으로 변환
        return {
            "ProductId": data.get("productId"),
            "PriceInRobux": data.get("price", 0),
            "Creator": {"Id": data.get("creatorTargetId") or data.get("creatorId")},
        }

    # 방법 2: 구 economy API
    resp2 = self.session.get(
        f"https://economy.roblox.com/v1/game-pass/{pass_id}/product-info"
    )
    print(f"[상품조회-방법2] status={resp2.status_code} body={resp2.text[:300]}")
    if resp2.status_code == 200:
        return resp2.json()

    return None
