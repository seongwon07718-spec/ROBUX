    async def info_callback(self, interaction: discord.Interaction):
        u_id = str(interaction.user.id)
        
        # DB 정보 가져오기 (기존 유지)
        conn = sqlite3.connect('vending1.db')
        cur = conn.cursor()
        cur.execute("SELECT money, total_spent FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone()
        conn.close()

        money, total_spent = (row[0], row[1]) if row else (0, 0)

        # 1. 이미지의 'container' 역할 (ui.Container 생성)
        container = ui.Container(ui.TextDisplay(f"## {interaction.user.display_name}님의 정보"), accent_color=0x5865F2)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"**잔액:** ₩{money:,}\n**누적 금액:** ₩{total_spent:,}"))

        # 2. 이미지의 'selecao' 역할 (ui.Select 생성)
        selecao = ui.Select(placeholder="조회하실 내역을 선택하세요", options=[
            discord.SelectOption(label="최근 구매 내역", value="buy", description="구매 기록 확인", emoji="🛒"),
            discord.SelectOption(label="최근 충전 내역", value="charge", description="충전 기록 확인", emoji="💳")
        ])

        # 3. 이미지의 'resposta_selecao' 역할 (콜백 함수 정의)
        async def resposta_selecao(it: discord.Interaction):
            # 이미지 방식대로 it.data['values'][0] 또는 selecao.values[0] 사용
            escolha = selecao.values[0]
            if escolha == "buy":
                await it.response.send_message(f"🛒 **{it.user.name}**님, 구매 내역이 없습니다.", ephemeral=True)
            else:
                await it.response.send_message(f"💳 **{it.user.name}**님, 충전 내역이 없습니다.", ephemeral=True)

        selecao.callback = resposta_selecao

        # 4. 이미지의 'linha' 역할 (ActionRow 생성 및 아이템 추가)
        # 중요: ActionRow에는 버튼이나 셀렉트만 넣어야 합니다.
        linha = ui.ActionRow()
        linha.add_item(selecao)

        # 5. 계층 구조 결합 (이미지 로직 핵심)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(linha) # 컨테이너 안에 줄(Select 포함) 추가

        # 6. 최종 뷰 생성 및 전송
        info_view = ui.LayoutView()
        info_view.add_item(container) # 뷰에 최종 컨테이너 추가

        await interaction.response.send_message(view=info_view, ephemeral=True)
