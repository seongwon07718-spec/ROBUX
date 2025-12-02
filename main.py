class FeeModal(discord.ui.Modal, title="수수료 계산"):
    def __init__(self, is_dollar: bool):
        super().__init__()
        self.is_dollar = is_dollar

        label = "달러" if self.is_dollar else "원화"
        placeholder = f"계산할 금액을 {label} 기준으로 입력해주세요!"

        # TextInput 생성은 super().__init__() 후에 하는 게 권장됨
        self.amount = discord.ui.TextInput(
            label=label,
            placeholder=placeholder,
            required=True
        )
        self.add_item(self.amount)
