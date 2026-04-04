    async def on_submit(self, it: discord.Interaction):
        # 1. 초기 응답 설정
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### <a:1792loading:1487444148716965949>  충전 준비 중\n-# - **충전 서버 API** 연결 시도중 (1/3)"))
        
        # 첫 응답은 send_message로 시작
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        msg = await it.original_response()

        steps = [
            "-# - **입금자명/충전금액** 설정 중 (2/3)",
            "-# - **안전한 충전**을 위한 설정 중 (3/3)",
            "-# - **모든 설정이 완료되었습니다**"
        ]

        # 2. 로딩 단계 업데이트
        for step in steps:
            await asyncio.sleep(1.5)
            con.clear_items()
            con.add_item(ui.TextDisplay(f"### <a:1792loading:1487444148716965949>  충전 준비 중\n{step}"))
            await msg.edit(view=ui.LayoutView().add_item(con))

        # 3. 입금 대기 화면 전환
        await asyncio.sleep(1)
        con.clear_items()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### <a:1792loading:1487444148716965949>  입금 대기 중"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay(f"-# - **입금자명**은 반드시 본인 실명으로 입력해주세요\n-# - 입금 대기 시간은 **5분**입니다\n-# - 충전 처리는 입금 후 **최대 2~3분**까지 걸립니다\n-# - **5분 지나고 입금할 시 충전 안됩니다**"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay(f"**입금 계좌**: `{BANK_K}`\n**입금 금액**: `{int(self.amount.value):,}원`\n**입금자명**: `{self.depositor.value}`"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 버튼 생성 및 콜백 설정
        copy_btn = ui.Button(label="계좌복사", style=discord.ButtonStyle.gray, emoji="<:success:1489875582874554429>")
        copy_btn.callback = self.copy_callback
        
        # 버튼을 포함한 최종 뷰 업데이트 (it.response.edit_message 대신 msg.edit 사용)
        con.add_item(ui.ActionRow(copy_btn))
        await msg.edit(view=ui.LayoutView().add_item(con))
        
        # 복사용 텍스트 별도 전송 (선택사항)
        await it.followup.send(content=f"`{BANK_K}`", ephemeral=True)

        # 4. 입금 확인 루프
        key = f"{self.depositor.value}_{self.amount.value}"
        success = False
        for _ in range(60): # 5분 (5초 * 60회)
            if pending_deposits.get(key):
                success = True
                del pending_deposits[key]
                break
            await asyncio.sleep(5)

        # 5. 결과 처리
        con.clear_items()
        if success:
            con.accent_color = 0x5865F2
            con.add_item(ui.TextDisplay("### <a:1792loading:1487444148716965949>  충전 처리 중\n-# - 유저 **DB에 충전 기록** 저장 중 (1/2)"))
            await msg.edit(view=ui.LayoutView().add_item(con))
            
            await asyncio.sleep(1.5)
            
            con.clear_items()
            con.add_item(ui.TextDisplay("### <a:1792loading:1487444148716965949>  충전 처리 중\n-# - 입금 **금액 반영** 중 (2/2)"))
            await msg.edit(view=ui.LayoutView().add_item(con))

            conn = sqlite3.connect('robux_shop.db')
            cur = conn.cursor()
            # 밸런스 업데이트 쿼리
            cur.execute("INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?", 
                        (str(it.user.id), int(self.amount.value), int(self.amount.value)))
            conn.commit()
            conn.close()

            await asyncio.sleep(1.5)

            con.clear_items()
            con.accent_color = 0x5865F2
            con.add_item(ui.TextDisplay("### <:emoji_19:1487441741484392498>  충전 완료"))
            con.add_item(ui.TextDisplay(f"-# - 잔액이 성공적으로 충전되었습니다\n-# - **충전 금액:** `{int(self.amount.value):,}원`"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("-# - 정보 버튼을 눌러 잔액을 확인하세요!"))
        else:
            con.accent_color = 0xED4245 # 실패 시 빨간색 계열 권장
            con.add_item(ui.TextDisplay("### <:emoji_19:1487441741484392498>  충전 실패"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("-# - 시간 내에 입금이 확인되지 않았습니다\n-# - 다시 충전 신청을 해주세요"))
        
        await msg.edit(view=ui.LayoutView().add_item(con))

