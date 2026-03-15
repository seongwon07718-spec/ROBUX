        # [수정 위치: conn.commit() 직전]
        web_key = str(uuid.uuid4()) # 중복 불가능한 랜덤 키 생성
        cur.execute("INSERT INTO buy_log (user_id, product_name, stock_data, date, web_key) VALUES (?, ?, ?, ?, ?)",
                    (u_id, self.prod_name, purchased_stock_text, time.strftime('%Y-%m-%d %H:%M'), web_key))
        
        conn.commit()
        conn.close()

        # [수정 위치: view_url 생성 부분]
        domain = "rbxshop.cloud:88" # 88번 포트 사용
        view_url = f"http://{domain}/view?key={web_key}" # id 대신 key 사용 (보안)
