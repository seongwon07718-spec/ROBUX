# --- [ 전역 설정 변수 ] ---
BANK_CONFIG = {
    "bank_name": "카카오뱅크",
    "account_num": "7777-03-6763823",
    "owner": "정성원"
}
AUTO_LOG_ENABLED = True  # True면 로그 채널에 승인 버튼 전송, False면 전송 안함

# --- [ 계좌 설정 모달 ] ---
class AccountSetupModal(ui.Modal, title="계좌 정보 설정"):
    bank = ui.TextInput(label="은행명", placeholder="예: 카카오뱅크", min_length=2)
    account = ui.TextInput(label="계좌번호", placeholder="하이픈 포함 입력")
    owner = ui.TextInput(label="예금주", placeholder="성함 입력")

    async def on_submit(self, interaction: discord.Interaction):
        global AUTO_LOG_ENABLED
        BANK_CONFIG["bank_name"] = self.bank.value
        BANK_CONFIG["account_num"] = self.account.value
        BANK_CONFIG["owner"] = self.owner.value

        setup_con = ui.Container(ui.TextDisplay("## 계좌 설정 완료"), accent_color=0x00ff00)
        setup_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        setup_con.add_item(ui.TextDisplay(f"**은행:** {self.bank.value}\n**계좌:** {self.account.value}\n**예금주:** {self.owner.value}"))
        
        view = ui.LayoutView()
        
        # 카카오뱅크인 경우 자동충전 옵션 버튼 추가
        if "카카오" in self.bank.value or "카뱅" in self.bank.value:
            allow_btn = ui.Button(label="자동충전 허용 (로그X)", style=discord.ButtonStyle.green)
            deny_btn = ui.Button(label="자동충전 거부 (로그O)", style=discord.ButtonStyle.red)
            
            async def allow_cb(it):
                global AUTO_LOG_ENABLED
                AUTO_LOG_ENABLED = False
                await it.response.send_message("✅ 이제 자동충전 시 로그 채널에 승인 컨테이너가 뜨지 않습니다.", ephemeral=True)
            
            async def deny_cb(it):
                global AUTO_LOG_ENABLED
                AUTO_LOG_ENABLED = True
                await it.response.send_message("✅ 이제 자동충전 시에도 로그 채널에 승인 컨테이너가 발송됩니다.", ephemeral=True)
            
            allow_btn.callback = allow_cb
            deny_btn.callback = deny_cb
            setup_con.add_item(ui.ActionRow(allow_btn, deny_btn))
        
        view.add_item(setup_con)
        await interaction.response.send_message(view=view, ephemeral=True)

# --- [ 수정된 BankInfoLayout ] ---
class BankInfoLayout(ui.LayoutView):
    def __init__(self, name, amount, db_id):
        super().__init__(); self.name, self.amount, self.db_id = name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 입금 정보"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        # 전역 설정값(BANK_CONFIG)을 사용하도록 수정
        self.container.add_item(ui.TextDisplay(f"은행명: {BANK_CONFIG['bank_name']}\n계좌: {BANK_CONFIG['account_num']}\n예금주: {BANK_CONFIG['owner']}"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"입금자명: {self.name}\n충전금액: {self.amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("-# 5분 이내로 입금해주셔야 충전이 완료됩니다"))
        self.add_item(self.container)
    # ... (start_timer 생략, 기존과 동일)

# --- [ 수정된 BankModal on_submit ] ---
    async def on_submit(self, interaction: discord.Interaction):
        # ... (기존 검증 로직 생략)
        db_id = database.insert_request(interaction.user.id, self.amount.value)
        layout = BankInfoLayout(self.name.value, self.amount.value, db_id)
        await interaction.response.send_message(view=layout, ephemeral=True)

        # ✅ AUTO_LOG_ENABLED 설정에 따른 조건부 로그 발송
        if AUTO_LOG_ENABLED:
            log_chan = bot.get_channel(LOG_CHANNEL_ID)
            if log_chan: 
                await log_chan.send(view=AdminLogView(interaction.user, self.name.value, self.amount.value, db_id))

        name_val = self.name.value
        amount_val = self.amount.value
        key = f"{name_val}_{amount_val}"
        asyncio.create_task(self.watch_deposit(interaction, layout, name_val, amount_val, key))
        asyncio.create_task(layout.start_timer(interaction))

# --- [ 새로운 명령어 추가 ] ---
@bot.tree.command(name="계좌설정", description="입금 계좌 정보를 수정합니다")
async def set_account(interaction: discord.Interaction):
    await interaction.response.send_modal(AccountSetupModal())
