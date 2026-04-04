def buy_gamepass(self, pass_id: int) -> dict:
    info = self.get_gamepass_product_info(pass_id)
    if not info:
        return {"purchased": False, "reason": "상품 정보 조회 실패"}

    price = info.get("PriceInRobux", 0)
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

    # ✅ 게임패스 전용 구매 API
    payload = {
        "expectedCurrency": 1,
        "expectedPrice": price,
        "expectedSellerId": seller_id,
    }
    resp = self.session.post(
        f"https://economy.roblox.com/v1/purchases/game-pass/{pass_id}",
        json=payload,
        headers=headers,
    )
    print(f"[구매결과1] status={resp.status_code} body={resp.text}")

    if resp.status_code == 200:
        try:
            return resp.json()
        except Exception:
            pass

    # 폴백: 새 game-passes API
    resp2 = self.session.post(
        f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/purchase",
        json={"expectedPrice": price, "expectedCurrency": 1},
        headers=headers,
    )
    print(f"[구매결과2] status={resp2.status_code} body={resp2.text}")

    try:
        return resp2.json()
    except Exception:
        return {"purchased": False, "reason": f"HTTP {resp2.status_code}"}
