class NewProductModal(ui.Modal, title="✨ 신규 상품 등록"):
    cat = ui.TextInput(label="신규 카테고리", placeholder="예: 게임, 이용권")
    name = ui.TextInput(label="신규 제품명", placeholder="등록할 제품 이름을 입력하세요")
    price = ui.TextInput(label="가격", placeholder="숫자만 입력하세요")

    async def on_submit(self, it: discord.Interaction):
        if not self.price.value.isdigit():
            return await it.response.send_message("❌ 가격은 숫자만 입력 가능합니다.", ephemeral=True)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("INSERT INTO products (category, name, price, stock) VALUES (?, ?, ?, ?)",
                    (self.cat.value, self.name.value, int(self.price.value), 0))
        conn.commit(); conn.close()
        
        await it.response.send_message(f"✅ **{self.name.value}** 제품이 등록되었습니다.", ephemeral=True)
