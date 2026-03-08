class BankModal(ui.Modal, title="계좌이체 충전"):
    name = ui.TextInput(label="입금자명", placeholder="입금하실 성함을 입력해주세요", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전금액", placeholder="금액을 입력해주세요 (숫자만)", min_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        # 1. 입력값 유효성 검사
        if not re.fullmatch(r'[가-힣]+', self.name.value):
            return await interaction.response.send_message("**입금자명은 한글로만 입력해주세요**", ephemeral=True)
        if not self.amount.value.isdigit():
            return await interaction.response.send_message("**충전금액은 숫자만 입력해주세요**", ephemeral=True)

        # 2. 도배 방지 (5분 쿨타임)
        last_time = database.get_last_request_time(interaction.user.id)
        current_time = time.time()
        if current_time - last_time < 300:
            remaining = int(300 - (current_time - last_time))
            return await interaction.response.send_message(f"**이전 신청 기록이 있습니다. {remaining}초 후 다시 시도해주세요**", ephemeral=True)

        # 3. 묻지도 따지지도 않고 계좌 정보부터 전송 (에러 방지 위해 content 없이 view만)
        db_id = database.insert_request(interaction.user.id, self.amount.value)
        layout = BankInfoLayout(self.name.value, self.amount.value, db_id)
        
        await interaction.response.send_message(view=layout, ephemeral=True)

        # 4. 관리자 채널에 신청 로그 전송
        log_chan = bot.get_channel(LOG_CHANNEL_ID)
        if log_chan:
            await log_chan.send(view=AdminLogView(interaction.user, self.name.value, self.amount.value, db_id))

        # 5. 계좌 정보를 띄운 상태에서 백그라운드로 자동 충전 확인
        charge_msg = f"{self.name.value} {self.amount.value}"
        result = ios_charge.send_charge_message(charge_msg)

        if result.get("ok"):
            # 자동 충전 내역이 확인되면 즉시 잔액 업데이트 후 알림 전송
            amount_int = int(self.amount.value)
            u_id = str(interaction.user.id)
            conn = sqlite3.connect('vending_data.db')
            cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
            cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount_int, amount_int, u_id))
            conn.commit()
            conn.close()

            # 계좌 정보창 아래에 별도의 메시지로 성공 알림
            await interaction.followup.send(f"✅ **입금이 확인되어 {amount_int:,}원이 자동 충전되었습니다!**", ephemeral=True)
        
        # 6. 5분 타이머 시작
        asyncio.create_task(layout.start_timer(interaction))

# --- [봇 실행 및 안내 문구 부분] ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("-" * 40)
    print(f"✅ 자판기 봇 로그인: {bot.user}")
    print(f"📱 iOS 자동충전 시스템: 정상 작동 중")
    print(f"🔗 외부 접속 주소: https://pay.rbxshop.cloud")
    print("-" * 40)
