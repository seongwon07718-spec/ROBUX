def purchase_gamepass(product_id, expected_price, seller_id):
    """
    최신 로블록스 구매 API 사양에 맞춰 수정한 구매 함수입니다.
    InvalidArguments 에러 방지를 위해 페이로드 구조를 최정밀화했습니다.
    """
    # 1. DB에서 관리자 쿠키 로드
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        return {"success": False, "message": "관리자 쿠키가 설정되지 않았습니다."}

    admin_cookie = row[0]
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", admin_cookie, domain=".roblox.com")

    # 브라우저 환경과 동일하게 헤더 구성 (Content-Type 필수)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com"
    }

    try:
        # 2. CSRF 토큰 갱신
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        csrf_token = auth_res.headers.get("x-csrf-token")
        
        if not csrf_token:
            return {"success": False, "message": "CSRF 토큰 획득 실패 (쿠키 만료 가능성)"}
        
        headers["X-CSRF-TOKEN"] = csrf_token

        # 3. 구매 요청 주소 및 데이터 (v1 purchase endpoint)
        purchase_url = f"https://economy.roblox.com/v1/purchases/products/{product_id}"
        
        # [중요] InvalidArguments 방지를 위해 데이터 타입을 정확히 맞춥니다.
        payload = {
            "expectedCurrency": 1,         # 1: Robux
            "expectedPrice": int(expected_price),
            "expectedSellerId": int(seller_id) if seller_id else 1
        }

        # 데이터 전송 (json.dumps로 확실하게 직렬화)
        res = session.post(purchase_url, headers=headers, data=json.dumps(payload), timeout=10)

        if res.status_code == 200:
            data = res.json()
            
            # purchased 필드가 존재하고 True인지 확인
            if data.get("purchased") is True:
                return {"success": True, "message": "구매 성공!", "data": data}
            else:
                # 에러 이유 상세 분석
                reason = data.get("reason") or data.get("errorMsg") or "알 수 없는 오류"
                return {"success": False, "message": f"구매 실패: {reason}"}
        else:
            # 400 에러 발생 시 응답 내용 확인용
            error_data = res.json() if res.text else {}
            error_msg = error_data.get("errors", [{}])[0].get("message", res.text)
            return {"success": False, "message": f"서버 오류 ({res.status_code}): {error_msg}"}

    except Exception as e:
        return {"success": False, "message": f"시스템 오류: {str(e)}"}

# --- [수정] 구매 확인 및 버튼 콜백 완성 ---
class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id, cookie):
        super().__init__(timeout=120)
        self.info, self.money, self.user_id, self.cookie = info, money, str(user_id), cookie

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        price_info = (
            f"-# - **게임패스 이름**: {self.info['name']}\n"
            f"-# - **게임패스 가격**: {self.info['price']:,}로벅스\n"
            f"-# - **결제금액**: {self.money:,}원"
        )
        con.add_item(ui.TextDisplay(f"### <:acy2:1489883409001091142>  구매 단계\n{price_info}"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        row = ui.ActionRow()
        btn_confirm = ui.Button(label="진행", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>")
        btn_confirm.callback = self.self_confirm
        btn_cancel = ui.Button(label="취소", style=discord.ButtonStyle.gray, emoji="<:downvote:1489930277450158080>")
        btn_cancel.callback = self.self_cancel
        
        row.add_item(btn_confirm)
        row.add_item(btn_cancel)
        con.add_item(row)
        self.clear_items()
        self.add_item(con)
        return self

    async def self_confirm(self, it: discord.Interaction):
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        row = cur.fetchone()
        
        if not row or row[0] < self.money:
            conn.close()
            return await it.response.edit_message(view=get_container_view("❌ 잔액 부족", "충전 후 다시 시도해 주세요.", 0xED4245))

        await it.response.edit_message(view=get_container_view("⌛ 처리 중", "로블록스 서버와 통신 중입니다...", 0xFEE75C))

        result = purchase_gamepass(self.info['productId'], self.info['price'])
        
        if result["success"]:
            order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=get_container_view("✅ 구매 성공", f"주문번호: `{order_id}`\n지급이 완료되었습니다.", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 구매 실패", f"사유: `{result['message']}`", 0xED4245))
        conn.close()

    async def self_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소됨", "구매 요청을 거부했습니다.", 0x99AAB5))

class GamepassModal(ui.Modal, title="게임패스 방식"):
    id_input = ui.TextInput(label="게임패스 ID 또는 링크", placeholder="아이디나 링크를 입력하세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        # 1. 타임아웃 방지 (생각 중... 상태 돌입)
        await it.response.defer(ephemeral=True)
        
        raw_val = self.id_input.value.strip()
        pass_id = extract_pass_id(raw_val)
        
        if not pass_id:
            return await it.followup.send(content="❌ 올바른 ID나 링크를 입력해주세요.", ephemeral=True)

        # 2. 정보 가져오기 (일반 함수이므로 await 없음)
        info = fetch_gamepass_details(pass_id)
        
        if not info or info.get('price') is None:
            return await it.followup.send(content=f"❌ ID `{pass_id}` 정보를 불러올 수 없습니다.", ephemeral=True)

        # 3. 비율 로드 및 가격 계산
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        rate = int(r_row[0]) if r_row else 1000
        # 가격이 0원이면 에러 방지
        money = int((info['price'] / rate) * 10000) if info['price'] > 0 else 0

        # 3. 확인창 띄우기
        view_obj = GamepassConfirmView(info, money, it.user.id, "DB_COOKIE_USED")
        await it.followup.send(view=await view_obj.build(), ephemeral=True)
