class CategorySelect(ui.Select):
    def __init__(self):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products")
        cats = cur.fetchall(); conn.close()
        options = [discord.SelectOption(label=c[0], value=c[0]) for c in cats] if cats else [discord.SelectOption(label="카테고리 없음", value="none")]
        super().__init__(placeholder="카테고리를 선택하세요", options=options, min_values=1, max_values=1)

class ProductSelect(ui.Select):
    def __init__(self, category):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT name FROM products WHERE category = ?", (category,))
        prods = cur.fetchall(); conn.close()
        options = [discord.SelectOption(label=p[0], value=p[0]) for p in prods] if prods else [discord.SelectOption(label="제품 없음", value="none")]
        super().__init__(placeholder="제품을 선택하세요", options=options, min_values=1, max_values=1)

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

    async def on_submit(self, it: discord.Interaction):
        name = self.prod_dropdown.component.values[0]
        if name == "none":
            return await it.response.send_message("**관리할 제품이 없습니다**", ephemeral=True)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        if self.price_input.value and self.price_input.value.isdigit():
            cur.execute("UPDATE products SET price = ? WHERE name = ?", (int(self.price_input.value), name))
        
        conn.commit(); conn.close()
        await it.response.send_message(f"**__{name}__ 설정 완료되었습니다**", ephemeral=True)

class CategorySelectView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=60)
        self.container = ui.Container(ui.TextDisplay("## 카테고리 선택"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("설정할 카테고리를 선택해주세요"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        self.cat_select = CategorySelect()
        self.cat_select.callback = self.category_callback
        
        self.container.add_item(ui.ActionRow(self.cat_select))
        self.add_item(self.container)

    async def category_callback(self, it: discord.Interaction):
        selected_cat = self.cat_select.values[0]
        if selected_cat == "none":
            return await it.response.send_message("**선택 가능한 카테고리가 없습니다**", ephemeral=True)
        
        await it.response.send_modal(ProductEditModal(selected_cat))

class NewProductModal(ui.Modal, title="신규 상품 등록"):
    cat = ui.TextInput(label="카테고리", placeholder="카테고리를 적어주세요")
    name = ui.TextInput(label="제품명", placeholder="등록할 제품 이름을 적어주세요")
    price = ui.TextInput(label="가격", placeholder="숫자만 입력해주세요")

    async def on_submit(self, it: discord.Interaction):
        if not self.price.value.isdigit():
            return await it.response.send_message("**가격은 숫자만 입력해 주세요**", ephemeral=True)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("INSERT INTO products (category, name, price, stock) VALUES (?, ?, ?, ?)",
                    (self.cat.value, self.name.value, int(self.price.value), 0))
        conn.commit(); conn.close()
        await it.response.send_message(f"**__{self.name.value}__ 등록 완료되었습니다**", ephemeral=True)

class CategoryDeleteModal(ui.Modal, title="카테고리 삭제"):
    def __init__(self):
        super().__init__()
        self.cat_select = ui.Label(
            text="삭제할 카테고리를 선택하세요",
            component=CategorySelect()
        )
        self.add_item(self.cat_select)

    async def on_submit(self, it: discord.Interaction):
        cat_name = self.cat_select.component.values[0]
        if cat_name == "none": return
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE category = ?", (cat_name,))
        conn.commit(); conn.close()
        await it.response.send_message(f"**카테고리 __[{cat_name}]__ 및 포함된 모든 제품이 삭제되었습니다**", ephemeral=True)

class CategorySelectView(ui.LayoutView):
    def __init__(self, purpose="edit"):
        super().__init__(timeout=60)
        self.purpose = purpose
        title = "제품 삭제 - 카테고리 선택" if purpose == "delete" else "상품 설정 - 카테고리 선택"
        self.container = ui.Container(ui.TextDisplay(f"## {title}"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("카테고리를 선택해주세요"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        self.cat_select = CategorySelect()
        self.cat_select.callback = self.category_callback
        self.container.add_item(ui.ActionRow(self.cat_select))
        self.add_item(self.container)

    async def category_callback(self, it: discord.Interaction):
        selected_cat = self.cat_select.values[0]
        if selected_cat == "none": return
        
        if self.purpose == "delete":
            await it.response.send_modal(ProductDeleteModal(selected_cat))
        else:
            await it.response.send_modal(ProductEditModal(selected_cat))

class ProductDeleteModal(ui.Modal):
    def __init__(self, category):
        super().__init__(title=f"[{category}] 제품 삭제")
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
        await it.response.send_message(f"**제품 __[{prod_name}]__이(가) 성공적으로 삭제되었습니다**", ephemeral=True)

class StockCategorySelectView(ui.LayoutView):
    def __init__(self, category=None):
        super().__init__(timeout=60)
        self.category = category
        
        if not self.category:
            self.con = ui.Container(ui.TextDisplay("## 재고 수정 - 카테고리 선택"), accent_color=0xffffff)
            self.con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            self.con.add_item(ui.TextDisplay("수정할 제품 카테고리를 선택하세요"))
            self.con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            self.add_category_select()
        else:
            self.con = ui.Container(ui.TextDisplay(f"## [{self.category}] 제품 선택"), accent_color=0xffffff)
            self.con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            self.con.add_item(ui.TextDisplay("재고 데이터를 직접 수정할 제품을 선택하세요"))
            self.con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            self.add_product_select()

        self.add_item(self.con)

    def add_category_select(self):
        """카테고리 드롭다운 추가"""
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products")
        cats = cur.fetchall(); conn.close()
        
        options = [discord.SelectOption(label=c[0], value=c[0]) for c in cats] if cats else [discord.SelectOption(label="카테고리 없음", value="none")]
        select = ui.Select(placeholder="카테고리 선택하기", options=options)
        select.callback = self.category_callback
        self.con.add_item(ui.ActionRow(select))

    def add_product_select(self):
        """제품 드롭다운 추가"""
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT name FROM products WHERE category = ?", (self.category,))
        prods = cur.fetchall(); conn.close()
        
        options = [discord.SelectOption(label=p[0], value=p[0]) for p in prods] if prods else [discord.SelectOption(label="제품 없음", value="none")]
        select = ui.Select(placeholder="제품 선택하기", options=options)
        select.callback = self.product_callback
        self.con.add_item(ui.ActionRow(select))

    async def category_callback(self, it: discord.Interaction):
        selected = it.data['values'][0]
        if selected == "none": return
        
        new_view = StockCategorySelectView(category=selected)
        await it.response.edit_message(view=new_view)

    async def product_callback(self, it: discord.Interaction):
        prod_name = it.data['values'][0]
        if prod_name == "none": return
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT stock_data FROM products WHERE name = ?", (prod_name,))
        res = cur.fetchone(); conn.close()
        current_data = res[0] if res and res[0] else ""
        
        await it.response.send_modal(StockDataListModal(prod_name, current_data))

async def stock_edit_product_callback(self, it: discord.Interaction):
    prod_name = it.data['values'][0]
    if prod_name == "none": return
    
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()
    cur.execute("SELECT stock_data FROM products WHERE name = ?", (prod_name,))
    res = cur.fetchone()
    conn.close()
    
    current_stock_list = res[0] if res and res[0] else ""
    
    await it.response.send_modal(StockDataListModal(prod_name, current_stock_list))

class StockDataListModal(ui.Modal):
    def __init__(self, name, current_data):
        super().__init__(title=f"{name} 재고 관리")
        self.name = name
        
        self.data_input = ui.TextInput(
            label="재고 리스트",
            style=discord.TextStyle.paragraph,
            default=str(current_data),
            placeholder="재고가 비어있습니다", 
            required=False
        )
        self.add_item(self.data_input)

    async def on_submit(self, it: discord.Interaction):
        updated_data = self.data_input.value
        
        new_count = len([l for l in updated_data.split('\n') if l.strip()])

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        
        cur.execute("UPDATE products SET stock_data = ?, stock = ? WHERE name = ?", 
                    (updated_data, new_count, self.name))
        conn.commit()
        conn.close()
        
        await it.response.send_message(f"**__{self.name}__ 재고 수정 완료되었습니다 (현재: __{new_count}__개)**", ephemeral=True)

class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## 상품 관리하기"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("상품 관리를 원하시면 드롭바를 눌려 이용해주세요"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        self.admin_select = ui.Select(
            placeholder="관리 항목 선택해주세요",
            options=[
                discord.SelectOption(label="신규상품 등록", value="new", description="새로운 상품을 등록합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="가격 설정", value="edit", description="기존 상품의 가격을 수정합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="제품 삭제", value="del_prod", description="특정 제품을 삭제합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="카테고리 삭제", value="del_cat", description="카테고리와 그 안의 모든 제품을 삭제합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="재고 수정", value="stock_edit", description="제품의 재고 수정합니다", emoji="<:dot_white:1482000567562928271>")
            ]
        )
        self.admin_select.callback = self.admin_callback
        self.container.add_item(ui.ActionRow(self.admin_select))
        self.add_item(self.container)

    async def admin_callback(self, it: discord.Interaction):
        val = self.admin_select.values[0]
        if val == "new":
            await it.response.send_modal(NewProductModal())
        elif val == "edit":
            await it.response.send_message(view=CategorySelectView(purpose="edit"), ephemeral=True)
        elif val == "del_prod":
            await it.response.send_message(view=CategorySelectView(purpose="delete"), ephemeral=True)
        elif val == "del_cat":
            await it.response.send_modal(CategoryDeleteModal())
        elif val == "stock_edit":
            await it.response.send_message(view=StockCategorySelectView(), ephemeral=True)
