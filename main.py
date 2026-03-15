class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        # 컨테이너에 정보 표시
        self.container = ui.Container(ui.TextDisplay("## 🛠️ 관리자 메뉴"), accent_color=0xffffff)
        self.container.add_item(ui.TextDisplay("아래 버튼을 눌러 모달을 열어주세요."))
        
        btn = ui.Button(label="제품 설정 및 입고", style=discord.ButtonStyle.success, emoji="⚙️")
        btn.callback = self.admin_callback
        
        self.container.add_item(ui.ActionRow(btn))
        self.add_item(self.container)

    async def admin_callback(self, it: discord.Interaction):
        # 최신 모달 실행
        await it.response.send_modal(ProductManageModal())

@bot.tree.command(name="상품설정", description="상품 관리 메뉴를 엽니다")
async def product_setting(it: discord.Interaction):
    if not it.user.guild_permissions.administrator:
        return await it.response.send_message("권한이 없습니다.", ephemeral=True)
    
    # 사진에서 발생한 400 Bad Request 에러를 피하기 위해 
    # 컨테이너 UI(V2)를 사용할 때는 content를 비우고 전송합니다.
    await it.response.send_message(view=ProductAdminLayout(), ephemeral=True)
