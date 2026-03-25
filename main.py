    async def info_callback(self, it: discord.Interaction):
        # 1. 컨테이너 생성 및 해외 V2 스타일 헤더 설정
        # 해외에서는 컨테이너 자체의 title과 title_icon_url을 사용하여 
        # 우측 상단(또는 좌측 상단)에 프로필을 고정합니다.
        container = ui.Container(
            title=f"{it.user.display_name} 님의 정보",
            title_icon_url=it.user.display_avatar.url, # 이 부분이 해외에서 프로필을 넣는 방식입니다.
            accent_color=0xffffff
        )

        # 2. 데이터 조회 (robux_shop.db 호환)
        u_id = str(it.user.id)
        money = 0
        try:
            conn = sqlite3.connect('robux_shop.db')
            cur = conn.cursor()
            cur.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
            row = cur.fetchone()
            conn.close()
            if row: money = row[0]
        except Exception as e:
            print(f"DB Error: {e}")

        # 가장 높은 역할 등급 확인
        user_roles = [role for role in it.user.roles if role.name != "@everyone"]
        role_grade = user_roles[-1].name if user_roles else "Guest"

        # 3. 본문 레이아웃 (Card 스타일)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        info_content = (
            f"> <:dot_white:1482000567562928271> **보유 잔액:** `{money:,}` 원\n"
            f"> <:dot_white:1482000567562928271> **사용 금액:** `0` 원\n"
            f"> <:dot_white:1482000567562928271> **역할 등급:** `{role_grade}`\n"
            f"> <:dot_white:1482000567562928271> **할인 혜택:** `0%`"
        )
        container.add_item(ui.TextDisplay(info_content))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 4. 내역 선택 메뉴 (Select)
        # 해외 V2 방식에서는 모든 인터랙티브 아이템을 ActionRow에 감싸서 컨테이너에 넣어야 에러가 없습니다.
        selecao = ui.Select(
            placeholder="조회하실 내역을 선택해 주세요",
            options=[
                discord.SelectOption(label="최근 충전 내역", value="charge", emoji="💳"),
                discord.SelectOption(label="최근 구매 내역", value="purchase", emoji="🛒")
            ]
        )

        async def res_callback(i: discord.Interaction):
            await i.response.send_message(f"**{selecao.values[0]}** 내역 조회 기능을 준비 중입니다.", ephemeral=True)
        
        selecao.callback = res_callback
        container.add_item(ui.ActionRow(selecao))

        # 5. 최종 전송 (LayoutView에 컨테이너 하나만 전송)
        # 사진 속의 Invalid Form Body 에러를 완벽하게 방지하는 구조입니다.
        view = ui.LayoutView().add_item(container)
        await it.response.send_message(view=view, ephemeral=True)

