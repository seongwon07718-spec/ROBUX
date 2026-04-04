def fetch_gamepass_details(pass_id, admin_cookie=None):
    # 세션을 사용하여 쿠키와 헤더를 관리합니다.
    session = requests.Session()
    
    if admin_cookie:
        # DB에서 가져온 쿠키를 세션에 설정
        session.cookies.set(".ROBLOSECURITY", admin_cookie, domain=".roblox.com")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/"
    }
    
    try:
        # 로그인된 세션으로 상세 정보 요청
        url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = session.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            
            # 가격 및 필수 정보 추출
            price = data.get("PriceInRobux")
            if price is None:
                price = data.get("price", 0)
                
            return {
                "id": pass_id,
                "name": data.get("Name") or data.get("name", "이름 없음"),
                "price": int(price),
                "sellerId": data.get("Creator", {}).get("Id") or data.get("creatorId"),
                "productId": data.get("ProductId") or data.get("productId"),
                "isForSale": data.get("IsForSale", True)
            }
        else:
            # 쿠키가 만료되었거나 ID가 틀렸을 경우 로그 출력
            print(f"API 조회 실패 (상태 코드: {res.status_code})")
            print(f"응답 내용: {res.text}")
            
    except Exception as e:
        print(f"조회 중 예외 발생: {e}")
    
    return None
