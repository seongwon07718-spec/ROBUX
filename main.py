class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## 🛠️ 상품 관리 시스템"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("수행할 작업을 아래 메뉴에서 선택하세요."))
        
        self.admin_select = ui.Select(
            placeholder="관리 항목 선택...",
            options=[
                discord.SelectOption(label="신규상품 등록", value="new", emoji="✨"),
                discord.SelectOption(label="상품 설정/입고", value="edit", emoji="⚙️"),
                discord.SelectOption(label="제품 삭제", value="del_prod", description="특정 제품을 삭제합니다.", emoji="🗑️"),
                discord.SelectOption(label="카테고리 삭제", value="del_cat", description="카테고리와 그 안의 모든 제품을 삭제합니다.", emoji="🔥")
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
            # 제품 삭제 시 카테고리 선택 컨테이너 전송
            await it.response.send_message(view=CategorySelectView(purpose="delete"), ephemeral=True)
        elif val == "del_cat":
            # 카테고리 삭제 모달 바로 띄우기
            await it.response.send_modal(CategoryDeleteModal())
