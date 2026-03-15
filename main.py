class StockFinalEditModal(ui.Modal):
    def __init__(self, name, stock):
        super().__init__(title=f"📝 {name} 재고 수정")
        self.name = name
        # 기존 재고를 default 값으로 넣어둠
        self.edit_input = ui.TextInput(
            label="수정할 재고 수량",
            default=str(stock),
            placeholder="숫자만 입력하세요",
            required=True
        )
        self.add_item(self.edit_input)

    async def on_submit(self, it: discord.Interaction):
        if not self.edit_input.value.isdigit():
            return await it.response.send_message("❌ 숫자만 입력 가능합니다.", ephemeral=True)
            
        new_val = int(self.edit_input.value)
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("UPDATE products SET stock = ? WHERE name = ?", (new_val, self.name))
        conn.commit(); conn.close()
        
        await it.response.send_message(f"✅ **{self.name}**의 재고가 **{new_val}개**로 수정되었습니다!", ephemeral=True)
