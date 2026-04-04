def fetch_gamepass_details(pass_id, admin_cookie=None):
    if not admin_cookie:
        print("에러: 관리자 쿠키가 설정되지 않았습니다.")
        return None

    # 세션 생성 및 쿠키 주입
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", admin_cookie, domain=".roblox.com")
    
    # 로블록스 보안 헤더 (이게 없으면 로그인 상태로 인정을 안 해줍니다)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com"
    }

    try:
        # 1. CSRF 토큰 확보 (로그인 상태를 증명하는 핵심 단계)
        # 로그아웃 엔드포인트에 빈 포스트를 날려 토큰만 받아옵니다.
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        csrf_token = auth_res.headers.get("x-csrf-token")
        
        if csrf_token:
            headers["X-CSRF-TOKEN"] = csrf_token

        # 2. 로그인된 상태(쿠키+토큰)로 실제 가격 정보 조회
        url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = session.get(url, headers=headers, timeout=7)
        
        if res.status_code == 200:
            data = res.json()
            
            # 알렉스님이 요청하신 가격(Price) 추출에 집중
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
            # 여전히 404가 뜬다면 ID 자체가 게임패스 ID가 아닐 확률이 큼
            print(f"조회 실패 코드: {res.status_code} | 응답: {res.text}")
            
    except Exception as e:
        print(f"로그인 조회 중 예외 발생: {e}")
    
    return None
