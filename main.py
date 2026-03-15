class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## 🛠️ 관리자 메뉴"), accent_color=0x000000)
        
        # 버튼 구성
        new_btn = ui.Button(label="신규상품", style=discord.ButtonStyle.success, emoji="✨")
        edit_btn = ui.Button(label="상품설정", style=discord.ButtonStyle.primary, emoji="⚙️")
        
        new_btn.callback = self.new_callback
        edit_btn.callback = self.edit_callback
        
        self.container.add_item(ui.ActionRow(new_btn, edit_btn))
        self.add_item(self.container)

    async def new_callback(self, it: discord.Interaction):
        await it.response.send_modal(NewProductModal())

    async def edit_callback(self, it: discord.Interaction):
        await it.response.send_modal(ProductEditModal())

@bot.tree.command(name="상품설정", description="상품 관리 메뉴를 출력합니다.")
async def admin_setting(it: discord.Interaction):
    if not it.user.guild_permissions.administrator:
        return await it.response.send_message("❌ 권한이 없습니다.", ephemeral=True)
    
    # COMPONENTS_V2를 사용할 때는 content를 비우고 전송해야 400 에러가 안 납니다.
    await it.response.send_message(view=ProductAdminLayout(), ephemeral=True)
