class StockDataListModal(ui.Modal):
    def __init__(self, name, current_data):
        super().__init__(title=f"{name} 재고 관리")
        self.name = name
        
        self.data_input = ui.TextInput(
            label="재고 리스트",
            style=discord.TextStyle.paragraph,
            default=str(current_data),
            placeholder="재고가 비어있습니다", 
            required=False
        )
        self.add_item(self.data_input)

    async def on_submit(self, it: discord.Interaction):
        updated_data = self.data_input.value
        new_count = len([l for l in updated_data.split('\n') if l.strip()])

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        
        # 이전 재고 수량 확인
        cur.execute("SELECT stock FROM products WHERE name = ?", (self.name,))
        old_res = cur.fetchone()
        old_count = old_res[0] if old_res else 0

        cur.execute("UPDATE products SET stock_data = ?, stock = ? WHERE name = ?", 
                    (updated_data, new_count, self.name))
        conn.commit()
        conn.close()
        
        # 재고가 늘어난 경우에만 컨테이너 웹훅 전송
        if new_count > old_count:
            await self.send_stock_webhook_container(self.name, new_count, new_count - old_count)

        await it.response.send_message(f"**__{self.name}__ 재고 수정 완료되었습니다 (현재: __{new_count}__개)**", ephemeral=True)

    async def send_stock_webhook_container(self, name, total_count, added_count):
        # ⚠️ 웹훅 URL을 여기에 입력하세요
        WEBHOOK_URL = "본인의_웹훅_주소"
        
        # 컨테이너 디자인 구성 (검정/흰색 컨셉)
        # 이모지를 모두 빼고 깔끔하게 텍스트로만 구성했습니다.
        dm_con = ui.Container(ui.TextDisplay("## 제품 입고 알림"), accent_color=0xffffff)
        dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        dm_con.add_item(ui.TextDisplay(
            f"제품명: {name}\n"
            f"입고 수량: {added_count}개\n"
            f"현재 총 재고: {total_count}개"
        ))
        
        # 컨테이너를 포함한 뷰 생성
        dm_v = ui.LayoutView().add_item(dm_con)
        
        # 웹훅 전송 (Webhook 객체 사용)
        try:
            webhook = discord.Webhook.from_url(WEBHOOK_URL, session=aiohttp.ClientSession())
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
                # 컨테이너 뷰를 전송
                await webhook.send(view=dm_v)
        except Exception as e:
            print(f"웹훅 컨테이너 전송 실패: {e}")
