    async def on_submit(self, it: discord.Interaction):
        raw_val = self.id_input.value.strip()
        
        # 1. 알렉스님이 사진으로 보여준 그 함수 그대로 사용
        pass_id = extract_pass_id(raw_val)
        
        if not pass_id:
            return await it.response.send_message(view=get_container_view("❌ 인식 오류", "올바른 ID나 링크를 입력해주세요.", 0xED4245), ephemeral=True)

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        admin_cookie = c_row[0] if c_row else None
        
        # 2. 정보 로드 (여기서 가격이 제대로 담겨야 합니다)
        info = fetch_gamepass_details(pass_id, admin_cookie)
        
        # [중요 수정] 가격이 0이거나 정보를 못 가져올 때의 예외 처리 강화
        if not info or info.get('price') is None:
            return await it.response.send_message(
                view=get_container_view("❌ 정보 없음", f"ID `{pass_id}`의 가격 정보를 불러올 수 없습니다.\n판매 중인지 확인해주세요.", 0xED4245), 
                ephemeral=True
            )

        # 3. 가격 계산 (데이터 타입 오류 방지를 위해 int 변환 필수)
        try:
            rate = int(r_row[0]) if r_row else 1000
            game_price = int(info['price']) # 가격을 확실하게 숫자로 고정
            
            # 계산식 (알렉스님 방식 유지)
            money = int((game_price / rate) * 10000)
            
            # 만약 계산된 금액이 0원이라면 최소 금액 설정(선택사항)
            if money <= 0: money = 100 
            
        except Exception as e:
            print(f"계산 에러: {e}")
            return await it.response.send_message(view=get_container_view("❌ 계산 오류", "가격 계산 중 문제가 발생했습니다.", 0xED4245), ephemeral=True)

        # 4. 결과 전송
        view_obj = GamepassConfirmView(info, money, it.user.id, admin_cookie)
        await it.response.send_message(view=await view_obj.build(), ephemeral=True)
