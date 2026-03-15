class BankInfoLayout(ui.LayoutView):
    def __init__(self, name, amount, db_id):
        super().__init__()
        self.name, self.amount, self.db_id = name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 입금 정보"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 은행명: {BANK_CONFIG['bank_name']}\n<:dot_white:1482000567562928271> 계좌번호: {BANK_CONFIG['account_num']}\n<:dot_white:1482000567562928271> 예금주: {BANK_CONFIG['owner']}\n<:dot_white:1482000567562928271> 충전금액: {self.amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("-# 5분 이내로 입금해주셔야 자동충전됩니다"))
        
        # 계좌복사 버튼 생성
        copy_btn = ui.Button(label="계좌복사", style=discord.ButtonStyle.gray, emoji="📋")
        copy_btn.callback = self.copy_callback
        
        # 버튼을 액션로우에 담아 컨테이너에 추가
        self.container.add_item(ui.ActionRow(copy_btn))
        self.add_item(self.container)

    async def copy_callback(self, it: discord.Interaction):
        # 계좌번호 가져오기
        account = BANK_CONFIG['account_num']
        
        # 버튼 비활성화 처리
        # it.message.components[0].children[0]는 현재 클릭된 버튼을 의미합니다.
        # 가장 확실한 방법은 클릭된 버튼의 disabled 속성을 바꾸고 메시지를 수정하는 것입니다.
        for item in self.container.items:
            if isinstance(item, ui.ActionRow):
                for child in item.children:
                    if isinstance(child, ui.Button) and child.label == "계좌복사":
                        child.disabled = True # 버튼 비활성화
        
        # 메시지 수정과 함께 계좌번호를 일반 텍스트로 보내서 복사하기 편하게 함
        await it.response.edit_message(view=self)
        await it.followup.send(content=f"{account}", ephemeral=True)

