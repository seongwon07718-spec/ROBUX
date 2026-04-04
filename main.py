def fetch_gamepass_details(pass_id):
    # 1. DB에서 /쿠키등록으로 저장된 쿠키 불러오기
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        print("❌ DB에 등록된 쿠키가 없습니다. /쿠키등록을 먼저 해주세요.")
        return None
    
    admin_cookie = row[0]

    # 2. 세션 및 쿠키 설정
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", admin_cookie, domain=".roblox.com")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com"
    }

    try:
        # 3. [우회 핵심] CSRF 토큰 갱신 (로그인 증명)
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers, timeout=5)
        csrf_token = auth_res.headers.get("x-csrf-token")
        if csrf_token:
            headers["X-CSRF-TOKEN"] = csrf_token

        # 4. 실제 정보 조회 (Economy API -> 404 발생 시 Apis로 우회)
        url = f"https://economy.roblox.com/v1/game-passes/{pass_id}/details"
        res = session.get(url, headers=headers, timeout=5)
        
        if res.status_code != 200:
            # 해외 우회용 세컨드 API 주소
            url = f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details"
            res = session.get(url, headers=headers, timeout=5)

        if res.status_code == 200:
            data = res.json()
            # [알렉스님 요청] 가격 추출 및 정수 변환
            price = data.get("PriceInRobux") or data.get("price") or 0
            
            return {
                "id": pass_id,
                "name": data.get("Name") or data.get("name", "상품명 없음"),
                "price": int(price),
                "sellerId": data.get("Creator", {}).get("Id") or data.get("creatorId"),
                "productId": data.get("ProductId") or data.get("productId")
            }
        else:
            print(f"❌ 최종 조회 실패: {res.status_code} | {res.text}")

    except Exception as e:
        print(f"🚨 시스템 에러: {e}")
    
    return None


class GamepassModal(ui.Modal, title="게임패스 구매"):
    id_input = ui.TextInput(label="게임패스 ID 또는 링크", placeholder="여기에 붙여넣으세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        raw_val = self.id_input.value.strip()
        pass_id = extract_pass_id(raw_val) # 알렉스님의 정밀 추출 함수
        
        if not pass_id:
            return await it.response.send_message(view=get_container_view("❌ 인식 오류", "ID를 찾을 수 없습니다.", 0xED4245), ephemeral=True)

        # 1. 함수 호출 (내부에서 DB 쿠키 사용)
        info = fetch_gamepass_details(pass_id)
        
        if not info:
            return await it.response.send_message(view=get_container_view("❌ 정보 없음", "쿠키가 만료되었거나 잘못된 ID입니다.", 0xED4245), ephemeral=True)

        # 2. 비율 계산을 위한 DB 조회 (비율은 여기서 따로 가져옴)
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000)

        # 3. 확인창 띄우기
        view_obj = GamepassConfirmView(info, money, it.user.id, "DB_COOKIE_USED")
        await it.response.send_message(view=await view_obj.build(), ephemeral=True)
