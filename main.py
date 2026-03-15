class StockProductSelectView(ui.LayoutView):
    def __init__(self, category):
        super().__init__(timeout=60)
        self.category = category
        self.con = ui.Container(ui.TextDisplay(f"## 📦 [{category}] 제품 선택"), accent_color=0x000000)
        
        # 해당 카테고리 제품만 가져오기
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT name FROM products WHERE category = ?", (category,))
        prods = cur.fetchall(); conn.close()
        options = [discord.SelectOption(label=p[0], value=p[0]) for p in prods] if prods else [discord.SelectOption(label="제품 없음", value="none")]
        
        self.prod_select = ui.Select(placeholder="수정할 제품을 선택하세요", options=options)
        self.prod_select.callback = self.prod_callback
        self.con.add_item(ui.ActionRow(self.prod_select))
        self.add_item(self.con)

    async def prod_callback(self, it: discord.Interaction):
        prod_name = self.prod_select.values[0]
        if prod_name == "none": return
        
        # 현재 재고 값 가져오기
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT stock FROM products WHERE name = ?", (prod_name,))
        current_stock = cur.fetchone()[0]; conn.close()
        
        # 최종 단계: 재고 수정 모달 띄우기
        await it.response.send_modal(StockFinalEditModal(prod_name, current_stock))
