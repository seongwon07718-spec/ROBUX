    async def build_main_menu(self):
        """실시간 재고를 비활성화된 버튼에 표시하도록 수정된 버전"""
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
        conn.close()

        cookie = row[0] if row else None
        robux, status = get_roblox_data(cookie)
        # 상태에 따른 재고 텍스트 설정
        stock_display = f"{robux:,} R$" if status == "정상" else "점검 중"

        con = ui.Container()
        con.accent_color = 0x5865F2
        
        # 1. 지급 방식 안내
        con.add_item(ui.TextDisplay("### <:emoji_18:1487422236838334484>  지급방식\n-# - 겜패 선물 방식\n-# - 인게임 선물 방식"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 2. 실시간 재고 타이틀 및 버튼형 표시
        con.add_item(ui.TextDisplay("### <:emoji_18:1487422236838334484>  실시간 재고"))
        
        # [수정] 누를 수 없는 버튼(disabled=True)을 만들어 재고를 표시
        stock_button = ui.Button(
            label=f"현재 재고: {stock_display}", 
            style=discord.ButtonStyle.secondary, 
            disabled=True,
            emoji="📦"
        )
        con.add_item(ui.ActionRow(stock_button))
        
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 3. 버튼 안내
        con.add_item(ui.TextDisplay(f"### <:emoji_18:1487422236838334484>  버튼 안내\n-# - **Charge** - 충전하기 / 24시간 자동 충전\n-# - **Info** - 내 정보 / 거래내역 확인하기\n-# - **Buying** - 로벅스 구매하기 / 24시간 구매 가능"))

        # 4. 하단 조작 버튼들
        charge = ui.Button(label="Charge", custom_id="charge", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        charge.callback = self.main_callback
        
        info = ui.Button(label="Info", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        info.callback = self.info_callback

        shop = ui.Button(label="Buying", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        shop.callback = self.shop_callback
        
        row_btns = ui.ActionRow(charge, info, shop)
        con.add_item(row_btns)
        
        self.clear_items()
        self.add_item(con)
        return con

