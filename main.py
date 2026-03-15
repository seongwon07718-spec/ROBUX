# --- 카테고리 이름 수정을 위한 모달 ---
class CategoryEditModal(ui.Modal, title="카테고리 이름 수정"):
    def __init__(self, old_name):
        super().__init__()
        self.old_name = old_name
        self.new_name = ui.TextInput(label="새 카테고리 이름", default=old_name, placeholder="변경할 이름을 입력하세요")
        self.add_item(self.new_name)

    async def on_submit(self, it: discord.Interaction):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        # 해당 카테고리를 사용하는 모든 제품의 카테고리명 일괄 변경
        cur.execute("UPDATE products SET category = ? WHERE category = ?", (self.new_name.value, self.old_name))
        conn.commit(); conn.close()
        await it.response.send_message(f"**카테고리명이 __{self.old_name}__에서 __{self.new_name.value}__(으)로 변경되었습니다.**", ephemeral=True)

# --- 제품 이름/가격/재고 수정을 위한 모달 ---
class ProductEditModal(ui.Modal):
    def __init__(self, category, prod_name):
        super().__init__(title=f"제품 수정: {prod_name}")
        self.category = category
        self.old_name = prod_name
        
        self.name_input = ui.TextInput(label="제품 이름", default=prod_name)
        self.price_input = ui.TextInput(label="가격", placeholder="숫자만 입력")
        
        # 기존 가격 불러오기 (플레이스홀더용)
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT price FROM products WHERE name = ?", (prod_name,))
        res = cur.fetchone(); conn.close()
        if res: self.price_input.placeholder = f"현재 가격: {res[0]}원"

        self.add_item(self.name_input)
        self.add_item(self.price_input)

    async def on_submit(self, it: discord.Interaction):
        new_price = self.price_input.value
        if new_price and not new_price.isdigit():
            return await it.response.send_message("**가격은 숫자만 입력 가능합니다.**", ephemeral=True)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        if new_price:
            cur.execute("UPDATE products SET name = ?, price = ? WHERE name = ?", (self.name_input.value, int(new_price), self.old_name))
        else:
            cur.execute("UPDATE products SET name = ? WHERE name = ?", (self.name_input.value, self.old_name))
        conn.commit(); conn.close()
        await it.response.send_message(f"**__{self.old_name}__ 제품 정보가 수정되었습니다.**", ephemeral=True)

# --- 카테고리 선택 후 제품 추가를 위한 모달 ---
class AddProductModal(ui.Modal):
    def __init__(self, category):
        super().__init__(title=f"[{category}] 제품 추가")
        self.category = category
        self.name = ui.TextInput(label="제품명", placeholder="추가할 제품 이름을 적어주세요")
        self.price = ui.TextInput(label="가격", placeholder="숫자만 입력해주세요")
        self.add_item(self.name); self.add_item(self.price)

    async def on_submit(self, it: discord.Interaction):
        if not self.price.value.isdigit():
            return await it.response.send_message("**가격은 숫자만 입력해 주세요**", ephemeral=True)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("INSERT INTO products (category, name, price, stock, sold_count) VALUES (?, ?, ?, ?, ?)",
                    (self.category, self.name.value, int(self.price.value), 0, 0))
        conn.commit(); conn.close()
        await it.response.send_message(f"**[{self.category}]**에 **__{self.name.value}__** 등록 완료되었습니다.", ephemeral=True)
