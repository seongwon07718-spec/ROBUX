# ─── 메인 자판기 뷰 ───────────────────────────────────────────
class VendingMainView(discord.ui.LayoutView):
    def __init__(self, gid, bot, title="구매하기", desc="아래 버튼을 눌러 이용해주세요", color=0x5865F2):
        super().__init__(timeout=None)
        self.gid = gid
        self.bot = bot

        self.container = discord.ui.Container(
            discord.ui.TextDisplay(f"## {title}\n{desc}"),
            discord.ui.Separator(),
            discord.ui.ActionRow(
                discord.ui.Button(label="구매",      style=discord.ButtonStyle.secondary,   custom_id=f"v_buy_{gid}"),
                discord.ui.Button(label="제품", style=discord.ButtonStyle.secondary, custom_id=f"v_browse_{gid}"),
                discord.ui.Button(label="충전",      style=discord.ButtonStyle.secondary,   custom_id=f"v_charge_{gid}"),
                discord.ui.Button(label="정보",   style=discord.ButtonStyle.secondary, custom_id=f"v_info_{gid}"),
            ),
            accent_color=color,
        )
        self.add_item(self.container)

        btn.buy.callback = self.on_interaction
        btn.browse.callback = self.on_interaction
        btn.charge.callback = self.on_interaction
        btn.info.callback = self.on_interaction
