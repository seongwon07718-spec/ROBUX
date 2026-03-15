class StockDataListModal(ui.Modal):
    def __init__(self, name, current_data):
        super().__init__(title=f"{name} 재고 관리")
        self.name = name
        
        # 핵심: placeholder가 아니라 'default'에 실제 데이터를 넣어야 눈에 보입니다.
        self.data_input = ui.TextInput(
            label="재고 리스트",
            style=discord.TextStyle.paragraph,
            default=str(current_data), # 여기에 DB에서 가져온 재고(3739, 4739 등)가 들어갑니다.
            placeholder="재고가 비어있습니다.", # 데이터가 하나도 없을 때만 보이는 문구
            required=False
        )
        self.add_item(self.data_input)

    async def on_submit(self, it: discord.Interaction):
        # 사용자가 수정(삭제 포함)한 최종 텍스트
        updated_data = self.data_input.value
        
        # 줄바꿈 기준으로 남은 재고 개수 계산
        new_count = len([l for l in updated_data.split('\n') if l.strip()])

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        
        # 수정된 리스트와 개수를 DB에 저장
        cur.execute("UPDATE products SET stock_data = ?, stock = ? WHERE name = ?", 
                    (updated_data, new_count, self.name))
        conn.commit()
        conn.close()
        
        await it.response.send_message(f"**__{self.name}__ 재고 수정 완료되었습니다 (현재: __{new_count}__개)**", ephemeral=True)
