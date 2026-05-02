# ─── 메인 자판기 뷰 ───────────────────────────────────────────
class VendingMainView(discord.ui.LayoutView):
    def __init__(self, gid, bot, title="구매하기", desc="아래 버튼을 눌러 이용해주세요", color=0x5865F2):
        super().__init__(timeout=None)
        self.gid = gid
        self.bot = bot

        # 1. 버튼 변수 선언 및 콜백 연결
        btn_buy = discord.ui.Button(label="구매", style=discord.ButtonStyle.secondary, custom_id=f"v_buy_{gid}")
        btn_browse = discord.ui.Button(label="제품", style=discord.ButtonStyle.secondary, custom_id=f"v_browse_{gid}")
        btn_charge = discord.ui.Button(label="충전", style=discord.ButtonStyle.secondary, custom_id=f"v_charge_{gid}")
        btn_info = discord.ui.Button(label="정보", style=discord.ButtonStyle.secondary, custom_id=f"v_info_{gid}")

        btn_buy.callback = self.on_interaction
        btn_browse.callback = self.on_interaction
        btn_charge.callback = self.on_interaction
        btn_info.callback = self.on_interaction

        # 2. 컨테이너에 변수 삽입[span_0](start_span)[span_0](end_span)
        self.container = discord.ui.Container(
            discord.ui.TextDisplay(f"## {title}\n{desc}"),
            discord.ui.Separator(),
            discord.ui.ActionRow(btn_buy, btn_browse, btn_charge, btn_info),
            accent_color=color,
        )
        self.add_item(self.container)[span_1](start_span)[span_1](end_span)

# ─── 정보 확인 뷰 (InfoView) ───────────────────────────────────
class InfoView(discord.ui.LayoutView):
    def __init__(self, gid, bot):
        super().__init__(timeout=60)
        
        btn_back = discord.ui.Button(label="돌아가기", style=discord.ButtonStyle.secondary, custom_id=f"v_back_{gid}")
        btn_back.callback = self.on_interaction # 콜백 연결

        self.container = discord.ui.Container(
            discord.ui.TextDisplay("## 정보 확인\n원하시는 정보를 확인하세요."),
            discord.ui.ActionRow(btn_back),
            accent_color=0x5865F2,
        )
        self.add_item(self.container)[span_2](start_span)[span_2](end_span)
