    async def info_callback(self, interaction: discord.Interaction):
        u_id = str(interaction.user.id)
        
        # DB에서 유저 정보 조회 (기존 database 모듈 사용)
        conn = sqlite3.connect('vending1.db')
        cur = conn.cursor()
        cur.execute("SELECT money, total_spent FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone()
        conn.close()

        money, total_spent = (row[0], row[1]) if row else (0, 0)

        # 1. 정보를 담을 컨테이너 생성
        info_con = ui.Container(ui.TextDisplay(f"## {interaction.user.display_name}님의 정보"), accent_color=0x5865F2)
        info_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        info_con.add_item(ui.TextDisplay(f"**잔액:** ₩{money:,}\n**누적 금액:** ₩{total_spent:,}"))
        info_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 2. 사진 속 방식과 동일한 ui.Select 생성
        selecao = ui.Select(placeholder="조회하실 내역을 선택하세요", options=[
            discord.SelectOption(label="최근 구매 내역", value="buy", description="최근 상품 구매 기록을 확인합니다.", emoji="🛒"),
            discord.SelectOption(label="최근 충전 내역", value="charge", description="최근 충전 신청 기록을 확인합니다.", emoji="💳")
        ])

        # Select 콜백 함수 연결 (사진의 self.resposta_selecao 방식)
        async def resposta_selecao(it: discord.Interaction):
            escolha = selecao.values[0] # 선택한 값 가져오기
            
            if escolha == "buy":
                await it.response.send_message(f"🛒 **{it.user.name}**님의 최근 구매 내역이 없습니다.", ephemeral=True)
            else:
                # database.get_history 함수 등을 활용해 내역 출력 가능
                await it.response.send_message(f"💳 **{it.user.name}**님의 최근 충전 내역이 없습니다.", ephemeral=True)

        selecao.callback = resposta_selecao

        # 3. 레이아웃에 컨테이너와 셀렉트 메뉴 추가
        info_view = ui.LayoutView()
        info_view.add_item(info_con)
        
        # 사진처럼 ui.ActionRow를 사용하여 Select 메뉴 추가
        linha = ui.ActionRow(selecao)
        info_view.add_item(linha)

        await interaction.response.send_message(view=info_view, ephemeral=True)
