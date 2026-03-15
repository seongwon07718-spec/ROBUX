# --- [ 카테고리/제품 선택용 드롭다운 클래스 ] ---
class CategorySelect(ui.Select):
    def __init__(self):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products")
        cats = cur.fetchall(); conn.close()
        options = [discord.SelectOption(label=c[0], value=c[0]) for c in cats] if cats else [discord.SelectOption(label="데이터 없음", value="none")]
        super().__init__(placeholder="카테고리를 먼저 선택하세요", options=options)

class ProductSelect(ui.Select):
    def __init__(self, category=None):
        options = [discord.SelectOption(label="카테고리를 선택해주세요", value="none")]
        if category:
            conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
            cur.execute("SELECT name FROM products WHERE category = ?", (category,))
            prods = cur.fetchall(); conn.close()
            options = [discord.SelectOption(label=p[0], value=p[0]) for p in prods] if prods else options
        super().__init__(placeholder="제품을 선택하세요", options=options)

# --- [ 상품 설정 모달 본체 ] ---
class ProductEditModal(ui.Modal, title="⚙️ 상품 설정 및 입고"):
    # 1. 카테고리 선택 (드롭바)
    cat_dropdown = ui.Label(text="카테고리 선택", component=CategorySelect())
    
    # 2. 제품 선택 (드롭바)
    prod_dropdown = ui.Label(text="제품 선택", component=ProductSelect())
    
    # 3. 가격
    price = ui.TextInput(label="가격 (변경 시 입력)", placeholder="가격을 수정하려면 입력하세요", required=False)
    
    # 4. 재고 (줄바꿈 입고)
    stock_data = ui.TextInput(
        label="재고 입고 (줄바꿈당 1개)",
        style=discord.TextStyle.paragraph,
        placeholder="내용을 입력하세요. 줄 수만큼 재고가 늘어납니다.",
        required=False
    )

    async def on_submit(self, it: discord.Interaction):
        cat = self.cat_dropdown.component.values[0]
        name = self.prod_dropdown.component.values[0]
        
        if name == "none":
            return await it.response.send_message("❌ 관리할 제품을 선택해주세요.", ephemeral=True)

        lines = self.stock_data.value.split('\n')
        add_count = len([l for l in lines if l.strip()])

        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        if self.price.value:
            cur.execute("UPDATE products SET price = ? WHERE name = ?", (int(self.price.value), name))
        if add_count > 0:
            cur.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (add_count, name))
        conn.commit(); conn.close()

        await it.response.send_message(f"✅ **{name}** 설정이 변경되었습니다.", ephemeral=True)
