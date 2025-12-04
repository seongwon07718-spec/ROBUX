class TxidSubmitView(disnake.ui.View):
    def __init__(self, transaction_id: int):
        super().__init__(timeout=600)
        self.transaction_id = transaction_id
    
        # 버튼을 수동으로 추가하여 custom_id에 transaction_id 포함
        self.add_item(disnake.ui.Button(
            label="TXID 전송", 
            style=disnake.ButtonStyle.primary, 
            custom_id=f"submit_txid_{transaction_id}"
        ))

    @disnake.ui.button(label="TXID 전송", style=disnake.ButtonStyle.primary)  # 데코레이터 제거 가능
    async def submit_txid_button_callback(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(TxidInputModal(self.transaction_id, inter.message.id))
