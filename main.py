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
                discord.SelectOption(label="제품 추가", value="add_prod", description="카테고리를 선택하여 제품을 추가합니다.", emoji="➕"),
                discord.SelectOption(label="카테고리 수정", value="edit_cat", description="카테고리 이름을 수정합니다.", emoji="📝"),
                discord.SelectOption(label="제품 수정", value="edit_prod", description="제품의 이름과 가격을 수정합니다.", emoji="🛠️"),
                discord.SelectOption(label="제품 삭제", value="del_prod", description="특정 제품을 삭제합니다.", emoji="🗑️"),
                discord.SelectOption(label="카테고리 삭제", value="del_cat", description="카테고리와 제품을 전체 삭제합니다.", emoji="❌"),
                discord.SelectOption(label="재고 수정", value="stock_edit", description="제품의 재고 데이터를 수정합니다.", emoji="📦")
            ]
        )
        self.admin_select.callback = self.admin_callback
        self.container.add_item(ui.ActionRow(self.admin_select))
        self.add_item(self.container)

    async def admin_callback(self, it: discord.Interaction):
        val = self.admin_select.values[0]
        
        # 제품 추가/수정/삭제 모두 '카테고리 선택 뷰'를 먼저 거치도록 설계
        if val == "add_prod":
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

# --- 관리자용 카테고리/제품 선택 통합 뷰 ---
class AdminCategorySelectView(ui.LayoutView):
    def __init__(self, purpose):
        super().__init__(timeout=60)
        self.purpose = purpose
        titles = {
            "add": "제품 추가 - 카테고리 선택",
            "edit_cat": "카테고리 수정 - 대상 선택",
            "edit_prod": "제품 수정 - 카테고리 선택",
            "delete_prod": "제품 삭제 - 카테고리 선택"
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
            # 제품 수정을 위해 제품 선택 드롭다운이 포함된 컨테이너로 교체
            new_con = ui.Container(ui.TextDisplay(f"## [{selected_cat}] 수정할 제품 선택"), accent_color=0xffffff)
            prod_sel = ProductSelect(selected_cat)
            async def ps_callback(it2: discord.Interaction):
                await it2.response.send_modal(ProductEditModal(selected_cat, prod_sel.values[0]))
            prod_sel.callback = ps_callback
            new_con.add_item(ui.ActionRow(prod_sel))
            await it.response.edit_message(view=ui.LayoutView().add_item(new_con))
        elif self.purpose == "delete_prod":
            new_con = ui.Container(ui.TextDisplay(f"## [{selected_cat}] 삭제할 제품 선택"), accent_color=0xffffff)
            prod_sel = ProductSelect(selected_cat)
            prod_sel.callback = lambda i: it.response.send_modal(ProductDeleteModal(selected_cat)) # 기존 로직 활용
            new_con.add_item(ui.ActionRow(prod_sel))
            await it.response.edit_message(view=ui.LayoutView().add_item(new_con))
