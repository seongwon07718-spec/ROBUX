# --- [ 전역 변수 ] ---
vending_msg = None # 자판기 메시지 객체 저장용

# --- [ 메인 자판기 갱신 로직 ] ---
class MeuLayout(ui.LayoutView):
    def __init__(self):
        super().__init__()
        # 컨테이너 구성은 기존과 동일
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

    # ... (callback 함수들은 기존과 동일)

# --- [ 상호작용 초기화 루프 (메시지 수정 방식) ] ---
async def keep_vending_alive(message):
    """2분마다 메시지를 '수정'하여 버튼 상호작용 세션을 유지합니다."""
    while True:
        await asyncio.sleep(120) # 2분마다 실행
        try:
            # 같은 내용으로 다시 edit하면 디스코드 서버에서 상호작용 시간이 갱신됩니다.
            await message.edit(view=MeuLayout())
            print(f"🔄 [자판기 갱신]: {time.strftime('%H:%M:%S')} - 상호작용 세션 연장 완료")
        except Exception as e:
            print(f"⚠️ 갱신 실패 (메시지가 삭제되었을 수 있음): {e}")
            break

# --- [ 명령어 부분 ] ---
@bot.tree.command(name="자판기", description="상호작용 오류가 없는 자판기를 전송합니다")
async def vending(interaction: discord.Interaction):
    await interaction.response.send_message("**자판기를 가동합니다.**", ephemeral=True)
    
    # 1. 자판기 메시지 전송
    view = MeuLayout()
    msg = await interaction.channel.send(view=view)
    
    # 2. 백그라운드에서 2분마다 수정을 통해 세션 유지 시작
    bot.loop.create_task(keep_vending_alive(msg))
