async def watch_deposit(self, interaction, layout, name, amount, key):
    while True:
        await asyncio.sleep(3)
        if pending_deposits.get(key):
            amount_int = int(amount)
            u_id = str(interaction.user.id)
            
            conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
            # 잔액 업데이트
            cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount_int, amount_int, u_id))
            
            # ✅ 최근 충전 내역 기록 (자동)
            cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                        (u_id, amount_int, time.strftime('%Y-%m-%d %H:%M'), "자동(계좌)"))
            
            conn.commit(); conn.close()
            
            if key in pending_deposits: del pending_deposits[key]
            database.update_status(layout.db_id, "완료")

            # 컨테이너 업데이트 로직...
            layout.container.clear_items()
            layout.container.accent_color = 0x00ff00
            layout.container.add_item(ui.TextDisplay(f"## ✅ 자동충전 완료\n금액: **{amount_int:,}원**"))
            await interaction.edit_original_response(view=layout)
            break
