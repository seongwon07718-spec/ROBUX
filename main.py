# 구매가 성공했을 때 실행되는 로직 예시
def update_total_spent(u_id, item_price):
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()
    
    # 1. 사용자의 money 차감 및 total_spent 누적 합산
    cur.execute("""
        UPDATE users 
        SET money = money - ?, 
            total_spent = total_spent + ? 
        WHERE user_id = ?
    """, (item_price, item_price, u_id))
    
    # 2. charge_logs에도 구매 내역 기록 (음수 금액으로 저장)
    cur.execute("""
        INSERT INTO charge_logs (user_id, amount, date, method) 
        VALUES (?, ?, datetime('now', 'localtime'), ?)
    """, (u_id, -item_price, f"제품구매({item_name})"))
    
    conn.commit()
    conn.close()

async def info_callback(self, it: discord.Interaction):
    if await check_black(it): return
    
    u_id = str(it.user.id)
    conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
    # total_spent를 함께 조회합니다.
    cur.execute("SELECT money, total_spent FROM users WHERE user_id = ?", (u_id,))
    row = cur.fetchone(); conn.close()
    
    # 데이터가 없을 경우 기본값 0
    money, total_spent = (row[0], row[1]) if row else (0, 0)
    
    container = ui.Container(ui.TextDisplay(f"## {it.user.display_name}님의 정보"), accent_color=0xffffff)
    container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    # 누적 금액(total_spent) 표시 부분
    container.add_item(ui.TextDisplay(
        f"<:dot_white:1482000567562928271> 보유 잔액: {money:,}원\n"
        f"<:dot_white:1482000567562928271> 누적 금액: {total_spent:,}원"
    ))
    container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    selecao = ui.Select(placeholder="조회할 내역 선택", options=[
        discord.SelectOption(label="최근 충전 내역", value="charge", emoji="<:dot_white:1482000567562928271>"),
        discord.SelectOption(label="최근 구매 내역", value="purchase", emoji="<:dot_white:1482000567562928271>")
    ])

    async def resp_callback(i: discord.Interaction):
        selected_val = selecao.values[0]
        conn2 = sqlite3.connect('vending_data.db'); cur2 = conn2.cursor()
        
        if selected_val == "charge":
            # amount > 0 (충전)
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
        
        elif selected_val == "purchase":
            # amount < 0 (구매)
            cur2.execute("SELECT amount, date, method FROM charge_logs WHERE user_id = ? AND amount < 0 ORDER BY date DESC LIMIT 5", (u_id,))
            logs = cur2.fetchall(); conn2.close()
            log_con = ui.Container(ui.TextDisplay("## 최근 구매 내역"), accent_color=0xffffff)
            if logs:
                for l in logs:
                    log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    # 금액은 절대값(abs) 처리하여 양수로 표기
                    log_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 금액: {abs(l[0]):,}원 ({l[2].replace('제품구매(', '').replace(')', '')})\n<:dot_white:1482000567562928271> 시간: {l[1]}"))
            else:
                log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                log_con.add_item(ui.TextDisplay("구매 내역이 없습니다"))
            
        await i.response.send_message(view=ui.LayoutView().add_item(log_con), ephemeral=True)
        
    selecao.callback = resp_callback
    container.add_item(ui.ActionRow(selecao))
    
    await it.response.send_message(view=ui.LayoutView().add_item(container), ephemeral=True)
