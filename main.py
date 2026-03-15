class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## 상품설정 메뉴"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("신규 상품 또는 상품설정을 해주세요"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        btn_new = ui.Button(label="신규상품", style=discord.ButtonStyle.success, emoji="✨")
        btn_edit = ui.Button(label="상품설정", style=discord.ButtonStyle.primary, emoji="⚙️")
        
        btn_new.callback = self.new_callback
        btn_edit.callback = self.edit_callback
        
        self.container.add_item(ui.ActionRow(btn_new, btn_edit))
        self.add_item(self.container)

    async def new_callback(self, it: discord.Interaction):
        await it.response.send_modal(NewProductModal())

    async def edit_callback(self, it: discord.Interaction):
        await it.response.send_message(view=CategorySelectView(), ephemeral=True)
