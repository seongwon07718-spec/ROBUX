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
        con.add_item(ui.TextDisplay("### <:emoji_18:1487422236838334484>  실시간 재고"))
        stock_button = ui.Button(
            label=f"현재 재고: {stock_display}", 
            style=discord.ButtonStyle.blurple, 
            disabled=True
        )
        con.add_item(ui.ActionRow(stock_button))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay("### <:emoji_18:1487422236838334484>  지급방식"))
        con.add_item(ui.TextDisplay("-# - **게임패스 방식** / 무조건 본인 게임만\n-# - **글로벌 선물 방식** / 예시: 라이벌 - 번들"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        charge = ui.Button(label="충전", custom_id="charge", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        charge.callback = self.main_callback
        
        info = ui.Button(label="정보", custom_id="info", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        info.callback = self.info_callback

        shop = ui.Button(label="구매", custom_id="buying", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        shop.callback = self.shop_callback
        
        row_btns = ui.ActionRow(charge, info, shop)
        con.add_item(row_btns)
        self.add_item(con)
        return con

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.vending_msg_info = {}

    async def setup_hook(self):
        self.stock_updater.start()
        await self.tree.sync()

    @tasks.loop(minutes=2.0)
    async def stock_updater(self):
        if not self.vending_msg_info:
            return

        for channel_id, msg_id in list(self.vending_msg_info.items()):
            try:
                channel = self.get_channel(channel_id)
                if not channel: continue
                
                msg = await channel.fetch_message(msg_id)
                view = RobuxVending(self)
                con = await view.build_main_menu()
                
                await msg.edit(view=ui.LayoutView().add_item(con))
            except Exception as e:
                print(f"Update Error: {e}")

    @stock_updater.before_loop
    async def before_stock_updater(self):
        await self.wait_until_ready()
