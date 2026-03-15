class CategorySelectView(ui.LayoutView):
    def __init__(self, purpose="edit"):
        super().__init__(timeout=60)
        self.purpose = purpose
        title = "🗑️ 제품 삭제 - 카테고리 선택" if purpose == "delete" else "📁 상품 설정 - 카테고리 선택"
        self.container = ui.Container(ui.TextDisplay(f"## {title}"), accent_color=0x000000)
        
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
