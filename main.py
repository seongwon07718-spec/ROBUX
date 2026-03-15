class ProductEditModal(ui.Modal):
    def __init__(self, category):
        super().__init__(title=f"[{category}] 제품 설정")
        self.category = category

        self.prod_dropdown = ui.Label(
            text=f"수정할 {category} 제품을 선택하세요",
            component=ProductSelect(category=category)
        )
        self.add_item(self.prod_dropdown)

        self.price_input = ui.TextInput(label="가격", placeholder="수정할 가격을 적어주세요", required=False)
        self.add_item(self.price_input)

        self.stock_input = ui.TextInput(
            label="재고 입고", 
            style=discord.TextStyle.paragraph, 
            placeholder="재고를 추가해주세요",
            required=False
        )
        self.add_item(self.stock_input)

    async def on_submit(self, it: discord.Interaction):
        name = self.prod_dropdown.component.values[0]
        if name == "none":
            return await it.response.send_message("**관리할 제품이 없습니다**", ephemeral=True)

        lines = self.stock_input.value.split('\n')
        add_count = len([l for l in lines if l.strip()])

        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        if self.price_input.value and self.price_input.value.isdigit():
            cur.execute("UPDATE products SET price = ? WHERE name = ?", (int(self.price_input.value), name))
        
        if add_count > 0:
            cur.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (add_count, name))
        
        conn.commit(); conn.close()
        await it.response.send_message(f"**__{name}__ 설정 및 __{add_count}__개 입고가 완료되었습니다**", ephemeral=True)
