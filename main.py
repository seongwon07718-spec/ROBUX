async def stock_edit_product_callback(self, it: discord.Interaction):
    prod_name = it.data['values'][0]
    if prod_name == "none": return
    
    # [중요] DB에서 현재 저장된 '실제 재고 리스트'를 가져옵니다.
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()
    cur.execute("SELECT stock_data FROM products WHERE name = ?", (prod_name,))
    res = cur.fetchone()
    conn.close()
    
    # 데이터가 있으면 그 내용을, 없으면 빈 값을 준비합니다.
    current_stock_list = res[0] if res and res[0] else ""
    
    # 가져온 실제 재고 데이터(current_stock_list)를 모달에 전달합니다.
    await it.response.send_modal(StockDataListModal(prod_name, current_stock_list))
