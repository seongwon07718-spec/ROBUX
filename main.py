class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## 🛠️ 상품 관리 도구"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("아래 버튼을 눌러 상품을 등록하거나 재고를 입고하세요."))
        
        # 버튼으로 더 직관적으로 변경
        btn = ui.Button(label="상품 설정 및 재고 입고", style=discord.ButtonStyle.primary, emoji="📦")
        btn.callback = self.admin_callback
        
        self.container.add_item(ui.ActionRow(btn))
        self.add_item(self.container)

    # 이 함수가 클래스 안에 정확히 있어야 두 번째 사진 에러가 안 납니다.
    async def admin_callback(self, it: discord.Interaction):
        await it.response.send_modal(ProductManageModal())
