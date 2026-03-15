async def cat_callback(interaction: discord.Interaction):
    selected = cat_select.values[0]
    
    conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
    # [중요] 여기에 sold_count를 반드시 추가해야 합니다! 
    # (기존: name, price, stock -> 수정: name, price, stock, sold_count)
    cur.execute("SELECT name, price, stock, sold_count FROM products WHERE category = ?", (selected,))
    products = cur.fetchall(); conn.close()

    # 데이터 출력 부분 (이미 수정하셨겠지만 한 번 더 확인하세요)
    if products:
        item_text = "\n".join([
            f"<:dot_white:1482000567562928271> 제품: **{p[0]}**\n"
            f"<:dot_white:1482000567562928271> 가격: {p[1]:,}원\n"
            f"<:dot_white:1482000567562928271> 재고: {p[2]}개 / 누적 판매: {p[3]}개\n" 
            for p in products
        ])
    else:
        item_text = "제품이 없습니다"
    
    # ... (나머지 Container 및 edit_message 코드는 동일)
