import sqlite3
import discord
from discord import app_commands, ui

# --- [ 1. 드롭다운 컴포넌트 ] ---
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

# --- [ 2. 2단계: 제품 설정 모달 ] ---
class ProductEditModal(ui.Modal):
    def __init__(self, category):
        super().__init__(title=f"⚙️ [{category}] 제품 설정")
        self.category = category

        # UI 요소들을 하나씩 명시적으로 추가 (노란 줄 방지)
        self.prod_dropdown = ui.Label(
            text=f"수정할 {category} 제품을 고르세요",
            component=ProductSelect(category=category)
        )
        self.add_item(self.prod_dropdown)

        self.price_input = ui.TextInput(label="가격 (숫자만)", placeholder="변경할 가격 입력", required=False)
        self.add_item(self.price_input)

        self.stock_input = ui.TextInput(
            label="재고 입고 (줄바꿈당 1개)", 
            style=discord.TextStyle.paragraph, 
            placeholder="내용을 입력하세요. 줄 수만큼 재고가 추가됩니다.",
            required=False
        )
        self.add_item(self.stock_input)

    async def on_submit(self, it: discord.Interaction):
        name = self.prod_dropdown.component.values[0]
        if name == "none":
            return await it.response.send_message("❌ 제품이 없습니다.", ephemeral=True)

        lines = self.stock_input.value.split('\n')
        add_count = len([l for l in lines if l.strip()])

        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        if self.price_input.value and self.price_input.value.isdigit():
            cur.execute("UPDATE products SET price = ? WHERE name = ?", (int(self.price_input.value), name))
        
        if add_count > 0:
            cur.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (add_count, name))
        conn.commit(); conn.close()

        await it.response.send_message(f"✅ **{name}** 설정 완료 (입고: {add_count}개)", ephemeral=True)

# --- [ 3. 1단계: 카테고리 선택 모달 ] ---
class CategorySelectModal(ui.Modal, title="⚙️ 상품 설정 - 카테고리 선택"):
    def __init__(self):
        super().__init__()
        self.cat_label = ui.Label(
            text="수정할 제품의 카테고리를 선택하세요",
            component=CategorySelect()
        )
        self.add_item(self.cat_label)

    async def on_submit(self, it: discord.Interaction):
        selected_cat = self.cat_label.component.values[0]
        if selected_cat == "none":
            return await it.response.send_message("❌ 카테고리가 없습니다.", ephemeral=True)
        
        # 다음 모달로 넘길 때 데이터 타입을 명확히 전달
        await it.response.send_modal(ProductEditModal(str(selected_cat)))

# --- [ 4. 관리 레이아웃 및 명령어 ] ---
class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        # 400 에러 방지를 위해 Container 안의 텍스트로만 정보 전달
        self.container = ui.Container(ui.TextDisplay("## 🛠️ 자판기 관리 메뉴"), accent_color=0x000000)
        
        btn_new = ui.Button(label="신규상품", style=discord.ButtonStyle.success, emoji="✨")
        btn_edit = ui.Button(label="상품설정", style=discord.ButtonStyle.primary, emoji="⚙️")
        
        btn_new.callback = self.new_btn_callback
        btn_edit.callback = self.edit_btn_callback
        
        self.container.add_item(ui.ActionRow(btn_new, btn_edit))
        self.add_item(self.container)

    async def new_btn_callback(self, it: discord.Interaction):
        await it.response.send_modal(NewProductModal())

    async def edit_btn_callback(self, it: discord.Interaction):
        await it.response.send_modal(CategorySelectModal())

@bot.tree.command(name="상품설정", description="상품 관리 도구를 엽니다.")
async def product_admin(it: discord.Interaction):
    # [중요] content="" 로 비워두어야 V2 컴포넌트 에러가 안 납니다.
    await it.response.send_message(view=ProductAdminLayout(), ephemeral=True)
