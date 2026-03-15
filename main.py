class ProductManageModal(ui.Modal, title="📦 상품 및 재고 통합 관리"):
    cat = ui.TextInput(label="카테고리", placeholder="카테고리 이름을 입력하세요", min_length=1)
    name = ui.TextInput(label="제품명", placeholder="정확한 제품명을 입력하세요", min_length=1)
    price = ui.TextInput(label="가격 (숫자만)", placeholder="예: 5000", min_length=1)
    
    # 재고 입력 칸을 한 줄이 아닌 여러 줄(Paragraph)로 변경
    stock_list = ui.TextInput(
        label="재고 입고 (줄바꿈으로 구분)", 
        style=discord.TextStyle.paragraph, 
        placeholder="내용을 입력하세요.\n입력한 '줄 수'만큼 재고가 추가됩니다.\n예:\n값1\n값2\n값3 (이렇게 적으면 3개 추가)",
        min_length=1
    )

    async def on_submit(self, it: discord.Interaction):
        # 1. 가격 숫자 체크
        if not self.price.value.isdigit():
            return await it.response.send_message("❌ 가격은 숫자만 입력 가능합니다.", ephemeral=True)

        # 2. 줄바꿈을 기준으로 데이터를 나눠서 개수 파악
        # 공백만 있는 줄은 제외하고 실제 내용이 있는 줄만 카운트합니다.
        raw_stock = self.stock_list.value.split('\n')
        clean_stock = [line for line in raw_stock if line.strip()] 
        add_count = len(clean_stock) # 줄 수가 곧 추가할 재고량

        if add_count == 0:
            return await it.response.send_message("❌ 입고할 재고 내용을 입력해주세요.", ephemeral=True)

        final_name = self.name.value.strip()
        final_price = int(self.price.value)

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()

        # 제품 존재 여부 확인
        cur.execute("SELECT stock FROM products WHERE name = ?", (final_name,))
        row = cur.fetchone()

        if row:
            # 기존 제품: 가격 업데이트 + 줄 수만큼 재고 더하기
            cur.execute("UPDATE products SET category = ?, price = ?, stock = stock + ? WHERE name = ?", 
                        (self.cat.value, final_price, add_count, final_name))
            msg = f"✅ **{final_name}** 정보 수정 완료\n📥 **{add_count}개**의 재고가 새로 입고되었습니다!"
        else:
            # 신규 제품: 등록 + 줄 수만큼 재고 설정
            cur.execute("INSERT INTO products (category, name, price, stock) VALUES (?, ?, ?, ?)", 
                        (self.cat.value, final_name, final_price, add_count))
            msg = f"✨ **{final_name}** 신규 등록 완료\n📥 **{add_count}개**의 재고가 입고되었습니다!"

        conn.commit()
        conn.close()

        # 결과 컨테이너
        res_con = ui.Container(ui.TextDisplay("## 📦 재고 입고 완료"), accent_color=0x00ff00)
        res_con.add_item(ui.TextDisplay(msg))
        res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        res_con.add_item(ui.TextDisplay(f"-# 현재 입력된 데이터: {add_count}줄 인식됨"))
        
        await it.response.send_message(view=ui.LayoutView().add_item(res_con), ephemeral=True)
