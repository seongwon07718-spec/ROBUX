class ProductModal(ui.Modal, title="카테고리 / 제품 설정"):
    cat = ui.TextInput(label="카테고리")
    name = ui.TextInput(label="제품명")
    price = ui.TextInput(label="가격")

    async def on_submit(self, it: discord.Interaction):
        if not self.price.value.isdigit():
            return await it.response.send_message("가격은 숫자만 입력해주세요", ephemeral=True)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO products (category, name, price, stock) VALUES (?, ?, ?, COALESCE((SELECT stock FROM products WHERE name = ?), 0))", 
                    (self.cat.value, self.name.value, int(self.price.value), self.name.value))
        conn.commit(); conn.close()
        await it.response.send_message("✅ 설정 완료", ephemeral=True)

class StockModal(ui.Modal, title="재고 수량 관리"):
    name = ui.TextInput(label="제품명")
    count = ui.TextInput(label="변경할 재고 수량")

    async def on_submit(self, it: discord.Interaction):
        if not self.count.value.isdigit():
            return await it.response.send_message("재고 수량은 숫자만 입력해주세요", ephemeral=True)

        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("UPDATE products SET stock = ? WHERE name = ?", (int(self.count.value), self.name.value))
        if cur.rowcount == 0:
            conn.close()
            return await it.response.send_message("해당 이름의 제품을 찾을 수 없습니다", ephemeral=True)
        conn.commit(); conn.close()
        await it.response.send_message("✅ 재고 수정 완료", ephemeral=True)
