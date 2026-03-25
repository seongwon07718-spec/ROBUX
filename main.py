class RobuxMenu(ui.LayoutView):
    def __init__(self):
        super().__init__()
        con = ui.Container()
        con.accent_color = 0xffffff
        con.add_item(ui.TextDisplay("## 구매하기"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay("아래 버튼을 눌러 이용해주세요"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 1. 버튼 정의 (순서 중요: ActionRow에 넣기 전에 정의해야 함)
        buy = ui.Button(label="공지", emoji="<:emoji_16:1486337864953495743>")
        buy.callback = self.buy_callback # 아래에 buy_callback 함수가 있어야 함
        
        shop = ui.Button(label="제품", emoji="<:emoji_13:1486337836796874905>")
        shop.callback = self.shop_callback
        
        charge = ui.Button(label="충전", emoji="<:emoji_14:1486337849367330857>", custom_id="charge")
        charge.callback = self.main_callback
        
        info = ui.Button(label="정보", emoji="<:emoji_13:1486337822989484212>")
        info.callback = self.info_callback
        
        # 2. 버튼들을 ActionRow에 담아 컨테이너에 추가
        row = ui.ActionRow(buy, shop, charge, info)
        con.add_item(row)
        
        # 3. 뷰에는 컨테이너만 추가
        self.add_item(con)

    # 에러 방지를 위해 콜백 함수들이 반드시 존재해야 함
    async def buy_callback(self, it: discord.Interaction):
        await it.response.send_message("공지사항 준비 중", ephemeral=True)

    async def shop_callback(self, it: discord.Interaction):
        await it.response.send_message("제품 목록 준비 중", ephemeral=True)

    async def info_callback(self, it: discord.Interaction):
        await it.response.send_message("정보 조회 중", ephemeral=True)

    async def main_callback(self, it: discord.Interaction):
        cid = it.data.get('custom_id')
        if cid == "charge":
            con = ui.Container()
            con.accent_color = 0xffffff
            con.add_item(ui.TextDisplay("## 충전 수단 선택"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("원하시는 충전 방식을 선택해주세요"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            btn_bank = ui.Button(label="계좌이체", style=discord.ButtonStyle.gray)
            async def bank_cb(i: discord.Interaction):
                await i.response.send_modal(ChargeModal()) # ChargeModal 정의 필요
            btn_bank.callback = bank_cb
            
            # 중요: 버튼을 컨테이너 안에 ActionRow로 넣음
            con.add_item(ui.ActionRow(btn_bank))
            
            # 보낼 때는 LayoutView에 con 하나만 담음
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

