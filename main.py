        key = f"{self.depositor.value}_{self.amount.value}"
        success = False
        for _ in range(60):
            if pending_deposits.get(key):
                success = True
                del pending_deposits[key]
                break
            await asyncio.sleep(5)

        con.clear_items()
        if success:
            con.accent_color = 0x57F287
            con.add_item(ui.TextDisplay(f"## 충전 완료\n\n<@{it.user.id}> 님의 잔액이 성공적으로 충전되었습니다!"))
        else:
            con.accent_color = 0xED4245
            con.add_item(ui.TextDisplay("## ❌ 충전 실패\n\n시간 내에 입금이 확인되지 않았습니다."))
        
        await msg.edit(view=ui.LayoutView().add_item(con))
