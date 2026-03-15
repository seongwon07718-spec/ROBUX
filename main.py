class StockDataSelectView(ui.LayoutView):
    def __init__(self, category):
        super().__init__(timeout=60)
        self.con = ui.Container(ui.TextDisplay(f"## 📋 [{category}] 제품 선택"), accent_color=0x000000)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT name FROM products WHERE category = ?", (category,))
        prods = cur.fetchall(); conn.close()
        
        options = [discord.SelectOption(label=p[0], value=p[0]) for p in prods] if prods else [discord.SelectOption(label="제품 없음", value="none")]
        
        self.prod_select = ui.Select(placeholder="재고 목록을 수정할 제품 선택", options=options)
        self.prod_select.callback = self.prod_callback
        self.con.add_item(ui.ActionRow(self.prod_select))
        self.add_item(self.con)

    async def prod_callback(self, it: discord.Interaction):
        prod_name = self.prod_select.values[0]
        if prod_name == "none": return
        
        # DB에서 해당 제품의 '실제 재고 데이터' 문자열을 가져옵니다.
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT stock_data FROM products WHERE name = ?", (prod_name,))
        res = cur.fetchone(); conn.close()
        # 데이터가 없으면 빈 칸으로 표시
        current_data = res[0] if res and res[0] else ""
        
        # 2단계: 재고 리스트 수정 모달 띄우기
        await it.response.send_modal(StockListEditModal(prod_name, current_data))
