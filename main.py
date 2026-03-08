# --- [ iOS 자동충전 서버 설정 ] ---
app = FastAPI()

class ChargeData(BaseModel):
    message: str

pending_deposits = {}

@app.post("/charge")
async def receive_charge(data: ChargeData):
    msg = data.message.strip()
    print(f"📥 [입금 문자 수신]:\n{msg}")
    
    # 1. 금액 추출 (숫자만 추출, 예: "입금 100원" -> "100")
    amount_match = re.search(r'입금\s*([\d,]+)원', msg)
    # 2. 이름 추출 (카카오뱅크 특유의 '입금' 줄 아래 이름 위치 확인)
    name_match = re.search(r'원\n([가-힣]+)\n잔액', msg)
    
    if amount_match and name_match:
        amount = amount_match.group(1).replace(",", "") # 콤마 제거
        name = name_match.group(1)
        
        key = f"{name}_{amount}"
        pending_deposits[key] = True
        print(f"✅ [인식 완료]: 이름({name}), 금액({amount}) -> 대기열 저장")
    else:
        # 일반적인 포맷(홍길동 10000)으로도 한 번 더 시도
        fallback = re.search(r'([가-힣]+)\s*(\d+)', msg)
        if fallback:
            key = f"{fallback.group(1)}_{fallback.group(2)}"
            pending_deposits[key] = True
            print(f"✅ [인식 완료]: {key} (일반 포맷)")

    return {"ok": True}

# --- [ BankModal 부분 수정 ] ---
class BankModal(ui.Modal, title="계좌이체 충전"):
    name = ui.TextInput(label="입금자명", placeholder="입금하실 성함을 입력해주세요", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전금액", placeholder="금액을 입력해주세요 (숫자만)", min_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        if not re.fullmatch(r'[가-힣]+', self.name.value):
            return await interaction.response.send_message("**입금자명은 한글로만 입력해주세요**", ephemeral=True)
        if not self.amount.value.isdigit():
            return await interaction.response.send_message("**충전금액은 숫자만 입력해주세요**", ephemeral=True)

        db_id = database.insert_request(interaction.user.id, self.amount.value)
        layout = BankInfoLayout(self.name.value, self.amount.value, db_id)
        await interaction.response.send_message(view=layout, ephemeral=True)

        log_chan = bot.get_channel(LOG_CHANNEL_ID)
        if log_chan: await log_chan.send(view=AdminLogView(interaction.user, self.name.value, self.amount.value, db_id))

        # ✅ 입금자 정보와 일치하는지 대기열 확인
        name_val = self.name.value
        amount_val = self.amount.value
        key = f"{name_val}_{amount_val}"

        # 봇이 확인하는 시점에 이미 문자가 와있을 수도 있으므로 즉시 체크
        if pending_deposits.get(key):
            await self.process_auto_charge(interaction, name_val, amount_val, key)
        else:
            # 아직 문자가 안 왔다면, 30초 동안 2초 간격으로 실시간 감시 (백그라운드)
            asyncio.create_task(self.watch_deposit(interaction, name_val, amount_val, key))
        
        asyncio.create_task(layout.start_timer(interaction))

    async def watch_deposit(self, interaction, name, amount, key):
        """실시간으로 pending_deposits를 감시하여 입금 확인 즉시 처리"""
        for _ in range(15): # 30초 동안 확인
            await asyncio.sleep(2)
            if pending_deposits.get(key):
                await self.process_auto_charge(interaction, name, amount, key)
                break

    async def process_auto_charge(self, interaction, name, amount, key):
        """실제 충전 처리 로직"""
        amount_int = int(amount)
        u_id = str(interaction.user.id)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
        cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount_int, amount_int, u_id))
        conn.commit(); conn.close()
        
        if key in pending_deposits: del pending_deposits[key]
        
        try:
            await interaction.followup.send(f"✅ **입금이 확인되었습니다!**\n**입금자:** {name}\n**충전금액:** {amount_int:,}원이 반영되었습니다.", ephemeral=True)
        except:
            pass
