# ─── 메인 자판기 뷰 ───────────────────────────────────────────
class VendingMainView(discord.ui.LayoutView):
    def __init__(self, gid, bot, title="자판기", desc="버튼을 눌러 이용하세요.", color=0x5865F2):
        super().__init__(timeout=None)
        self.gid = gid
        self.bot = bot

        self.container = discord.ui.Container(
            discord.ui.TextDisplay(f"## {title}\n{desc}"),
            discord.ui.Separator(),
            accent_color=color,
        )

        self.row = discord.ui.ActionRow(
            discord.ui.Button(label="구매",      style=discord.ButtonStyle.success,   custom_id=f"v_buy_{gid}"),
            discord.ui.Button(label="제품 보기", style=discord.ButtonStyle.secondary, custom_id=f"v_browse_{gid}"),
            discord.ui.Button(label="충전",      style=discord.ButtonStyle.primary,   custom_id=f"v_charge_{gid}"),
            discord.ui.Button(label="내 정보",   style=discord.ButtonStyle.secondary, custom_id=f"v_info_{gid}"),
        )
        self.add_item(self.row)

    async def on_interaction(self, i: discord.Interaction):
        cid = i.data.get("custom_id", "")
        
        if cid == f"v_buy_{self.gid}":
            gdb = GuildDB(self.gid)
            cats = gdb.get_cats()
            if not cats:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(
                        discord.ui.TextDisplay("카테고리가 없습니다."), 
                        accent_color=0xFEE75C
                    )
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
                return
            await i.response.send_message(view=BuyCatView(self.gid, cats), ephemeral=True)

        elif cid == f"v_browse_{self.gid}":
            gdb = GuildDB(self.gid)
            cats = gdb.get_cats()
            if not cats:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(
                        discord.ui.TextDisplay("카테고리가 없습니다."), 
                        accent_color=0xFEE75C
                    )
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
                return
            await i.response.send_message(view=BrowseView(self.gid, cats), ephemeral=True)

        elif cid == f"v_charge_{self.gid}":
            gdb = GuildDB(self.gid)
            if not gdb.get_cfg("bank_num"):
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(
                        discord.ui.TextDisplay("충전 계좌가 설정되지 않았습니다."), 
                        accent_color=0xED4245
                    )
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
                return
            await i.response.send_modal(ChargeModal(self.gid, self.bot))

        elif cid == f"v_info_{self.gid}":
            gdb = GuildDB(self.gid)
            ud = gdb.get_user(i.user.id)
            await i.response.send_message(view=InfoView(self.gid, i.user.id, ud), ephemeral=True)
