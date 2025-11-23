import disnake
from disnake.ext import commands, tasks
import asyncio
import requests
from datetime import datetime, timezone, timedelta

# ============== 중요: 여기에 실제 봇 토큰을 입력해주세요! ==============
# 실제 프로젝트에서는 .env 파일을 사용하여 토큰을 관리하는 것이 좋습니다.
# 예시: BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
# 지금은 요청에 따라 코드 내부에 직접 명시합니다.
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" # <<<<< 이 부분을 자신의 봇 토큰으로 바꿔주세요!

# 봇 생성
bot = commands.Bot(command_prefix="!", intents=disnake.Intents.default())

# UTC+9 (한국 표준시) 타임존 설정
KST = timezone(timedelta(hours=9))

# ==================== 실시간 환율 가져오는 함수 ====================
async def get_btc_krw_price():
    """CoinGecko API를 사용하여 비트코인-원화 환율을 가져옵니다."""
    try:
        # CoinGecko API의 단순 가격 조회 엔드포인트 사용
        # Rate limits: API 키 없이도 분당 10-50회 호출 가능. 60초마다 갱신이므로 충분합니다.
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=krw")
        response.raise_for_status() # HTTP 오류가 발생하면 예외를 발생시킴
        data = response.json()
        price = data.get("bitcoin", {}).get("krw")

        if price:
            # 천 단위 구분 기호와 'KRW'를 붙여 보기 좋게 포맷합니다.
            return f"{price:,.0f} KRW"
        else:
            return "가격 조회 불가"
    except requests.exceptions.RequestException as e:
        print(f"비트코인 가격을 가져오는 중 오류 발생: {e}")
        return "환율 조회 오류"

# ==================== 임베드 및 자동 업데이트 뷰 정의 ====================
class PurchasePanel(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # timeout=None 으로 설정하여 봇이 재시작되어도 뷰가 유지될 수 있도록 합니다.
        self.last_updated_time = datetime.now(KST) # 마지막 갱신 시간 (한국 표준시)
        self.message = None # 임베드 메시지를 참조할 변수 (나중에 메시지를 편집하기 위함)
        self.updater.start() # 봇이 시작될 때 updater 작업을 시작합니다.
        print("PurchasePanel 뷰가 초기화되었습니다.")

    def create_embed(self, current_price_str: str) -> disnake.Embed:
        """현재 환율과 갱신 시간을 포함하는 임베드를 생성합니다."""
        embed = disnake.Embed(
            title="매입하기",
            color=disnake.Color.blue() # 원하는 색상으로 변경 가능
        )
        embed.add_field(name="실시간 환율", value=current_price_str, inline=False)
        
        # 마지막 갱신 시간 계산
        now = datetime.now(KST)
        time_diff = now - self.last_updated_time
        seconds_ago = int(time_diff.total_seconds())

        embed.add_field(name="마지막 갱신", value=f"{seconds_ago}초 전 (60초마다 갱신)", inline=False)
        embed.set_footer(text=f"데이터 기준 시각: {now.strftime('%Y-%m-%d %H:%M:%S KST')}")
        return embed

    @tasks.loop(seconds=60) # 60초마다 이 작업을 실행합니다.
    async def updater(self):
        """임베드 메시지를 갱신합니다."""
        if self.message: # message가 할당되어 있어야만 업데이트를 시도합니다.
            print(f"임베드 자동 업데이트 시작: {datetime.now(KST).strftime('%H:%M:%S')}")
            current_price_str = await get_btc_krw_price()
            new_embed = self.create_embed(current_price_str)
            
            try:
                # 원본 메시지를 새 임베드와 함께 수정합니다.
                await self.message.edit(embed=new_embed, view=self)
                self.last_updated_time = datetime.now(KST) # 갱신 시간 업데이트
                print(f"임베드가 성공적으로 업데이트되었습니다. 다음 업데이트: 60초 후")
            except disnake.errors.NotFound:
                print("메시지를 찾을 수 없어 업데이트 실패. 메시지가 삭제되었을 수 있습니다.")
                self.updater.stop() # 메시지가 삭제되었다면 더 이상 업데이트하지 않습니다.
            except Exception as e:
                print(f"임베드 업데이트 중 예상치 못한 오류 발생: {e}")
        else:
            print("message 객체가 할당되지 않아 업데이트 건너뛰기.")


    @updater.before_loop
    async def before_updater(self):
        """updater 작업이 시작되기 전에 봇이 준비될 때까지 기다립니다."""
        await bot.wait_until_ready()
        print("매입 패널 자동 업데이트 작업이 시작됩니다.")

    # (선택 사항) 새로고침 버튼 추가
    @disnake.ui.button(label="수동 새로고침", style=disnake.ButtonStyle.green, custom_id="manual_refresh")
    async def refresh_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        """사용자가 직접 새로고침 버튼을 눌렀을 때 임베드를 갱신합니다."""
        await interaction.response.defer() # 상호작용에 즉시 응답하여 '로딩 중...' 표시를 제거
        print(f"수동 새로고침 요청: {interaction.user.name} at {datetime.now(KST).strftime('%H:%M:%S')}")

        current_price_str = await get_btc_krw_price()
        new_embed = self.create_embed(current_price_str)
        
        await interaction.edit_original_response(embed=new_embed, view=self)
        self.last_updated_time = datetime.now(KST) # 갱신 시간 업데이트
        print("임베드가 수동으로 새로고침되었습니다.")


# ==================== 봇 이벤트 및 명령어 ====================
@bot.event
async def on_ready():
    print(f"봇 '{bot.user}'이(가) 준비되었습니다!")
    # 봇이 시작될 때 뷰를 한 번만 인스턴스화하고 저장합니다.
    global purchase_panel_view
    purchase_panel_view = PurchasePanel()

# /매입패널 슬래시 명령어
@bot.slash_command(name="매입패널", description="매입 패널 임베드를 표시하고 실시간 환율을 보여줍니다.")
async def purchase_panel_command(interaction: disnake.ApplicationCommandInteraction):
    """
    매입 패널 임베드를 생성하고, 메시지 참조를 뷰에 할당합니다.
    """
    # 최초 환율 정보를 가져옵니다.
    initial_price_str = await get_btc_krw_price()
    initial_embed = purchase_panel_view.create_embed(initial_price_str)

    # 임베드를 메시지로 보내고, 전송된 메시지 객체를 뷰에 저장합니다.
    # 이렇게 해야 뷰의 updater 작업이 이 메시지를 수정할 수 있습니다.
    message = await interaction.response.send_message(embed=initial_embed, view=purchase_panel_view)
    purchase_panel_view.message = await message.original_response() # original_response()를 통해 Message 객체 획득

    print(f"'/매입패널' 명령어가 실행되었습니다. 메시지 ID: {purchase_panel_view.message.id}")

# 봇 실행
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
