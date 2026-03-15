# --- [ 1. 제품 선택 드롭다운 클래스 ] ---
class ProductSelect(ui.Select):
    def __init__(self, category=None):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        # 해당 카테고리의 제품 목록 가져오기
        if category:
            cur.execute("SELECT name FROM products WHERE category = ?", (category,))
        else:
            cur.execute("SELECT name FROM products")
        prods = cur.fetchall(); conn.close()

        options = [discord.SelectOption(label=p[0], value=p[0]) for p in prods]
        if not options:
            options = [discord.SelectOption(label="등록된 제품 없음", value="none")]

        super().__init__(placeholder="관리할 제품을 선택하세요", options=options)

# --- [ 2. 통합 관리 모달 (V2 방식) ] ---
class ProductManageModal(ui.Modal, title="📦 상품 및 재고 관리"):
    cat = ui.TextInput(label="카테고리 (신규 등록 시 필수)", placeholder="카테고리 입력", required=False)
    
    # 보내주신 사진의 ui.Label + component(Dropdown) 방식 적용
    product_dropdown = ui.Label(
        text="수정/입고할 제품 선택",
        component=ProductSelect()
    )
    
    new_name = ui.TextInput(label="신규 제품명 (신규 등록 시에만)", placeholder="기존 제품 수정 시 비워두세요", required=False)
    price = ui.TextInput(label="가격", placeholder="숫자만 입력", required=False)
    
    stock_data = ui.TextInput(
        label="재고 입고 (줄바꿈당 1개)", 
        style=discord.TextStyle.paragraph, 
        placeholder="내용을 입력하세요. 줄 수만큼 재고가 추가됩니다.",
        required=False
    )

    async def on_submit(self, it: discord.Interaction):
        selected_prod = self.product_dropdown.component.values[0]
        final_name = self.new_name.value if self.new_name.value else selected_prod
        
        if final_name == "none" and not self.new_name.value:
            return await it.response.send_message("❌ 제품명을 선택하거나 입력해주세요.", ephemeral=True)

        # 줄바꿈 재고 계산
        lines = self.stock_data.value.split('\n')
        add_count = len([l for l in lines if l.strip()])

        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        
        # 제품 존재 확인
        cur.execute("SELECT name FROM products WHERE name = ?", (final_name,))
        if cur.fetchone():
            # 기존 제품 업데이트 (입력된 값만 변경)
            if self.price.value:
                cur.execute("UPDATE products SET price = ? WHERE name = ?", (int(self.price.value), final_name))
            if add_count > 0:
                cur.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (add_count, final_name))
            status = f"✅ **{final_name}** 수정/입고 완료!"
        else:
            # 신규 제품 등록
            cur.execute("INSERT INTO products (category, name, price, stock) VALUES (?, ?, ?, ?)",
                        (self.cat.value, final_name, int(self.price.value or 0), add_count))
            status = f"✨ **{final_name}** 신규 등록 완료!"

        conn.commit(); conn.close()
        await it.response.send_message(status, ephemeral=True)
