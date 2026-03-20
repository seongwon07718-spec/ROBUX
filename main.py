import sqlite3
import discord
import aiohttp
from discord import ui

# --- [1] 기본 컴포넌트 (드롭다운) ---
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

# --- [2] 모달 관리 (추가/수정/삭제) ---
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
        await it.response.send_message(f"**카테고리 __[{cat_name}]__ 및 모든 제품이 삭제되었습니다**", ephemeral=True)

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
        await it.response.send_message(f"**[{self.category}]**에 **__{self.name.value}__** 등록 완료.", ephemeral=True)

class ProductEditModal(ui.Modal):
    def __init__(self, category, prod_name):
        super().__init__(title=f"제품 수정: {prod_name}")
        self.category, self.old_name = category, prod_name
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
        await it.response.send_message(f"**__{self.old_name}__ 제품 정보가 수정되었습니다**", ephemeral=True)

class ProductDeleteModal(ui.Modal):
    def __init__(self, category):
        super().__init__(title=f"[{category}] 제품 삭제")
        self.p_select = ProductSelect(category)
        self.add_item(ui.Label(text=f"삭제할 {category} 제품을 선택하세요", component=self.p_select))
    async def on_submit(self, it: discord.Interaction):
        prod_name = self.p_select.values[0]
        if prod_name == "none": return
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE name = ?", (prod_name,))
        conn.commit(); conn.close()
        await it.response.send_message(f"**제품 __[{prod_name}]__이(가) 삭제되었습니다**", ephemeral=True)

# --- [3] 재고 관리 모달 및 웹훅 ---
class StockDataListModal(ui.Modal):
    def __init__(self, name, current_data):
        super().__init__(title=f"{name} 재고 관리")
        self.name = name
        self.data_input = ui.TextInput(label="재고 리스트", style=discord.TextStyle.paragraph, default=str(current_data), required=False)
        self.add_item(self.data_input)
    async def on_submit(self, it: discord.Interaction):
        updated_data = self.data_input.value
        new_count = len([l for l in updated_data.split('\n') if l.strip()])
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT stock FROM products WHERE name = ?", (self.name,))
        old_res = cur.fetchone(); old_count = old_res[0] if old_res else 0
        cur.execute("UPDATE products SET stock_data = ?, stock = ? WHERE name = ?", (updated_data, new_count, self.name))
        conn.commit(); conn.close()
        if new_count > old_count:
            await self.send_stock_webhook_container(self.name, new_count, new_count - old_count)
        await it.response.send_message(f"**__{self.name}__ 재고 수정 완료 (현재: __{new_count}__개)**", ephemeral=True)

    async def send_stock_webhook_container(self, name, total_count, added_count):
        stock_url = WEBHOOK_CONFIG.get("재고")
        stock_con = ui.Container(ui.TextDisplay("## 제품 입고 알림"), accent_color=0xffffff)
        stock_con.add_item(ui.TextDisplay(f"제품명: {name}\n입고 수량: {added_count}개\n현재 총 재고: {total_count}개"))
        try:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(stock_url, session=session)
                await webhook.send(view=ui.LayoutView().add_item(stock_con))
        except Exception as e: print(f"웹훅 실패: {e}")

# --- [4] 통합 관리자 뷰 레이아웃 ---
class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## 상품 관리하기"), accent_color=0xffffff)
        self.admin_select = ui.Select(
            placeholder="관리 항목을 선택해주세요",
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
        self.container.add_item(ui.ActionRow(self.admin_select))
        self.add_item(self.container)

    async def admin_callback(self, it: discord.Interaction):
        val = self.admin_select.values[0]
        if val == "add_cat": await it.response.send_modal(AddCategoryModal())
        elif val == "del_cat": await it.response.send_modal(CategoryDeleteModal())
        elif val == "stock_edit": await it.response.send_message(view=StockCategorySelectView(), ephemeral=True)
        else: await it.response.send_message(view=AdminCategorySelectView(purpose=val), ephemeral=True)

class AdminCategorySelectView(ui.LayoutView):
    def __init__(self, purpose):
        super().__init__(timeout=60); self.purpose = purpose
        title = {"add_prod":"제품 추가", "edit_cat":"카테고리 수정", "edit_prod":"제품 수정", "del_prod":"제품 삭제"}.get(purpose)
        self.container = ui.Container(ui.TextDisplay(f"## {title}"), accent_color=0xffffff)
        self.cat_select = CategorySelect(); self.cat_select.callback = self.category_callback
        self.container.add_item(ui.ActionRow(self.cat_select)); self.add_item(self.container)

    async def category_callback(self, it: discord.Interaction):
        selected = self.cat_select.values[0]
        if selected == "none": return
        if self.purpose == "add_prod": await it.response.send_modal(AddProductModal(selected))
        elif self.purpose == "edit_cat": await it.response.send_modal(CategoryEditModal(selected))
        elif self.purpose == "edit_prod":
            new_con = ui.Container(ui.TextDisplay(f"## [{selected}] 수정할 제품 선택"), accent_color=0xffffff)
            p_sel = ProductSelect(selected)
            p_sel.callback = lambda i: it.response.send_modal(ProductEditModal(selected, p_sel.values[0]))
            new_con.add_item(ui.ActionRow(p_sel))
            await it.response.edit_message(view=ui.LayoutView().add_item(new_con))
        elif self.purpose == "del_prod":
            new_con = ui.Container(ui.TextDisplay(f"## [{selected}] 삭제할 제품 선택"), accent_color=0xffffff)
            p_sel = ProductSelect(selected)
            p_sel.callback = lambda i: it.response.send_modal(ProductDeleteModal(selected))
            new_con.add_item(ui.ActionRow(p_sel))
            await it.response.edit_message(view=ui.LayoutView().add_item(new_con))

class StockCategorySelectView(ui.LayoutView):
    def __init__(self, category=None):
        super().__init__(timeout=60); self.category = category
        title = "재고 수정" if not category else f"## {category} 제품 선택"
        self.con = ui.Container(ui.TextDisplay(f"## {title}"), accent_color=0xffffff)
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
