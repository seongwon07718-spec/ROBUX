class StockDataListModal(ui.Modal):
    def __init__(self, name, current_data):
        super().__init__(title=f"{name} 재고 관리")
        self.name = name
        
        # [핵심 수정] default 자리에 current_data를 넣어줘야 실제 재고가 보입니다.
        self.data_input = ui.TextInput(
            label="재고 리스트",
            style=discord.TextStyle.paragraph,
            default=str(current_data), # ← "수정하거나 삭제하세요" 대신 실제 재고가 적힙니다.
            placeholder="비어있음 (재고를 입력하거나 수정하세요)",
            required=False
        )
        self.add_item(self.data_input)

    async def on_submit(self, it: discord.Interaction):
        # 사용자가 수정한 텍스트 전체를 가져옵니다.
        updated_data = self.data_input.value
        # 줄바꿈 기준으로 남은 재고 개수 다시 계산
        new_count = len([l for l in updated_data.split('\n') if l.strip()])

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        # 수정된 텍스트와 개수를 DB에 저장합니다.
        cur.execute("UPDATE products SET stock_data = ?, stock = ? WHERE name = ?", 
                    (updated_data, new_count, self.name))
        conn.commit()
        conn.close()
        
        await it.response.send_message(f"**__{self.name}__ 재고 수정 완료되었습니다 (현재: __{new_count}__개)**", ephemeral=True)
