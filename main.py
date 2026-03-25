    async def info_callback(self, it: discord.Interaction):
        # 1. 컨테이너 생성 및 기본 설정
        container = ui.Container()
        container.accent_color = 0xffffff
        
        # 제목 설정
        container.add_item(ui.TextDisplay(f"## {it.user.display_name} 님의 정보"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 2. robux_shop.db에서 보유 잔액 가져오기
        u_id = str(it.user.id)
        # DB 파일명을 robux_shop.db로 수정하여 호환성 확보
        conn = sqlite3.connect('robux_shop.db')
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone()
        conn.close()

        money = row[0] if row else 0
        total_spent = 0 # 사용 금액 0원 고정
        discount = "0%" # 할인 0% 고정
        
        # 유저가 보유한 가장 높은 역할 등급 가져오기
        # @everyone(기본역할)을 제외하고 가장 상위에 있는 역할의 이름을 가져옵니다.
        user_roles = [role for role in it.user.roles if role.name != "@everyone"]
        role_grade = user_roles[-1].name if user_roles else "역할 없음"

        # 3. 정보 본문 구성 (도트 이모지 스타일)
        info_text = (
            f"<:dot_white:1482000567562928271> **보유 잔액:** {money:,}원\n"
            f"<:dot_white:1482000567562928271> **사용 금액:** {total_spent:,}원\n"
            f"<:dot_white:1482000567562928271> **역할 등급:** {role_grade}\n"
            f"<:dot_white:1482000567562928271> **할인 혜택:** {discount}"
        )
        container.add_item(ui.TextDisplay(info_text))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 4. 선택 메뉴(Select) 구성
        selecao = ui.Select(placeholder="조회할 내역 선택", options=[
            discord.SelectOption(label="최근 충전 내역", value="charge", emoji="<:dot_white:1482000567562928271>"),
            discord.SelectOption(label="최근 구매 내역", value="purchase", emoji="<:dot_white:1482000567562928271>")
        ])

        async def res_callback(i: discord.Interaction):
            selected_val = selecao.values[0]
            # 선택된 값에 따른 추가 로직은 여기에 작성
            await i.response.send_message(f"현재 {selected_val} 내역이 존재하지 않습니다.", ephemeral=True)

        selecao.callback = res_callback
        
        # 중요: 선택 메뉴를 컨테이너 내부 ActionRow에 추가 (에러 해결 핵심)
        container.add_item(ui.ActionRow(selecao))
        
        # 5. 최종 전송 (LayoutView에 컨테이너 하나만 담음)
        view = ui.LayoutView().add_item(container)
        await it.response.send_message(view=view, ephemeral=True)

