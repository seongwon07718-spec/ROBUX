class AdminLogView(ui.LayoutView):
    def __init__(self, user, name, amount, db_id):
        super().__init__(); self.user, self.name, self.amount, self.db_id = user, name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 충전 신청"), accent_color=0xffff00)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**신청자:** {user.mention}\n**입금자명:** {name}\n**신청금액:** {amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        approve_btn = ui.Button(label="완료", style=discord.ButtonStyle.green); approve_btn.callback = self.approve_callback
        cancel_btn = ui.Button(label="취소", style=discord.ButtonStyle.red); cancel_btn.callback = self.cancel_callback
        self.container.add_item(ui.ActionRow(approve_btn, cancel_btn)); self.add_item(self.container)

    async def approve_callback(self, interaction: discord.Interaction):
        # 1. 데이터베이스 업데이트 (잔액 추가 및 내역 기록)
        amount_int = int(self.amount)
        u_id = str(self.user.id)
        
        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        # 잔액 및 누적 금액 업데이트
        cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount_int, amount_int, u_id))
        # ✅ 최근 충전 내역에 기록 저장 (수동 승인)
        cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                    (u_id, amount_int, time.strftime('%Y-%m-%d %H:%M'), "수동(관리자)"))
        conn.commit()
        conn.close()

        # 2. 신청 상태 업데이트 (requests 테이블)
        database.update_status(self.db_id, "완료")

        # 3. UI 업데이트
        self.container.clear_items()
        self.container.accent_color = 0x00ff00
        self.container.add_item(ui.TextDisplay(f"## 충전 완료 (수동 승인)"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**처리자:** {interaction.user.mention}\n**대상:** {self.user.mention}\n**금액:** {self.amount}원"))
        
        await interaction.response.edit_message(view=self)
        
        try: 
            await self.user.send(f"**{self.amount}원 충전이 완료되었습니다 (관리자 승인)**")
        except: 
            pass

    async def cancel_callback(self, interaction: discord.Interaction):
        database.update_status(self.db_id, "취소")
        self.container.clear_items()
        self.container.accent_color = 0xff0000
        self.container.add_item(ui.TextDisplay(f"## 충전 취소"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**처리자:** {interaction.user.mention}\n**대상:** {self.user.mention}\n**금액:** {self.amount}원"))
        
        await interaction.response.edit_message(view=self)
