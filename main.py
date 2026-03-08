# --- [ 상호작용 오류 방지용 자판기 레이아웃 ] ---
class MeuLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None) # ✅ 버튼 타임아웃을 None으로 설정 (영구 유지)
        container = ui.Container(ui.TextDisplay("## 🛒 자판기 메뉴"), accent_color=0xffffff)
        
        # 버튼 생성 (에모지 포함)
        self.shop_btn = ui.Button(label="제품", emoji="<:1302328347765899395:1480120014735540235>")
        self.chage_btn = ui.Button(label="충전", emoji="<:1302328427545624689:1480120016056619038>")
        self.buy_btn = ui.Button(label="구매", emoji="<:1302328398856847474:1480120020129419314>")
        self.info_btn = ui.Button(label="정보", emoji="<:1306285145132892180:1480120018602688664>")
        
        # 콜백 연결
        self.shop_btn.callback = self.shop_callback
        self.chage_btn.callback = self.chage_callback
        self.buy_btn.callback = self.buy_callback
        self.info_btn.callback = self.info_callback
        
        container.add_item(ui.ActionRow(self.shop_btn, self.chage_btn, self.buy_btn, self.info_btn))
        self.add_item(container)

    # 모든 콜백 시작 부분에 에러 방지 로직 추가
    async def shop_callback(self, it: discord.Interaction):
        # 즉시 '생각 중...' 상태로 만들어 상호작용 만료를 방지
        await it.response.send_message("제품 목록을 불러오는 중입니다...", ephemeral=True)

    async def chage_callback(self, it: discord.Interaction):
        # 상호작용 실패 오류를 막기 위해 즉시 모달을 띄움
        await it.response.send_modal(ChargeModal()) # 충전 수단 선택 모달 등

    async def info_callback(self, it: discord.Interaction):
        # 1. 상호작용 즉시 응답 (오류 방지 핵심)
        await it.response.defer(ephemeral=True) 
        
        u_id = str(it.user.id)
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT money, total_spent FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone(); conn.close()
        
        money, total_spent = (row[0], row[1]) if row else (0, 0)
        
        # 2. 내역 불러오기 (최근 충전 내역 포함)
        # (기존의 내역 조회 로직 동일하게 수행)
        
        container = ui.Container(ui.TextDisplay(f"## {it.user.display_name}님의 정보"), accent_color=0xffffff)
        container.add_item(ui.TextDisplay(f"보유 잔액: {money:,}원\n누적 금액: {total_spent:,}원"))
        
        # 3. 이미 defer를 했으므로 followup으로 전송
        await it.followup.send(view=ui.LayoutView().add_item(container), ephemeral=True)

# --- [ 자동 갱신 루프 (2분마다 세션 리프레시) ] ---
async def update_vending_session(msg):
    """메시지를 수정하여 버튼의 상호작용 가능 시간을 무한히 연장합니다."""
    while True:
        await asyncio.sleep(120) # 2분마다
        try:
            # 뷰를 다시 생성해서 덮어씌움으로써 세션을 갱신함
            await msg.edit(view=MeuLayout())
        except:
            break

@bot.tree.command(name="자판기", description="상호작용 오류가 없는 자판기를 소환합니다")
async def vending(interaction: discord.Interaction):
    # 관리자에게만 보이는 시작 메시지
    await interaction.response.send_message("✅ 자판기 세션 최적화 모드로 가동합니다.", ephemeral=True)
    
    view = MeuLayout()
    msg = await interaction.channel.send(view=view)
    
    # 백그라운드에서 버튼 세션 유지 (가장 중요한 부분)
    bot.loop.create_task(update_vending_session(msg))
