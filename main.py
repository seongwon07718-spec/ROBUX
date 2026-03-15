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
                # 충전 내역 (amount > 0)
                cur2.execute("SELECT amount, date, method FROM charge_logs WHERE user_id = ? AND amount > 0 ORDER BY date DESC LIMIT 5", (u_id,))
                logs = cur2.fetchall(); conn2.close()
                log_con = ui.Container(ui.TextDisplay("## 최근 충전 내역"), accent_color=0xffffff)
                log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                if logs:
                    # 충전 시간과 금액, 수단 표시
                    log_text = "\n".join([f"<:dot_white:1482000567562928271> **시간:** {l[1]}\n　┗ **금액:** {l[0]:,}원 ({l[2]})" for l in logs])
                    log_con.add_item(ui.TextDisplay(log_text))
                else: log_con.add_item(ui.TextDisplay("충전 내역이 없습니다"))
            
            elif selected == "purchase":
                # 구매 내역 (amount < 0)
                cur2.execute("SELECT amount, date, method FROM charge_logs WHERE user_id = ? AND amount < 0 ORDER BY date DESC LIMIT 5", (u_id,))
                logs = cur2.fetchall(); conn2.close()
                log_con = ui.Container(ui.TextDisplay("## 최근 구매 내역"), accent_color=0xffffff)
                log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                if logs:
                    # 구매 시간, 제품명(method에서 추출), 금액 표시
                    log_text = "\n".join([f"<:dot_white:1482000567562928271> **시간:** {l[1]}\n　┗ **내용:** {l[2].replace('제품구매(', '').replace(')', '')}\n　┗ **금액:** {abs(l[0]):,}원" for l in logs])
                    log_con.add_item(ui.TextDisplay(log_text))
                else: log_con.add_item(ui.TextDisplay("구매 내역이 없습니다"))
                
            await i.response.send_message(view=ui.LayoutView().add_item(log_con), ephemeral=True)
            
        selecao.callback = resp
        container.add_item(ui.ActionRow(selecao))
        await it.followup.send(view=ui.LayoutView().add_item(container), ephemeral=True)
