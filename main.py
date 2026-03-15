def process_purchase(user_id, product_name):
    """구매 성공 시 재고 차감 및 누적 판매량 증가"""
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()
    
    # 1. 재고 데이터 하나 가져오기 (가장 윗줄)
    cur.execute("SELECT stock_data FROM products WHERE name = ?", (product_name,))
    res = cur.fetchone()
    if not res or not res[0]:
        return None # 재고 없음
    
    stock_list = res[0].split('\n')
    item_to_sell = stock_list[0] # 첫 번째 재고 코드
    remaining_stock = "\n".join(stock_list[1:]) # 남은 재고 리스트
    
    # 2. DB 업데이트: 재고 1 감소, 누적 판매 1 증가, 재고 텍스트 갱신
    cur.execute("""UPDATE products 
                   SET stock = stock - 1, 
                       sold_count = sold_count + 1, 
                       stock_data = ? 
                   WHERE name = ?""", (remaining_stock, product_name))
    
    conn.commit()
    conn.close()
    return item_to_sell
