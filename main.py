        async def resp(i: discord.Interaction):
            selected = selecao.values[0]
            conn2 = sqlite3.connect('vending_data.db'); cur2 = conn2.cursor()
            
            if selected == "charge":
                cur2.execute("SELECT amount, date, method FROM charge_logs WHERE user_id = ? AND amount > 0 ORDER BY date DESC LIMIT 5", (u_id,))
                logs = cur2.fetchall(); conn2.close()
                if logs:
                    for l in logs:

                    log_text = "\n".join([f"<:dot_white:1482000567562928271> 금액: {l[0]:,}원 ({l[2]})\n<:dot_white:1482000567562928271> 시간: {l[1]}" for l in logs])
                    log_con = ui.Container(ui.TextDisplay("## 최근 충전 내역"), accent_color=0xffffff)
                    log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    log_con.add_item(ui.TextDisplay(log_text))
                else: log_con.add_item(ui.TextDisplay("충전 내역이 없습니다"))
            
            elif selected == "purchase":
                cur2.execute("SELECT amount, date, method FROM charge_logs WHERE user_id = ? AND amount < 0 ORDER BY date DESC LIMIT 5", (u_id,))
                logs = cur2.fetchall(); conn2.close()
                log_con = ui.Container(ui.TextDisplay("## 최근 구매 내역"), accent_color=0xffffff)
                log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                if logs:
                    log_text = "\n".join([f"<:dot_white:1482000567562928271> 금액: {abs(l[0]):,}원 ({l[2].replace('제품구매(', '').replace(')', '')})\n<:dot_white:1482000567562928271> 시간: {l[1]}" for l in logs])
                    log_con.add_item(ui.TextDisplay(log_text))
                else: log_con.add_item(ui.TextDisplay("구매 내역이 없습니다"))
                
            await i.response.send_message(view=ui.LayoutView().add_item(log_con), ephemeral=True)
            
        selecao.callback = resp
        container.add_item(ui.ActionRow(selecao))
        await it.followup.send(view=ui.LayoutView().add_item(container), ephemeral=True)
