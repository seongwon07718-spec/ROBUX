def fetch_gamepass_details(pass_id):
    # 1. DB에서 /쿠키등록으로 저장된 쿠키 불러오기
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        print("❌ DB에 등록된 쿠키가 없습니다.")
        return None
    
    admin_cookie = row[0]
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", admin_cookie, domain=".roblox.com")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com"
    }

    try:
        # [우회] CSRF 토큰 갱신
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers, timeout=5)
        csrf_token = auth_res.headers.get("x-csrf-token")
        if csrf_token:
            headers["X-CSRF-TOKEN"] = csrf_token

        # 정보 조회
        url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = session.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            
            # --- [핵심] 가격 파싱 3중 체크 ---
            # 1순위: PriceInRobux, 2순위: price, 3순위: 0
            raw_price = data.get("PriceInRobux")
            if raw_price is None:
                raw_price = data.get("price")
            
            # 최종 가격을 정수형(int)으로 변환 (None 방지)
            final_price = int(raw_price) if raw_price is not None else 0
            
            print(f"DEBUG: 파싱된 가격 -> {final_price} (원본: {raw_price})")
            
            return {
                "id": pass_id,
                "name": data.get("Name") or data.get("name", "상품명 없음"),
                "price": final_price, # 무조건 숫자로 들어감
                "sellerId": data.get("Creator", {}).get("Id") or data.get("creatorId"),
                "productId": data.get("ProductId") or data.get("productId")
            }
        else:
            print(f"❌ 조회 실패: {res.status_code}")

    except Exception as e:
        print(f"🚨 파싱 에러: {e}")
    
    return None
