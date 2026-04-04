class RobuxVending(ui.LayoutView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def build_main_menu(self):
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
        conn.close()

        cookie = row[0] if row else None
        robux, status = get_roblox_data(cookie)
        stock_display = f"{robux:,} R$" if status == "정상" else f"{status}"

        con = ui.Container()
        con.accent_color = 0x5865F2
        
        # 실시간 재고 섹션
        con.add_item(ui.Section(
            ui.TextDisplay("### <:emoji_18:1487422236838334484>  실시간 재고"),
            accessory=ui.Button(label=f"현재 재고: {stock_display}", style=discord.ButtonStyle.blurple, disabled=True)
        ))

        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 지급 방식 섹션
        con.add_item(ui.Section(
            ui.TextDisplay("### <:emoji_18:1487422236838334484>  지급방식\n-# - **게임패스 방식** / 무조건 본인 게임만\n-# - **글로벌 선물 방식** / 예시: 라이벌 - 번들"),
            accessory=ui.Thumbnail(media="https://cdn.discordapp.com/attachments/1485111392087314432/1487425365507833956/IMG_0013.png")
        ))
        
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 메인 버튼들
        charge = ui.Button(label="충전", custom_id="charge", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        charge.callback = self.main_callback # 기존 충전 콜백
        
        info = ui.Button(label="정보", custom_id="info", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        info.callback = self.info_callback

        shop = ui.Button(label="구매", custom_id="buying", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        shop.callback = self.shop_callback # 구매 버튼 콜백
        
        con.add_item(ui.ActionRow(charge, info, shop))
        
        self.clear_items()
        self.add_item(con)
        return con

    async def shop_callback(self, it: discord.Interaction):
        """구매 버튼 클릭 시 실행되는 함수"""
        con = ui.Container()
        con.accent_color = 0x5865F2
        
        con.add_item(ui.TextDisplay("### <:emoji_18:1487422236838334484>  구매 방식 선택"))
        con.add_item(ui.TextDisplay("-# 아래 버튼 중 원하시는 구매 방식을 선택해주세요.\n-# 각 방식에 따라 지급 속도와 절차가 다를 수 있습니다."))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 구매 방식 버튼 생성
        btn_gamepass = ui.Button(label="게임패스", style=discord.ButtonStyle.gray, emoji="🎮")
        btn_ingame = ui.Button(label="인게임", style=discord.ButtonStyle.gray, emoji="💎")
        btn_group = ui.Button(label="그룹", style=discord.ButtonStyle.gray, emoji="👥")

        # 버튼 콜백 설정 (나중에 상품 목록으로 연결)
        async def method_callback(interaction):
            await interaction.response.send_message(f"**{interaction.data['label']}** 방식 상품 준비 중입니다.", ephemeral=True)
        
        btn_gamepass.callback = method_callback
        btn_ingame.callback = method_callback
        btn_group.callback = method_callback

        con.add_item(ui.ActionRow(btn_gamepass, btn_ingame, btn_group))
        
        # 새로운 View 객체에 담아서 전송 (상호작용 오류 방지)
        new_view = ui.LayoutView(timeout=None)
        new_view.add_item(con)
        
        await it.response.send_message(view=new_view, ephemeral=True)

    # 나머지 기존 콜백들 (수정 금지)
    async def main_callback(self, it): pass
    async def info_callback(self, it): pass

