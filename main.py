    async def info_callback(self, interaction: discord.Interaction):
        u_id = str(interaction.user.id)
        
        # DB에서 유저 정보 불러오기
        conn = sqlite3.connect('vending1.db')
        cur = conn.cursor()
        cur.execute("SELECT money, total_spent FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone()
        conn.close()

        money, total_spent = (row[0], row[1]) if row else (0, 0)

        # 1. 컨테이너 설정
        info_con = ui.Container(ui.TextDisplay(f"## {interaction.user.display_name}님의 정보"), accent_color=0x5865F2)
        info_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        info_con.add_item(ui.TextDisplay(f"**잔액:** ₩{money:,}\n**누적 금액:** ₩{total_spent:,}"))
        info_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 2. Select 메뉴 설정
        history_select = ui.Select(placeholder="거래 내역 조회하기")
        history_select.add_option(label="최근 구매 내역", description="최근 구매하신 상품 5개를 보여줍니다", emoji="🛒", value="buy_log")
        history_select.add_option(label="최근 충전 내역", description="최근 충전하신 기록 5개를 보여줍니다", emoji="💳", value="charge_log")

        # Select 콜백 함수
        async def select_callback(it: discord.Interaction):
            selected = history_select.values[0]
            if selected == "buy_log":
                await it.response.send_message("🛒 최근 구매 내역이 없습니다.", ephemeral=True)
            else:
                await it.response.send_message("💳 최근 충전 내역이 없습니다.", ephemeral=True)

        history_select.callback = select_callback

        # 3. 레이아웃 구성 및 전송
        info_view = ui.LayoutView()
        info_view.add_item(info_con)
        info_view.add_item(ui.ActionRow(history_select))

        await interaction.response.send_message(view=info_view, ephemeral=True)
