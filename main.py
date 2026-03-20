import sqlite3
import discord
import time
import aiohttp
# 필요한 ui, WEBHOOK_CONFIG 등은 기존 main.py 설정을 따름

# --- [1] 기본 선택 컴포넌트 ---
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

# --- [2] 모든 모달 클래스 (수정/삭제/추가) ---
class ProductEditModal(ui.Modal):
    def __init__(self, category, prod_name):
        super().__init__(title=f"제품 수정: {prod_name}")
        self.category = category; self.old_name = prod_name
        self.name_input = ui.TextInput(label="제품 이름", default=prod_name)
        self.price_input = ui.TextInput(label="가격", placeholder="숫자만 입력")
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT price FROM products WHERE name = ?", (prod_name,))
        res = cur.fetchone(); conn.close()
        if res: self.price_input.placeholder = f"현재 가격: {res[0]}원"
        self.add_item(self.name_input); self.add_item(self.price_input)

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
        await it.response.send_message(f"**__{self.old_name}__ 정보 수정 완료**", ephemeral=True)

class NewProductModal(ui.Modal, title="신규 상품 등록"):
    cat = ui.TextInput(label="카테고리"); name = ui.TextInput(label="제품명"); price = ui.TextInput(label="가격")
    async def on_submit(self, it: discord.Interaction):
        if not self.price.value.isdigit(): return await it.response.send_message("**숫자만 입력 가능**", ephemeral=True)
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("INSERT INTO products (category, name, price, stock) VALUES (?, ?, ?, ?)", (self.cat.value, self.name.value, int(self.price.value), 0))
        conn.commit(); conn.close()
        await it.response.send_message(f"**{self.name.value} 등록 완료**", ephemeral=True)

class CategoryDeleteModal(ui.Modal, title="카테고리 삭제"):
    def __init__(self):
        super().__init__()
        self.cat_select_comp = CategorySelect()
        self.add_item(ui.Label(text="삭제할 카테고리를 선택하세요", component=self.cat_select_comp))
    async def on_submit(self, it: discord.Interaction):
        cat_name = self.cat_select_comp.values[0]
        if cat_name == "none": return
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE category = ?", (cat_name,))
        conn.commit(); conn.close()
        await it.response.send_message(f"**카테고리 [{cat_name}] 삭제 완료**", ephemeral=True)

class ProductDeleteModal(ui.Modal):
    def __init__(self, category):
        super().__init__(title=f"[{category}] 제품 삭제")
        self.p_select = ProductSelect(category)
        self.add_item(ui.Label(text="삭제할 제품 선택", component=self.p_select))
    async def on_submit(self, it: discord.Interaction):
        prod_name = self.p_select.values[0]
        if prod_name == "none": return
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE name = ?", (prod_name,))
        conn.commit(); conn.close()
        await it.response.send_message(f"**제품 [{prod_name}] 삭제 완료**", ephemeral=True)

class StockDataListModal(ui.Modal):
    def __init__(self, name, current_data):
        super().__init__(title=f"{name} 재고 관리"); self.name = name
        self.data_input = ui.TextInput(label="재고 리스트", style=discord.TextStyle.paragraph, default=str(current_data), required=False)
        self.add_item(self.data_input)
    async def on_submit(self, it: discord.Interaction):
        updated = self.data_input.value
        new_count = len([l for l in updated.split('\n') if l.strip()])
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT stock FROM products WHERE name = ?", (self.name,))
        old_count = cur.fetchone()[0] if cur.fetchone() else 0
        cur.execute("UPDATE products SET stock_data = ?, stock = ? WHERE name = ?", (updated, new_count, self.name))
        conn.commit(); conn.close()
        if new_count > old_count: await self.send_stock_webhook_container(self.name, new_count, new_count - old_count)
        await it.response.send_message(f"**재고 수정 완료 (현재: {new_count}개)**", ephemeral=True)
    async def send_stock_webhook_container(self, name, total, added):
        url = WEBHOOK_CONFIG.get("재고")
        con = ui.Container(ui.TextDisplay("## 제품 입고 알림"), accent_color=0xffffff)
        con.add_item(ui.TextDisplay(f"제품: {name}\n입고: {added}개\n총 재고: {total}개"))
        try:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(url, session=session)
                await webhook.send(view=ui.LayoutView().add_item(con))
        except: pass

class CategoryEditModal(ui.Modal, title="카테고리 이름 수정"):
    def __init__(self, old_name):
        super().__init__(); self.old_name = old_name
        self.new_name = ui.TextInput(label="새 이름", default=old_name)
        self.add_item(self.new_name)
    async def on_submit(self, it: discord.Interaction):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("UPDATE products SET category = ? WHERE category = ?", (self.new_name.value, self.old_name))
        conn.commit(); conn.close()
        await it.response.send_message(f"**카테고리명 변경 완료**", ephemeral=True)

class AddProductModal(ui.Modal):
    def __init__(self, category):
        super().__init__(title=f"[{category}] 제품 추가"); self.category = category
        self.name = ui.TextInput(label="제품명"); self.price = ui.TextInput(label="가격")
        self.add_item(self.name); self.add_item(self.price)
    async def on_submit(self, it: discord.Interaction):
        if not self.price.value.isdigit(): return await it.response.send_message("**숫자만 입력**", ephemeral=True)
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("INSERT INTO products (category, name, price, stock, sold_count) VALUES (?, ?, ?, 0, 0)", (self.category, self.name.value, int(self.price.value)))
        conn.commit(); conn.close()
        await it.response.send_message(f"**등록 완료**", ephemeral=True)

class AddCategoryModal(ui.Modal, title="신규 카테고리 추가"):
    cat_name = ui.TextInput(label="카테고리 이름")
    async def on_submit(self, it: discord.Interaction):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT category FROM products WHERE category = ?", (self.cat_name.value,))
        if cur.fetchone(): conn.close(); return await it.response.send_message("**이미 존재함**", ephemeral=True)
        conn.commit(); conn.close()
        await it.response.send_message(f"**카테고리 등록 완료**", ephemeral=True)

# --- [3] 관리자 뷰 레이아웃 ---
class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## 상품 관리하기"), accent_color=0xffffff)
        self.admin_select = ui.Select(
            placeholder="관리 항목 선택",
            options=[
                discord.SelectOption(label="제품 추가", value="add_prod", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="제품 삭제", value="del_prod", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="제품 수정", value="edit_prod", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="재고 수정", value="stock_edit", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="카테고리 추가", value="add_cat", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="카테고리 삭제", value="del_cat", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="카테고리 수정", value="edit_cat", emoji="<:dot_white:1482000567562928271>"),
            ]
        )
        self.admin_select.callback = self.admin_callback
        self.container.add_item(ui.ActionRow(self.admin_select)); self.add_item(self.container)

    async def admin_callback(self, it: discord.Interaction):
        val = self.admin_select.values[0]
        if val == "add_cat": await it.response.send_modal(AddCategoryModal())
        elif val == "del_cat": await it.response.send_modal(CategoryDeleteModal())
        elif val == "stock_edit": await it.response.send_message(view=StockCategorySelectView(), ephemeral=True)
        else: await it.response.send_message(view=AdminCategorySelectView(purpose=val), ephemeral=True)

class AdminCategorySelectView(ui.LayoutView):
    def __init__(self, purpose):
        super().__init__(timeout=60); self.purpose = purpose
        title = {"add":"제품 추가","edit_cat":"카테고리 수정","edit_prod":"제품 수정","delete_prod":"제품 삭제"}.get(purpose, "카테고리 선택")
        self.container = ui.Container(ui.TextDisplay(f"## {title}"), accent_color=0xffffff)
        self.cat_select = CategorySelect(); self.cat_select.callback = self.category_callback
        self.container.add_item(ui.ActionRow(self.cat_select)); self.add_item(self.container)

    async def category_callback(self, it: discord.Interaction):
        selected = self.cat_select.values[0]
        if selected == "none": return
        if self.purpose == "add": await it.response.send_modal(AddProductModal(selected))
        elif self.purpose == "edit_cat": await it.response.send_modal(CategoryEditModal(selected))
        elif self.purpose == "edit_prod":
            new_con = ui.Container(ui.TextDisplay(f"## [{selected}] 수정 제품 선택"), accent_color=0xffffff)
            p_sel = ProductSelect(selected)
            p_sel.callback = lambda i: it.response.send_modal(ProductEditModal(selected, p_sel.values[0]))
            new_con.add_item(ui.ActionRow(p_sel))
            await it.response.edit_message(view=ui.LayoutView().add_item(new_con))
        elif self.purpose == "delete_prod":
            new_con = ui.Container(ui.TextDisplay(f"## [{selected}] 삭제 제품 선택"), accent_color=0xffffff)
            p_sel = ProductSelect(selected)
            p_sel.callback = lambda i: it.response.send_modal(ProductDeleteModal(selected))
            new_con.add_item(ui.ActionRow(p_sel))
            await it.response.edit_message(view=ui.LayoutView().add_item(new_con))

class StockCategorySelectView(ui.LayoutView):
    def __init__(self, category=None):
        super().__init__(timeout=60); self.category = category
        self.con = ui.Container(ui.TextDisplay("## 재고 수정" if not category else f"## {category} 제품 선택"), accent_color=0xffffff)
        if not category:
            sel = CategorySelect(); sel.callback = self.category_callback
        else:
            sel = ProductSelect(category); sel.callback = self.product_callback
        self.con.add_item(ui.ActionRow(sel)); self.add_item(self.con)

    async def category_callback(self, it: discord.Interaction):
        await it.response.edit_message(view=StockCategorySelectView(category=it.data['values'][0]))

    async def product_callback(self, it: discord.Interaction):
        name = it.data['values'][0]
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT stock_data FROM products WHERE name = ?", (name,))
        res = cur.fetchone(); conn.close()
        await it.response.send_modal(StockDataListModal(name, res[0] if res else ""))
