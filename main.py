        key = f"{self.depositor.value}_{self.amount.value}"
        success = False
        for _ in range(60): # 5분 대기
            if pending_deposits.get(key):
                success = True
                del pending_deposits[key]
                break
            await asyncio.sleep(5)

        con.clear_items()
        
        if success:
            # 1. DB 기록 중 단계 표시
            con.accent_color = 0x5865F2
            con.add_item(ui.TextDisplay("## ⚙️ 처리 중..."))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("🔄 유저 DB에 충전 기록 저장 중 (1/2)"))
            await msg.edit(view=ui.LayoutView().add_item(con))
            
            await asyncio.sleep(1.5) # 처리 느낌을 주기 위한 지연
            
            # 2. 금액 반영 중 단계 표시
            con.clear_items()
            con.add_item(ui.TextDisplay("## ⚙️ 처리 중..."))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("✅ 유저 DB에 충전 기록 저장 완료 (1/2)\n🔄 입금 금액 반영 중 (2/2)"))
            await msg.edit(view=ui.LayoutView().add_item(con))

            # 실제 DB 반영 로직
            conn = sqlite3.connect('robux_shop.db')
            cur = conn.cursor()
            cur.execute("INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?", 
                        (str(it.user.id), int(self.amount.value), int(self.amount.value)))
            conn.commit()
            conn.close()

            await asyncio.sleep(1.5)

            # 3. 최종 완료 화면
            con.clear_items()
            con.accent_color = 0x57F287 # 녹색
            con.add_item(ui.TextDisplay(f"## 🎉 충전 완료\n\n<@{it.user.id}> 님의 잔액이 성공적으로 충전되었습니다!\n**충전 금액:** `{int(self.amount.value):,}원`"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("-# 내 정보 버튼을 눌러 잔액을 확인하실 수 있습니다."))
        
        else:
            # 충전 실패 화면
            con.accent_color = 0xED4245 # 빨간색
            con.add_item(ui.TextDisplay("## ❌ 충전 실패\n\n시간 내에 입금이 확인되지 않았습니다.\n문의가 필요하시면 관리자를 호출해주세요."))
        
        await msg.edit(view=ui.LayoutView().add_item(con))

