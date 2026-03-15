class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        # 1. 컨테이너 설정
        self.container = ui.Container(ui.TextDisplay("## 🛠️ 상품 관리 메뉴"), accent_color=0x000000)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("수행할 관리 작업을 아래 드롭바에서 선택하세요."))
        
        # 2. 드롭다운(Select) 생성
        self.admin_select = ui.Select(
            placeholder="관리 항목을 선택하세요...",
            options=[
                discord.SelectOption(label="신규상품 등록", value="new", description="새로운 상품을 DB에 추가합니다.", emoji="✨"),
                discord.SelectOption(label="기존상품 설정", value="edit", description="카테고리별 제품 수정 및 재고 입고", emoji="⚙️")
            ]
        )
        
        # 콜백 연결
        self.admin_select.callback = self.admin_callback
        
        # 3. 컨테이너에 드롭다운 추가 (ActionRow 활용)
        self.container.add_item(ui.ActionRow(self.admin_select))
        self.add_item(self.container)

    async def admin_callback(self, it: discord.Interaction):
        # 선택된 값(value)에 따라 분기 처리
        selected_value = self.admin_select.values[0]
        
        if selected_value == "new":
            # 신규상품 선택 시 모달 띄우기
            await it.response.send_modal(NewProductModal())
            
        elif selected_value == "edit":
            # 상품설정 선택 시 카테고리 선택 컨테이너 전송
            # (이전에 만든 CategorySelectView가 있어야 합니다)
            await it.response.send_message(view=CategorySelectView(), ephemeral=True)
