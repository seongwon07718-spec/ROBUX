# --- [ 메인 자판기 레이아웃 ] ---
class MeuLayout(ui.LayoutView):
    def __init__(self):
        # ✅ timeout=None: 이 설정으로 3분이 지나도 버튼 세션이 만료되지 않습니다.
        super().__init__(timeout=None) 
        
        self.container = ui.Container(ui.TextDisplay("## 🛒 자판기 메뉴"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        shop = ui.Button(label="제품", emoji="<:1302328347765899395:1480120014735540235>")
        chage = ui.Button(label="충전", emoji="<:1302328427545624689:1480120016056619038>")
        buy = ui.Button(label="구매", emoji="<:1302328398856847474:1480120020129419314>")
        info = ui.Button(label="정보", emoji="<:1306285145132892180:1480120018602688664>")
        
        shop.callback = self.shop_callback
        chage.callback = self.chage_callback
        buy.callback = self.buy_callback
        info.callback = self.info_callback
        
        self.container.add_item(ui.ActionRow(shop, chage, buy, info))
        self.add_item(self.container)

    # ✅ 모든 버튼 클릭 시 상호작용 오류를 방지하기 위해 defer() 또는 즉시 응답 사용
    async def shop_callback(self, it: discord.Interaction):
        await it.response.send_message("준비중입니다", ephemeral=True)

    async def chage_callback(self, it: discord.Interaction):
        # 충전 방식 선택창 전송 (상호작용 만료 방지)
        await it.response.send_message(view=ChargeLayout(), ephemeral=True)

    async def buy_callback(self, it: discord.Interaction):
        await it.response.send_message("준비중입니다", ephemeral=True)
    
    async def info_callback(self, it: discord.Interaction):
        # 1. 즉시 응답 처리 (이게 없으면 3초 뒤 상호작용 실패가 뜹니다)
        await it.response.defer(ephemeral=True)
        
        u_id = str(it.user.id)
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT money, total_spent FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone(); conn.close()
        money, total_spent = (row[0], row[1]) if row else (0, 0)

        container = ui.Container(ui.TextDisplay(f"## {it.user.display_name}님의 정보"), accent_color=0xffffff)
        container.add_item(ui.TextDisplay(f"보유 잔액: {money:,}원\n누적 금액: {total_spent:,}원"))
        
        selecao = ui.Select(placeholder="조회할 내역 선택", options=[
            discord.SelectOption(label="최근 충전 내역", value="charge", emoji="💰")
        ])

        async def resp(i: discord.Interaction):
            if selecao.values[0] == "charge":
                conn2 = sqlite3.connect('vending_data.db'); cur2 = conn2.cursor()
                cur2.execute("SELECT amount, date FROM charge_logs WHERE user_id = ? ORDER BY date DESC LIMIT 5", (u_id,))
                logs = cur2.fetchall(); conn2.close()
                
                log_con = ui.Container(ui.TextDisplay("## 최근 충전 내역"), accent_color=0x5865F2)
                if logs:
                    log_text = "\n".join([f"• {l[1]} | {l[0]:,}원" for l in logs])
                    log_con.add_item(ui.TextDisplay(log_text))
                else: log_con.add_item(ui.TextDisplay("내역이 없습니다."))
                await i.response.send_message(view=ui.LayoutView().add_item(log_con), ephemeral=True)

        selecao.callback = resp
        container.add_item(ui.ActionRow(selecao))
        
        # 2. defer를 사용했으므로 followup으로 결과 전송
        await it.followup.send(view=ui.LayoutView().add_item(container), ephemeral=True)

# --- [ 명령어 부분 ] ---
@bot.tree.command(name="자판기", description="상호작용 오류가 없는 영구 버튼 자판기를 전송합니다")
async def vending(interaction: discord.Interaction):
    # 이제 주기적으로 메시지를 수정하거나 삭제하지 않습니다.
    await interaction.response.send_message("**자판기가 전송되었습니다**", ephemeral=True)
    await interaction.channel.send(view=MeuLayout())
