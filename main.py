class AddCategoryModal(ui.Modal, title="신규 카테고리 추가"):
    cat_name = ui.TextInput(label="카테고리 이름", placeholder="생성할 카테고리 이름을 입력하세요")

    async def on_submit(self, it: discord.Interaction):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        
        # 중복 체크 (선택 사항이지만 안전을 위해 권장)
        cur.execute("SELECT DISTINCT category FROM products WHERE category = ?", (self.cat_name.value,))
        if cur.fetchone():
            conn.close()
            return await it.response.send_message(f"**이미 존재하는 카테고리입니다: {self.cat_name.value}**", ephemeral=True)
            
        # 카테고리 생성을 위해 임시로 '더미' 제품을 넣거나, 카테고리 전용 테이블이 있다면 거기에 넣어야 합니다.
        # 현재 구조상 products 테이블에서 category를 관리하므로, 빈 제품을 하나 등록하거나 구조에 맞춰 저장합니다.
        # 여기서는 제품명 '카테고리 생성용'으로 임시 등록하는 예시입니다. (실제 제품 목록에는 노출되지 않게 처리 필요)
        cur.execute("INSERT INTO products (category, name, price, stock, sold_count) VALUES (?, ?, ?, ?, ?)",
                    (self.cat_name.value, f"[{self.cat_name.value}] 안내", 0, 0, 0))
        
        conn.commit(); conn.close()
        await it.response.send_message(f"**카테고리 __{self.cat_name.value}__ 등록이 완료되었습니다.**", ephemeral=True)
