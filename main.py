class BankInfoLayout(ui.LayoutView):
    def __init__(self, name, amount, db_id):
        super().__init__(); self.name, self.amount, self.db_id = name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 입금 정보"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 은행명: {BANK_CONFIG['bank_name']}\n<:dot_white:1482000567562928271> 계좌번호: {BANK_CONFIG['account_num']}\n<:dot_white:1482000567562928271> 예금주: {BANK_CONFIG['owner']}\n<:dot_white:1482000567562928271> 충전금액: {self.amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("-# 5분 이내로 입금해주셔야 자동충전됩니다"))
        self.add_item(self.container)
