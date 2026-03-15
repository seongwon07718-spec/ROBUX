class StockDataListModal(ui.Modal):
    def __init__(self, name, current_data):
        # 다른 부분은 바꾸지 않고 요청하신 구조를 유지합니다.
        super().__init__(title=f"{name} 재고 관리")
        self.name = name
        
        self.data_input = ui.TextInput(
            label="재고 리스트",
            style=discord.TextStyle.paragraph,
            default=str(current_data), # 기존 재고 리스트를 입력창에 표시
            placeholder="수정하거나 삭제하세요",
            required=False
        )
        self.add_item(self.data_input)

    async def on_submit(self, it: discord.Interaction):
        updated_data = self.data_input.value
        # 줄바꿈 기준으로 실제 데이터가 있는 줄만 계산
        new_count = len([l for l in updated_data.split('\n') if l.strip()])

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        # stock_data와 stock 수량을 동시에 업데이트
        cur.execute("UPDATE products SET stock_data = ?, stock = ? WHERE name = ?", 
                    (updated_data, new_count, self.name))
        conn.commit()
        conn.close()
        
        await it.response.send_message(f"**__{self.name}__ 재고 수정 완료되었습니다 (현재: __{new_count}__개)**", ephemeral=True)
