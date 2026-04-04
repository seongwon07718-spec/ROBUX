def fetch_gamepass_details(pass_id, admin_cookie=None):
    # 헤더를 실제 브라우저처럼 세팅해야 404를 피할 수 있습니다.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Origin": "https://www.roblox.com",
        "Referer": "https://www.roblox.com/"
    }
    cookies = {".ROBLOSECURITY": admin_cookie} if admin_cookie else {}

    try:
        # 주소 끝에 /details가 정확히 붙어야 합니다.
        url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = requests.get(url, headers=headers, cookies=cookies, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            
            # [핵심] 로블록스 API 필드명은 대소문자가 섞여있습니다.
            # 가격(PriceInRobux), 이름(Name), 판매자(Creator -> Id), 상품ID(ProductId)
            price = data.get("PriceInRobux")
            if price is None:
                price = data.get("price", 0) # 소문자 백업
                
            return {
                "id": pass_id,
                "name": data.get("Name") or data.get("name", "이름 없음"),
                "price": int(price), # 여기서 숫자로 확실히 변환
                "sellerId": data.get("Creator", {}).get("Id") or data.get("creatorId"),
                "productId": data.get("ProductId") or data.get("productId"),
                "isForSale": data.get("IsForSale", True)
            }
        else:
            # 404 등이 뜨면 터미널에 찍어서 확인
            print(f"로블록스 응답 에러 ({res.status_code}): {res.text}")
            
    except Exception as e:
        print(f"조회 중 예외 발생: {e}")
    
    return None
