# --- [ 1. 드롭다운 컴포넌트 클래스 ] ---
class CategorySelect(ui.Select):
    def __init__(self):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products")
        cats = cur.fetchall(); conn.close()
        options = [discord.SelectOption(label=c[0], value=c[0]) for c in cats] if cats else [discord.SelectOption(label="카테고리 없음", value="none")]
        super().__init__(placeholder="카테고리를 선택하세요", options=options)

class ProductSelect(ui.Select):
    def __init__(self, category):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT name FROM products WHERE category = ?", (category,))
        prods = cur.fetchall(); conn.close()
        options = [discord.SelectOption(label=p[0], value=p[0]) for p in prods] if prods else [discord.SelectOption(label="제품 없음", value="none")]
        super().__init__(placeholder="제품을 선택하세요", options=options)

# --- [ 2. 상품 설정 2단계 모달 (제품 선택 및 입고) ] ---
class ProductEditModal(ui.Modal):
    def __init__(self, category):
        super().__init__(title=f"⚙️ [{category}] 제품 설정")
        self.category = category

        # 노란 줄 방지를 위해 순차적으로 add_item 실행
        self.prod_dropdown = ui.Label(
            text=f"[{category}] 카테고리의 제품을 선택하세요",
            component=ProductSelect(category=category)
        )
        self.add_item(self.prod_dropdown)

        self.price = ui.TextInput(
            label="가격 (변경 시 입력)", 
            placeholder="숫자만 입력", 
            required=False
        )
        self.add_item(self.price)

        self.stock_data = ui.TextInput(
            label="재고 입고 (줄바꿈당 1개)",
            style=discord.TextStyle.paragraph,
            placeholder="입력한 줄 수만큼 재고가 추가됩니다.",
            required=False
        )
        self.add_item(self.stock_data)

    async def on_submit(self, it: discord.Interaction):
        name = self.prod_dropdown.component.values[0]
        if name == "none":
            return await it.response.send_message("❌ 관리할 제품이 없습니다.", ephemeral=True)

        # 줄바꿈 재고 계산
        lines = self.stock_data.value.split('\n')
        add_count = len([l for l in lines if l.strip()])

        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        if self.price.value and self.price.value.isdigit():
            cur.execute("UPDATE products SET price = ? WHERE name = ?", (int(self.price.value), name))
        
        if add_count > 0:
            cur.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (add_count, name))
        conn.commit(); conn.close()

        await it.response.send_message(f"✅ **{name}** 설정 및 **{add_count}개** 입고 완료!", ephemeral=True)

# --- [ 3. 상품 설정 1단계 모달 (카테고리 선택) ] ---
class CategorySelectModal(ui.Modal, title="⚙️ 상품 설정 - 카테고리 선택"):
    def __init__(self):
        super().__init__()
        self.cat_label = ui.Label(
            text="수정할 제품이 포함된 카테고리를 선택하세요",
            component=CategorySelect()
        )
        self.add_item(self.cat_label)

    async def on_submit(self, it: discord.Interaction):
        selected_cat = self.cat_label.component.values[0]
        if selected_cat == "none":
            return await it.response.send_message("❌ 선택 가능한 카테고리가 없습니다.", ephemeral=True)
        
        # 다음 단계 모달 실행
        await it.response.send_modal(ProductEditModal(selected_cat))

# --- [ 4. 관리자 레이아웃 (버튼) ] ---
class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        # 컨테이너 구성
        self.container = ui.Container(ui.TextDisplay("## 🛠️ 관리자 도구"), accent_color=0x000000)
        
        btn_new = ui.Button(label="신규상품", style=discord.ButtonStyle.success, emoji="✨")
        btn_edit = ui.Button(label="상품설정", style=discord.ButtonStyle.primary, emoji="⚙️")
        
        btn_new.callback = self.new_callback
        btn_edit.callback = self.edit_callback
        
        self.container.add_item(ui.ActionRow(btn_new, btn_edit))
        self.add_item(self.container)

    async def new_callback(self, it: discord.Interaction):
        await it.response.send_modal(NewProductModal()) # 기존 NewProductModal 클래스 사용

    async def edit_callback(self, it: discord.Interaction):
        await it.response.send_modal(CategorySelectModal())
