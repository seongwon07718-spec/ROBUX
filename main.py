    async def info_callback(self, it: discord.Interaction):
        # 1. 컨테이너 생성 및 유저 아바타 설정
        container = ui.Container()
        container.accent_color = 0xffffff
        
        # 유저 아바타 URL 가져오기
        avatar_url = it.user.display_avatar.url

        # 2. robux_shop.db에서 데이터 조회
        u_id = str(it.user.id)
        conn = sqlite3.connect('robux_shop.db')
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone()
        conn.close()

        money = row[0] if row else 0
        total_spent = 0
        discount = "0%"
        
        # 유저의 가장 높은 역할 찾기
        user_roles = [role for role in it.user.roles if role.name != "@everyone"]
        role_grade = user_roles[-1].name if user_roles else "역할 없음"

        # 3. 레이아웃 구성
        # 제목과 프로필 이미지를 상단에 배치 (TextDisplay의 image_url 활용)
        container.add_item(ui.TextDisplay(
            f"## {it.user.display_name} 님의 정보",
            image_url=avatar_url # 우측 상단에 프로필 이미지가 노출되도록 설정
        ))
        
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 본문 정보 (도트 이모지 스타일)
        info_text = (
            f"<:dot_white:1482000567562928271> **보유 잔액:** {money:,}원\n"
            f"<:dot_white:1482000567562928271> **사용 금액:** {total_spent:,}원\n"
            f"<:dot_white:1482000567562928271> **역할 등급:** {role_grade}\n"
            f"<:dot_white:1482000567562928271> **할인 혜택:** {discount}"
        )
        container.add_item(ui.TextDisplay(info_text))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 4. 선택 메뉴 (Select)
        selecao = ui.Select(placeholder="조회할 내역 선택", options=[
            discord.SelectOption(label="최근 충전 내역", value="charge", emoji="<:dot_white:1482000567562928271>"),
            discord.SelectOption(label="최근 구매 내역", value="purchase", emoji="<:dot_white:1482000567562928271>")
        ])

        async def res_callback(i: discord.Interaction):
            selected_val = selecao.values[0]
            await i.response.send_message(f"{selected_val} 내역을 불러오는 중입니다...", ephemeral=True)

        selecao.callback = res_callback
        
        # 선택 메뉴를 컨테이너 안의 ActionRow로 추가
        container.add_item(ui.ActionRow(selecao))
        
        # 5. 전송 (LayoutView에 컨테이너 하나만 담기)
        view = ui.LayoutView().add_item(container)
        await it.response.send_message(view=view, ephemeral=True)

