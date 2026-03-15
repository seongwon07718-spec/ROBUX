class CategoryDeleteModal(ui.Modal, title="🔥 카테고리 삭제"):
    def __init__(self):
        super().__init__()
        self.cat_select = ui.Label(
            text="삭제할 카테고리를 선택하세요 (안의 제품도 모두 삭제됨)",
            component=CategorySelect()
        )
        self.add_item(self.cat_select)

    async def on_submit(self, it: discord.Interaction):
        cat_name = self.cat_select.component.values[0]
        if cat_name == "none": return
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE category = ?", (cat_name,))
        conn.commit(); conn.close()
        await it.response.send_message(f"🗑️ 카테고리 **[{cat_name}]** 및 포함된 모든 제품이 삭제되었습니다.", ephemeral=True)
