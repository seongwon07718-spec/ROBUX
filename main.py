class FinalBuyView(ui.LayoutView):

    def __init__(self, pass_info: dict, money: int, user_id: int | str, discount: int = 0):

        super().__init__(timeout=60)
        self.pass_info = pass_info
        self.money = money
        self.user_id = str(user_id)
        self.discount = discount
        self._build_ui()

    def _build_ui(self):

        con = ui.Container()
        con.accent_color = 0x5865F2

        discount_text = f"\n-# - **할인율**: {self.discount}%" if self.discount > 0 else ""

        con.add_item(ui.TextDisplay(
            f"### <:acy2:1489883409001091142> 최종 단계\n"
            f"-# - **게임패스 이름**: {self.pass_info.get('name', '알 수 없음')}\n"
            f"-# - **로벅스**: {self.pass_info.get('price', 0):,}로벅스"
            f"{discount_text}\n"
            f"-# - **차감금액**: {self.money:,}원"
        ))

        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        btn = ui.Button(
            label="진행하기",
            style=discord.ButtonStyle.gray,
            emoji="<:upvote:1489930275868770305>"
        )
        btn.callback = self.do_buy
        con.add_item(ui.ActionRow(btn))
        self.add_item(con)
