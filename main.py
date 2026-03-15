class ProductManageModal(ui.Modal, title="📦 상품 및 재고 통합 관리"):
    # 1. 카테고리 입력 (텍스트)
    cat = ui.TextInput(label="카테고리", placeholder="카테고리 이름을 입력하세요", min_length=1)
    
    # 2. 제품 선택 메뉴 (사진처럼 모달 안의 셀렉트 메뉴)
    # 기존 DB에 있는 제품들을 선택하거나 새 제품을 등록할 수 있도록 구성
    name_select = ui.Select(
        placeholder="제품을 선택하거나 아래에 직접 입력하세요",
        options=[discord.SelectOption(label="신규 등록 (직접 입력)", value="new")],
        min_values=1, max_values=1
    )
    
    # 3. 신규 제품명 또는 기존 제품 확인용 (선택이 'new'일 때 사용)
    name_input = ui.TextInput(label="제품명 (신규 등록 시 필수)", placeholder="기존 제품 선택 시 비워두셔도 됩니다", required=False)
    
    # 4. 가격 설정
    price = ui.TextInput(label="가격 (숫자만)", placeholder="예: 5000", min_length=1)
    
    # 5. 재고 입고 (기존 재고 + 입력값)
    add_stock = ui.TextInput(label="재고 입고 수량 (더해질 수량)", placeholder="예: 10 (입력한 만큼 재고가 늘어납니다)", min_length=1)

    def __init__(self):
        super().__init__()
        # 초기화 시점에 DB에서 제품 목록을 가져와 Select 메뉴에 채울 수도 있습니다.
        # 여기서는 기본 구조를 잡기 위해 수동 입력을 우선시하는 모달로 구성합니다.

    async def on_submit(self, it: discord.Interaction):
        # 숫자 유효성 검사
        if not self.price.value.isdigit() or not self.add_stock.value.isdigit():
            return await it.response.send_message("❌ 가격과 입고 수량은 숫자만 입력 가능합니다.", ephemeral=True)

        final_name = self.name_input.value if self.name_input.value else "미지정 제품"
        in_stock = int(self.add_stock.value)
        final_price = int(self.price.value)

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()

        # 제품이 있는지 확인
        cur.execute("SELECT stock FROM products WHERE name = ?", (final_name,))
        row = cur.fetchone()

        if row:
            # 기존 제품이 있으면: 가격 업데이트 + 재고 더하기(입고)
            cur.execute("UPDATE products SET category = ?, price = ?, stock = stock + ? WHERE name = ?", 
                        (self.cat.value, final_price, in_stock, final_name))
            msg = f"✅ **{final_name}** 제품의 정보 수정 및 **{in_stock}개** 입고 완료!"
        else:
            # 제품이 없으면 신규 생성
            cur.execute("INSERT INTO products (category, name, price, stock) VALUES (?, ?, ?, ?)", 
                        (self.cat.value, final_name, final_price, in_stock))
            msg = f"✨ **{final_name}** 신규 제품 등록 및 **{in_stock}개** 입고 완료!"

        conn.commit()
        conn.close()

        # 결과 컨테이너 전송
        res_con = ui.Container(ui.TextDisplay("## 📦 처리 결과"), accent_color=0x00ff00)
        res_con.add_item(ui.TextDisplay(msg))
        await it.response.send_message(view=ui.LayoutView().add_item(res_con), ephemeral=True)
