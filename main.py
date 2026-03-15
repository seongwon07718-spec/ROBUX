# --- [ 1. 재고수정 전용 제품 선택 콜백 ] ---
# (재고수정 메뉴 드롭다운의 콜백 부분에 넣어주세요)
async def stock_edit_product_callback(self, it: discord.Interaction):
    prod_name = it.data['values'][0] # 선택한 제품명
    if prod_name == "none": return
    
    # [핵심] DB에서 이 제품에 들어있는 전체 재고 리스트(stock_data)를 가져옵니다.
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()
    cur.execute("SELECT stock_data FROM products WHERE name = ?", (prod_name,))
    res = cur.fetchone()
    conn.close()
    
    # 데이터가 있으면 가져오고, 없으면 빈 칸으로 설정
    current_data = res[0] if res and res[0] else ""
    
    # 2단계: 가져온 데이터를 '재고 리스트' 칸에 채워서 모달을 띄웁니다.
    await it.response.send_modal(StockDataListModal(prod_name, current_data))


# --- [ 2. 재고수정 모달 (기존 코드 유지) ] ---
class StockDataListModal(ui.Modal):
    def __init__(self, name, current_data):
        super().__init__(title=f"{name} 재고 관리")
        self.name = name
        
        self.data_input = ui.TextInput(
            label="재고 리스트",
            style=discord.TextStyle.paragraph,
            default=str(current_data), # ← 여기서 입고 시 추가했던 데이터가 보입니다.
            placeholder="수정하거나 삭제하세요",
            required=False
        )
        self.add_item(self.data_input)

    async def on_submit(self, it: discord.Interaction):
        updated_data = self.data_input.value
        new_count = len([l for l in updated_data.split('\n') if l.strip()])

        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        # 사용자가 수정한 텍스트와 계산된 개수를 다시 DB에 저장
        cur.execute("UPDATE products SET stock_data = ?, stock = ? WHERE name = ?", 
                    (updated_data, new_count, self.name))
        conn.commit(); conn.close()
        
        await it.response.send_message(f"**__{self.name}__ 재고 수정 완료되었습니다 (현재: __{new_count}__개)**", ephemeral=True)
