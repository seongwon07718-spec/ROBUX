class BankInfoLayout(ui.LayoutView):
    def __init__(self, name, amount, db_id):
        super().__init__()
        self.name, self.amount, self.db_id = name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 입금 정보"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 은행명: {BANK_CONFIG['bank_name']}\n<:dot_white:1482000567562928271> 계좌번호: {BANK_CONFIG['account_num']}\n<:dot_white:1482000567562928271> 예금주: {BANK_CONFIG['owner']}\n<:dot_white:1482000567562928271> 충전금액: {self.amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("-# 5분 이내로 입금해주셔야 자동충전됩니다"))
        
        # 버튼을 self(인스턴스) 변수로 만들어 어디서든 접근 가능하게 합니다.
        self.copy_btn = ui.Button(label="계좌복사", style=discord.ButtonStyle.gray, emoji="<:copy:1482673389679415316>")
        self.copy_btn.callback = self.copy_callback
        
        self.container.add_item(ui.ActionRow(self.copy_btn))
        self.add_item(self.container)

    async def copy_callback(self, it: discord.Interaction):
        # 1. 버튼 비활성화 (self.copy_btn을 직접 수정)
        self.copy_btn.disabled = True
        
        # 2. 변경된 버튼 상태를 메시지에 반영
        await it.response.edit_message(view=self)
        
        # 3. 계좌번호 전송 (사용자가 복사할 수 있도록)
        await it.followup.send(content=f"{BANK_CONFIG['account_num']}", ephemeral=True)
