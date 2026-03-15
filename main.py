class StockCategorySelectView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=60)
        self.con = ui.Container(ui.TextDisplay("## 📝 재고 수정 - 카테고리 선택"), accent_color=0x000000)
        
        # 카테고리 목록 가져오기
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products")
        cats = cur.fetchall(); conn.close()
        options = [discord.SelectOption(label=c[0], value=c[0]) for c in cats] if cats else [discord.SelectOption(label="카테고리 없음", value="none")]
        
        self.cat_select = ui.Select(placeholder="카테고리를 선택하세요", options=options)
        self.cat_select.callback = self.cat_callback
        self.con.add_item(ui.ActionRow(self.cat_select))
        self.add_item(self.con)

    async def cat_callback(self, it: discord.Interaction):
        selected_cat = self.cat_select.values[0]
        if selected_cat == "none": return
        # 다음 단계: 제품 선택 컨테이너로 이동
        await it.response.send_message(view=StockProductSelectView(selected_cat), ephemeral=True)
