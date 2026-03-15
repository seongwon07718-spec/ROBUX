class ProductEditModal(ui.Modal):
    def __init__(self, category):
        super().__init__(title=f"⚙️ [{category}] 제품 설정")
        
        # 1. 드롭다운 추가
        self.prod_dropdown = ui.Label(
            text=f"{category} 제품 선택",
            component=ProductSelect(category=category)
        )
        self.add_item(self.prod_dropdown)
        
        # 2. 텍스트 입력창들 추가 (반드시 하나씩 add_item 해줘야 함)
        self.price = ui.TextInput(label="가격", required=False)
        self.stock_data = ui.TextInput(label="재고 입고", style=discord.TextStyle.paragraph, required=False)
        
        self.add_item(self.price)
        self.add_item(self.stock_data)
