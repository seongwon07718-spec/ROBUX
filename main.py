class CalculatorModal(disnake.ui.Modal):
    def __init__(self, serial_code):
        components = [
            disnake.ui.TextInput(
                label="계산할 금액 (원)",
                placeholder="예: 100000",
                custom_id="calc_amount",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=20,
            )
        ]
        super().__init__(
            title="수수료 계산기",
            custom_id=f"calc_modal_{serial_code}",
            components=components,
        )
