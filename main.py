class MeuLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None) 
        self.container = ui.Container(ui.TextDisplay("## 구매하기"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("아래 버튼을 눌려 이용해주세요"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 버튼 생성
        buy = ui.Button(label="구매", emoji="<:buy:1481994292255002705>")
        shop = ui.Button(label="제품", emoji="<:shop:1481994009499930766>")
        chage = ui.Button(label="충전", emoji="<:change:1481994723802611732>")
        info = ui.Button(label="정보", emoji="<:info:1481993647774892043>")
        
        # 콜백 연결 (함수가 클래스 내부에 정의되어 있어야 함)
        buy.callback = self.buy_callback
        shop.callback = self.shop_callback
        chage.callback = self.chage_callback
        info.callback = self.info_callback
        
        # 버튼들을 ActionRow에 담아 컨테이너에 추가
        act = ui.ActionRow(buy, shop, chage, info)
        self.container.add_item(act)
        
        # 컨테이너를 최종 View에 추가
        self.add_item(self.container)

    async def info_callback(self, it: discord.Interaction):
        if await check_black(it): return
        await it.response.defer(ephemeral=True)
        u_id = str(it.user.id)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT money, total_spent FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone(); conn.close()
        money, total_spent = (row[0], row[1]) if row else (0, 0)
        
        container = ui.Container(ui.TextDisplay(f"## {it.user.display_name}님의 정보"), accent_color=0xffffff)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 보유 잔액: {money:,}원\n<:dot_white:1482000567562928271> 누적 금액: {total_spent:,}원"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        selecao = ui.Select(placeholder="조회할 내역 선택", options=[
            discord.SelectOption(label="최근 충전 내역", value="charge", emoji="<:dot_white:1482000567562928271>"),
            discord.SelectOption(label="최근 구매 내역", value="purchase", emoji="<:dot_white:1482000567562928271>")
        ])

        async def resp(i: discord.Interaction):
            selected = selecao.values[0]
            conn2 = sqlite3.connect('vending_data.db'); cur2 = conn2.cursor()
            
            if selected == "charge":
                cur2.execute("SELECT amount, date, method FROM charge_logs WHERE user_id = ? AND amount > 0 ORDER BY date DESC LIMIT 5", (u_id,))
                logs = cur2.fetchall(); conn2.close()
                log_con = ui.Container(ui.TextDisplay("## 최근 충전 내역"), accent_color=0xffffff)
                if logs:
                    for l in logs:
                        log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                        log_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 금액: {l[0]:,}원 ({l[2]})\n<:dot_white:1482000567562928271> 시간: {l[1]}"))
                else:
                    log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    log_con.add_item(ui.TextDisplay("충전 내역이 없습니다"))
            
            elif selected == "purchase":
                cur2.execute("SELECT amount, date, method FROM charge_logs WHERE user_id = ? AND amount < 0 ORDER BY date DESC LIMIT 5", (u_id,))
                logs = cur2.fetchall(); conn2.close()
                log_con = ui.Container(ui.TextDisplay("## 최근 구매 내역"), accent_color=0xffffff)
                if logs:
                    for l in logs:
                        log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                        log_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 금액: {abs(l[0]):,}원 ({l[2].replace('제품구매(', '').replace(')', '')})\n<:dot_white:1482000567562928271> 시간: {l[1]}"))
                else:
                    log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    log_con.add_item(ui.TextDisplay("구매 내역이 없습니다"))
                
            await i.response.send_message(view=ui.LayoutView().add_item(log_con), ephemeral=True)
            
        selecao.callback = resp
        container.add_item(ui.ActionRow(selecao))
        # followup 사용 (defer를 했으므로)
        await it.followup.send(view=ui.LayoutView().add_item(container), ephemeral=True)

    # ... (나머지 shop_callback, chage_callback, buy_callback 함수들은 그대로 유지)
