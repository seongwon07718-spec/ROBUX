        # [수정된 저장 부분]
        import uuid
        web_key = str(uuid.uuid4())
        
        cur.execute("INSERT INTO buy_log (user_id, product_name, stock_data, date, web_key) VALUES (?, ?, ?, ?, ?)",
                    (u_id, self.prod_name, purchased_stock_text, time.strftime('%Y-%m-%d %H:%M'), web_key))
        conn.commit()
        conn.close()

        try:
            # Cloudflare Tunnel을 쓴다면 포트번호 없이 도메인만 입력
            domain = "swnx.shop" 
            view_url = f"http://{domain}/view?key={web_key}"
            
            # ... (이후 버튼 및 DM 전송 코드는 동일)
