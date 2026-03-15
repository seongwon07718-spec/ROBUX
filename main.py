class ProductDeleteModal(ui.Modal):
    def __init__(self, category):
        super().__init__(title=f"🗑️ [{category}] 제품 삭제")
        self.prod_select = ui.Label(
            text=f"삭제할 {category} 제품을 선택하세요",
            component=ProductSelect(category=category)
        )
        self.add_item(self.prod_select)

    async def on_submit(self, it: discord.Interaction):
        prod_name = self.prod_select.component.values[0]
        if prod_name == "none": return
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE name = ?", (prod_name,))
        conn.commit(); conn.close()
        await it.response.send_message(f"✅ 제품 **[{prod_name}]**이(가) 성공적으로 삭제되었습니다.", ephemeral=True)
