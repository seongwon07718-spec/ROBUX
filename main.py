def fetch_gamepass_price(pass_id, admin_cookie=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    cookies = {".ROBLOSECURITY": admin_cookie} if admin_cookie else {}
    
    try:
        # 1순위: 가장 정확한 Economy API
        url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = requests.get(url, headers=headers, cookies=cookies, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            # 로블록스 API의 다양한 가격 필드명을 모두 체크
            price = data.get("PriceInRobux") # 보통 대문자로 옴
            if price is None:
                price = data.get("price") # 소문자 케이스 체크
            
            if price is not None:
                return int(price) # 숫자로 변환해서 반환
                
        # 2순위: 1단계 실패 시 Apis 엔드포인트로 재시도
        fallback_url = f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
        res2 = requests.get(fallback_url, headers=headers, cookies=cookies, timeout=5)
        if res2.status_code == 200:
            data2 = res2.json()
            price = data2.get("price") or data2.get("PriceInRobux")
            if price is not None:
                return int(price)

    except Exception as e:
        print(f"가격 추출 중 오류: {e}")
    
    return 0 # 찾지 못하면 0 반환
