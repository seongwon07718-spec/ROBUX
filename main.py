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
    def __init__(self, category, prod_name):
        super().__init__(title=f"제품 수정: {prod_name}")
        self.category = category
        self.old_name = prod_name
        
        self.name_input = ui.TextInput(label="제품 이름", default=prod_name)
        self.price_input = ui.TextInput(label="가격", placeholder="숫자만 입력")
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT price FROM products WHERE name = ?", (prod_name,))
        res = cur.fetchone(); conn.close()
        if res: self.price_input.placeholder = f"현재 가격: {res[0]}원"

        self.add_item(self.name_input)
        self.add_item(self.price_input)

    async def on_submit(self, it: discord.Interaction):
        new_price = self.price_input.value
        if new_price and not new_price.isdigit():
            return await it.response.send_message("**가격은 숫자만 입력 가능합니다**", ephemeral=True)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        if new_price:
            cur.execute("UPDATE products SET name = ?, price = ? WHERE name = ?", (self.name_input.value, int(new_price), self.old_name))
        else:
            cur.execute("UPDATE products SET name = ? WHERE name = ?", (self.name_input.value, self.old_name))
        conn.commit(); conn.close()
        await it.response.send_message(f"**__{self.old_name}__ 제품 정보가 수정되었습니다**", ephemeral=True)

class CategorySelectView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=60)
        self.container = ui.Container(ui.TextDisplay("## 카테고리 선택"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("카테고리를 선택해주세요"))
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
        title = "제품 삭제" if purpose == "delete" else "상품 설정"
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
            self.con = ui.Container(ui.TextDisplay("## 재고 수정"), accent_color=0xffffff)
            self.con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            self.con.add_item(ui.TextDisplay("카테고리를 선택해주세요"))
            self.con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            self.add_category_select()
        else:
            self.con = ui.Container(ui.TextDisplay(f"## 제품 선택"), accent_color=0xffffff)
            self.con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            self.con.add_item(ui.TextDisplay("제품를 선택해주세요"))
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
        
        cur.execute("SELECT stock FROM products WHERE name = ?", (self.name,))
        old_res = cur.fetchone()
        old_count = old_res[0] if old_res else 0

        cur.execute("UPDATE products SET stock_data = ?, stock = ? WHERE name = ?", 
                    (updated_data, new_count, self.name))
        conn.commit()
        conn.close()
        
        if new_count > old_count:
            await self.send_stock_webhook_container(self.name, new_count, new_count - old_count)

        await it.response.send_message(f"**__{self.name}__ 재고 수정 완료되었습니다 (현재: __{new_count}__개)**", ephemeral=True)

    async def send_stock_webhook_container(self, name, total_count, added_count):
        
        stock_url = WEBHOOK_CONFIG.get("재고")

        stock_con = ui.Container(ui.TextDisplay("## 제품 입고 알림"), accent_color=0xffffff)
        stock_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        stock_con.add_item(ui.TextDisplay(
            f"<:dot_white:1482000567562928271> 제품명: {name}\n"
            f"<:dot_white:1482000567562928271> 입고 수량: {added_count}개\n"
            f"<:dot_white:1482000567562928271> 현재 총 재고: {total_count}개"
        ))
        
        stock_v = ui.LayoutView().add_item(stock_con)
        
        try:
            webhook = discord.Webhook.from_url(stock_url, session=aiohttp.ClientSession())
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(stock_url, session=session)
                await webhook.send(view=stock_v)
        except Exception as e:
            print(f"웹훅 컨테이너 전송 실패: {e}")

class CategoryEditModal(ui.Modal, title="카테고리 이름 수정"):
    def __init__(self, old_name):
        super().__init__()
        self.old_name = old_name
        self.new_name = ui.TextInput(label="새 카테고리 이름", default=old_name, placeholder="변경할 이름을 입력하세요")
        self.add_item(self.new_name)

    async def on_submit(self, it: discord.Interaction):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("UPDATE products SET category = ? WHERE category = ?", (self.new_name.value, self.old_name))
        conn.commit(); conn.close()
        await it.response.send_message(f"**카테고리명이 __{self.old_name}__에서 __{self.new_name.value}__(으)로 변경되었습니다.**", ephemeral=True)

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

class AddCategoryModal(ui.Modal, title="신규 카테고리 추가"):
    cat_name = ui.TextInput(label="카테고리 이름", placeholder="생성할 카테고리 이름을 적어주세요")

    async def on_submit(self, it: discord.Interaction):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        
        cur.execute("SELECT DISTINCT category FROM products WHERE category = ?", (self.cat_name.value,))
        if cur.fetchone():
            conn.close()
            return await it.response.send_message(f"**이미 존재하는 카테고리입니다: {self.cat_name.value}**", ephemeral=True)
        
        conn.commit(); conn.close()
        await it.response.send_message(f"**카테고리 __{self.cat_name.value}__ 등록이 완료되었습니다**", ephemeral=True)

class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## 상품 관리하기"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("상품 관리를 원하시면 드롭바를 눌러 이용해주세요"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        self.admin_select = ui.Select(
            placeholder="관리 항목을 선택해주세요",
            options=[
                discord.SelectOption(label="제품 추가", value="add_prod", description="카테고리를 선택하여 제품을 추가합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="제품 삭제", value="del_prod", description="카테고리를 선택하여 제품을 삭제합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="제품 수정", value="edit_prod", description="제품의 이름과 가격을 수정합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="재고 수정", value="stock_edit", description="제품의 재고 데이터를 수정합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="카테고리 추가", value="add_cat", description="카테고리를 추가합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="카테고리 삭제", value="del_cat", description="카테고리와 제품을 전체 삭제합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="카테고리 수정", value="edit_cat", description="카테고리 이름을 수정합니다", emoji="<:dot_white:1482000567562928271>"),
            ]
        )
        self.admin_select.callback = self.admin_callback
        self.container.add_item(ui.ActionRow(self.admin_select))
        self.add_item(self.container)

    async def admin_callback(self, it: discord.Interaction):
        val = self.admin_select.values[0]
        
        if val == "add_cat":
            await it.response.send_modal(AddCategoryModal())
            
        elif val == "add_prod":
            await it.response.send_message(view=AdminCategorySelectView(purpose="add"), ephemeral=True)
            
        elif val == "edit_cat":
            await it.response.send_message(view=AdminCategorySelectView(purpose="edit_cat"), ephemeral=True)
            
        elif val == "edit_prod":
            await it.response.send_message(view=AdminCategorySelectView(purpose="edit_prod"), ephemeral=True)
            
        elif val == "del_prod":
            await it.response.send_message(view=AdminCategorySelectView(purpose="delete_prod"), ephemeral=True)
            
        elif val == "del_cat":
            await it.response.send_modal(CategoryDeleteModal())
            
        elif val == "stock_edit":
            await it.response.send_message(view=StockCategorySelectView(), ephemeral=True)

class AdminCategorySelectView(ui.LayoutView):
    def __init__(self, purpose):
        super().__init__(timeout=60)
        self.purpose = purpose
        titles = {
            "add": "제품 추가",
            "edit_cat": "카테고리 수정",
            "edit_prod": "제품 수정",
            "delete_prod": "제품 삭제"
        }
        self.container = ui.Container(ui.TextDisplay(f"## {titles.get(purpose)}"), accent_color=0xffffff)
        self.cat_select = CategorySelect()
        self.cat_select.callback = self.category_callback
        self.container.add_item(ui.ActionRow(self.cat_select))
        self.add_item(self.container)

    async def category_callback(self, it: discord.Interaction):
        selected_cat = self.cat_select.values[0]
        if selected_cat == "none": return

        if self.purpose == "add":
            await it.response.send_modal(AddProductModal(selected_cat))
        elif self.purpose == "edit_cat":
            await it.response.send_modal(CategoryEditModal(selected_cat))
        elif self.purpose == "edit_prod":
            new_con = ui.Container(ui.TextDisplay(f"## [{selected_cat}] 수정할 제품 선택"), accent_color=0xffffff)
            new_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            prod_sel = ProductSelect(selected_cat)
            async def ps_callback(it2: discord.Interaction):
                await it2.response.send_modal(ProductEditModal(selected_cat, prod_sel.values[0]))
            prod_sel.callback = ps_callback
            new_con.add_item(ui.ActionRow(prod_sel))
            await it.response.edit_message(view=ui.LayoutView().add_item(new_con))
        elif self.purpose == "delete_prod":
            new_con = ui.Container(ui.TextDisplay(f"## [{selected_cat}] 삭제할 제품 선택"), accent_color=0xffffff)
            new_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            prod_sel = ProductSelect(selected_cat)
            prod_sel.callback = lambda i: it.response.send_modal(ProductDeleteModal(selected_cat))
            new_con.add_item(ui.ActionRow(prod_sel))
            await it.response.edit_message(view=ui.LayoutView().add_item(new_con))
