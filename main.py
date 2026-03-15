# --- [ 1. 카테고리 선택 모달 ] ---
class CategorySelectModal(ui.Modal, title="⚙️ 상품 설정 - 카테고리 선택"):
    # 카테고리 목록을 드롭바(Select)로 표시
    cat_dropdown = ui.Label(text="먼저 카테고리를 선택하세요", component=CategorySelect())

    async def on_submit(self, it: discord.Interaction):
        selected_cat = self.cat_dropdown.component.values[0]
        if selected_cat == "none":
            return await it.response.send_message("❌ 선택 가능한 카테고리가 없습니다.", ephemeral=True)
        
        # [핵심] 카테고리를 선택하면 해당 카테고리의 제품들만 담긴 다음 모달을 띄움
        await it.response.send_modal(ProductEditModal(selected_cat))

# --- [ 2. 제품 설정 및 재고 입고 모달 ] ---
class ProductEditModal(ui.Modal):
    def __init__(self, category):
        super().__init__(title=f"⚙️ [{category}] 제품 설정")
        self.category = category
        
        # 선택된 카테고리에 해당하는 제품들만 드롭바에 추가
        self.prod_dropdown = ui.Label(
            text=f"{category} 카테고리의 제품 선택",
            component=ProductSelect(category=category) # 필터링된 제품 목록
        )
        self.add_item(self.prod_dropdown)
        
        # 가격 및 재고 입력칸 추가
        self.price = ui.TextInput(label="가격 (변경 시 입력)", placeholder="수정할 가격", required=False)
        self.stock_data = ui.TextInput(
            label="재고 입고 (줄바꿈당 1개)",
            style=discord.TextStyle.paragraph,
            placeholder="내용을 입력하세요. 줄 수만큼 재고가 늘어납니다.",
            required=False
        )
        self.add_item(self.price)
        self.add_item(self.stock_data)

    async def on_submit(self, it: discord.Interaction):
        name = self.prod_dropdown.component.values[0]
        if name == "none":
            return await it.response.send_message("❌ 제품을 선택해주세요.", ephemeral=True)

        # 줄바꿈 재고 계산
        lines = self.stock_data.value.split('\n')
        add_count = len([l for l in lines if l.strip()])

        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        
        # 가격 변경이 있을 경우만 업데이트
        if self.price.value:
            cur.execute("UPDATE products SET price = ? WHERE name = ?", (int(self.price.value), name))
        
        # 재고 입고가 있을 경우만 업데이트
        if add_count > 0:
            cur.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (add_count, name))
        
        conn.commit(); conn.close()
        await it.response.send_message(f"✅ **{name}** 제품의 설정 및 입고가 완료되었습니다!", ephemeral=True)

# --- [ 3. 관리자 레이아웃 버튼 연결 ] ---
class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## 🛠️ 관리자 메뉴"), accent_color=0x000000)
        
        new_btn = ui.Button(label="신규상품", style=discord.ButtonStyle.success, emoji="✨")
        edit_btn = ui.Button(label="상품설정", style=discord.ButtonStyle.primary, emoji="⚙️")
        
        new_btn.callback = self.new_callback
        edit_btn.callback = self.edit_callback # 여기에 연결
        
        self.container.add_item(ui.ActionRow(new_btn, edit_btn))
        self.add_item(self.container)

    async def new_callback(self, it: discord.Interaction):
        await it.response.send_modal(NewProductModal())

    async def edit_callback(self, it: discord.Interaction):
        # 상품설정 버튼을 누르면 먼저 카테고리 선택 모달이 뜹니다.
        await it.response.send_modal(CategorySelectModal())
