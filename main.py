class AdminLogView(ui.LayoutView):
    # ... (기존 __init__ 생략)

    async def approve_callback(self, interaction: discord.Interaction):
        amount_int = int(self.amount)
        u_id = str(self.user.id)
        
        # 데이터베이스 처리
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount_int, amount_int, u_id))
        
        # ✅ 최근 충전 내역 기록 (수동 승인)
        cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                    (u_id, amount_int, time.strftime('%Y-%m-%d %H:%M'), "수동(관리자)"))
        
        conn.commit(); conn.close()
        
        database.update_status(self.db_id, "완료")
        
        # 관리자 로그 컨테이너 업데이트
        self.container.clear_items(); self.container.accent_color = 0x00ff00
        self.container.add_item(ui.TextDisplay(f"## 충전 완료 (수동)"))
        # ... (이후 기존 코드와 동일하게 처리)
        await interaction.response.edit_message(view=self)
