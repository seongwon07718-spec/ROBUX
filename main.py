class CategoryModal(ui.Modal, title="카테고리 설정"):
    cat_name = ui.TextInput(label="카테고리 이름", placeholder="새로운 카테고리명을 입력하세요")
    async def on_submit(self, it: discord.Interaction):
        # 카테고리는 제품 등록 시 자동으로 분류되므로 안내 메시지만 전송
        await it.response.send_message(f"✅ 카테고리 [**{self.cat_name.value}**] 설정 준비 완료. 제품 설정에서 등록해주세요.", ephemeral=True)

class ProductModal(ui.Modal, title="제품 설정"):
    cat_name = ui.TextInput(label="카테고리", placeholder="예: 음료")
    prod_name = ui.TextInput(label="제품명", placeholder="예: 콜라")
    price = ui.TextInput(label="가격", placeholder="숫자만 입력")
    async def on_submit(self, it: discord.Interaction):
        if not self.price.value.isdigit():
            return await it.response.send_message("❌ 가격은 숫자만 입력하세요.", ephemeral=True)
        
        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        # DB에 제품 정보 저장 (이미 있으면 업데이트)
        cur.execute("INSERT OR REPLACE INTO products (category, name, price, stock) VALUES (?, ?, ?, ?)",
                    (self.cat_name.value, self.prod_name.value, int(self.price.value), 0))
        conn.commit(); conn.close()
        await it.response.send_message(f"✅ 제품 [**{self.prod_name.value}**]이(가) DB에 반영되었습니다.", ephemeral=True)

class StockModal(ui.Modal, title="재고 설정"):
    prod_name = ui.TextInput(label="제품명", placeholder="재고를 수정할 제품의 정확한 이름")
    count = ui.TextInput(label="수량", placeholder="변경할 숫자 입력")
    async def on_submit(self, it: discord.Interaction):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("UPDATE products SET stock = ? WHERE name = ?", (self.count.value, self.prod_name.value))
        conn.commit(); conn.close()
        await it.response.send_message(f"✅ [**{self.prod_name.value}**] 재고가 {self.count.value}개로 수정되었습니다.", ephemeral=True)
