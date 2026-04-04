    async def on_submit(self, it: discord.Interaction):
        raw_val = self.id_input.value.strip()
        pass_id = extract_pass_id(raw_val) # 알렉스님의 추출 함수
        
        # DB에서 쿠키와 비율 로드
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        admin_cookie = c_row[0] if c_row else None
        
        # [핵심] 불러온 쿠키를 넣어서 로그인 상태로 조회 시도
        info = fetch_gamepass_details(pass_id, admin_cookie)
        
        if not info:
            return await it.response.send_message(
                view=get_container_view("❌ 정보 없음", "로그인 세션이 만료되었거나 올바르지 않은 ID입니다.", 0xED4245), 
                ephemeral=True
            )

        # 가격 계산 및 출력 로직... (이후 동일)
