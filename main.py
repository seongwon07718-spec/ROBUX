# --- 입금 정보 입력 모달 (핵심 수정 부분) ---
class ChargeModal(ui.Modal, title="계좌이체 충전 신청"):
    depositor = ui.TextInput(label="입금자명", placeholder="입금자명", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전 금액", placeholder="숫자만 입력", min_length=3)

    async def on_submit(self, it: discord.Interaction):
        # 1. 초기 로딩 화면 전송
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("## ⏳ 충전 준비 중..."))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        status_text = ui.TextDisplay("🔄 충전 서버 api 연결 중 (1/3)")
        con.add_item(status_text)
        
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        msg = await it.original_response()

        # 2. 단계별 텍스트 수정 애니메이션
        steps = [
            "✅ 충전 서버 api 연결 완료 (1/3)\n🔄 입금자명/충전금액 설정 중 (2/3)",
            "✅ 입금자명/충전금액 설정 완료 (2/3)\n🔄 안전한 충전을 위한 설정 중 (3/3)",
            "✅ 모든 설정이 완료되었습니다! (3/3)"
        ]

        for step in steps:
            await asyncio.sleep(1.2)
            # 기존 아이템 제거 후 새 텍스트 추가로 수정 효과
            con.clear_items()
            con.add_item(ui.TextDisplay("## ⏳ 충전 준비 중..."))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay(step))
            await msg.edit(view=ui.LayoutView().add_item(con))

        # 3. 계좌 안내 화면으로 교체
        await asyncio.sleep(1)
        con.clear_items()
        con.accent_color = 0xFEE75C # 노란색
        con.add_item(ui.TextDisplay(f"## 💳 입금 안내\n\n**계좌번호:** `{BANK_INFO}`\n**입금자명:** `{self.depositor.value}`\n**입금금액:** `{int(self.amount.value):,}원`"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay("⚠️ 입금자명과 금액이 일치해야 자동으로 충전됩니다."))
        await msg.edit(view=ui.LayoutView().add_item(con))

        # 4. 자동 충전 감지 대기 (FastAPI와 연동)
        key = f"{self.depositor.value}_{self.amount.value}"
        success = False
        for _ in range(60): # 5분 대기
            if pending_deposits.get(key):
                success = True
                del pending_deposits[key]
                break
            await asyncio.sleep(5)

        # 5. 결과 업데이트
        con.clear_items()
        if success:
            # DB 업데이트 로직 (생략)
            con.accent_color = 0x57F287 # 초록색
            con.add_item(ui.TextDisplay(f"## 🎉 충전 완료\n\n<@{it.user.id}> 님의 잔액이 성공적으로 충전되었습니다!"))
        else:
            con.accent_color = 0xED4245 # 빨간색
            con.add_item(ui.TextDisplay("## ❌ 충전 실패\n\n시간 내에 입금이 확인되지 않았습니다."))
        
        await msg.edit(view=ui.LayoutView().add_item(con))

# --- 자판기 메뉴 내 충전 버튼 콜백 (에러 발생 지점 수정) ---
async def main_callback(self, it: discord.Interaction):
    cid = it.data['custom_id']
    if cid == "charge":
        con = ui.Container()
        con.accent_color = 0xffffff
        con.add_item(ui.TextDisplay("## 💳 충전 수단 선택\n원하시는 충전 방식을 선택해주세요."))
        
        # 버튼을 ActionRow에 담아서 컨테이너에 추가 (에러 해결 핵심)
        btn_bank = ui.Button(label="계좌이체", style=discord.ButtonStyle.green, emoji="🏦")
        async def bank_cb(i: discord.Interaction):
            await i.response.send_modal(ChargeModal())
        btn_bank.callback = bank_cb
        
        # 버튼을 컨테이너 안에 넣어서 구조를 맞춤
        con.add_item(ui.ActionRow(btn_bank))
        
        # 전송 시에는 LayoutView에 컨테이너 하나만 담아서 보냄
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

