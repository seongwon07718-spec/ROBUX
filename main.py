import disnake
from disnake.ext import commands, tasks
import asyncio
import requests
from datetime import datetime, timezone, timedelta

# ============== 중요: 여기에 실제 봇 토큰을 입력해주세요! ==============
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" # <<<<< 이 부분을 자신의 봇 토큰으로 바꿔주세요!

# 봇 생성
intents = disnake.Intents.default()
intents.message_content = True # 만약 메시지 내용을 읽는 기능이 필요하다면 활성화 (현재 코드에는 불필요)
bot = commands.Bot(command_prefix="!", intents=intents)

# UTC+9 (한국 표준시) 타임존 설정
KST = timezone(timedelta(hours=9))

# ============== 실시간 USD/KRW 환율 가져오는 함수 ==============
async def get_usd_krw_rate():
    """frankfurter.app API를 사용하여 1 USD의 KRW 환율을 가져옵니다."""
    try:
        # frankfurter.app은 무료이며 API 키 없이 사용 가능합니다. (rate limit 고려)
        response = requests.get("https://api.frankfurter.app/latest?from=USD&to=KRW")
        response.raise_for_status() # HTTP 오류가 발생하면 예외를 발생시킴
        data = response.json()
        
        # 'rates' 딕셔너리에서 'KRW' 값 추출
        rate = data.get("rates", {}).get("KRW")

        if rate:
            # 소수점 둘째 자리까지 표시하고 천 단위 구분 기호와 'KRW'를 붙여 보기 좋게 포맷합니다.
            return f"{rate:,.2f} KRW"
        else:
            return "환율 조회 불가"
    except requests.exceptions.RequestException as e:
        print(f"USD/KRW 환율을 가져오는 중 오류 발생: {e}")
        return "환율 조회 오류"

# ============== 임베드 및 자동 업데이트 뷰 정의 ==============
class PurchasePanel(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # timeout=None 으로 설정하여 봇이 재시작되어도 뷰가 유지될 수 있도록 합니다.
        self._price_update_time = datetime.now(KST) # 실제 환율 API를 마지막으로 호출한 시간
        self.last_api_price_str = "환율을 가져오는 중..." # 마지막으로 API에서 가져온 환율 값
        self.message = None # 임베드 메시지를 참조할 변수 (나중에 메시지를 편집하기 위함)
        
        # 갱신 태스크 시작 (10초마다 임베드 수정)
        self.updater.start() 
        # 환율 API 호출 태스크 시작 (60초마다 환율 데이터 업데이트)
        self.price_fetcher.start()
        
        print("PurchasePanel 뷰가 초기화되었습니다.")

    def create_embed(self, current_price_display_str: str) -> disnake.Embed:
        """현재 환율과 갱신 시간을 포함하는 임베드를 생성합니다."""
        embed = disnake.Embed(
            title="매입하기",
            color=disnake.Color.blue() # 원하는 색상으로 변경 가능
        )
        embed.add_field(name="1 USD 실시간 환율", value=current_price_display_str, inline=False)
        
        # 마지막 갱신 시간 계산 (API 호출 시간 기준)
        now = datetime.now(KST)
        time_diff = now - self._price_update_time
        seconds_ago = int(time_diff.total_seconds())

        embed.add_field(name="마지막 갱신", value=f"{seconds_ago}초 전 (환율은 60초마다 API 갱신)", inline=False)
        embed.set_footer(text=f"데이터 기준 시각: {self._price_update_time.strftime('%Y-%m-%d %H:%M:%S KST')}")
        return embed

    @tasks.loop(seconds=10) # 10초마다 이 작업을 실행하여 '몇 초 전' 업데이트
    async def updater(self):
        """임베드 메시지를 갱신합니다. (주로 '마지막 갱신' 필드 업데이트)"""
        if self.message: # message가 할당되어 있어야만 업데이트를 시도합니다.
            # print(f"임베드 자동 업데이트 시작 (10초 주기): {datetime.now(KST).strftime('%H:%M:%S')}")
            
            # price_fetcher에서 업데이트된 self.last_api_price_str 사용
            new_embed = self.create_embed(self.last_api_price_str)
            
            try:
                await self.message.edit(embed=new_embed, view=self)
                # print(f"임베드가 성공적으로 업데이트되었습니다. 다음 업데이트: 10초 후")
            except disnake.errors.NotFound:
                print("메시지를 찾을 수 없어 업데이트 실패. 메시지가 삭제되었을 수 있습니다.")
                self.updater.stop() # 메시지가 삭제되었다면 더 이상 업데이트하지 않습니다.
                self.price_fetcher.stop() # 가격 패쳐도 중지
            except Exception as e:
                print(f"임베드 업데이트 중 예상치 못한 오류 발생: {e}")
        # else:
        #     print("message 객체가 할당되지 않아 10초 주기 업데이트 건너뛰기.")

    @updater.before_loop
    async def before_updater(self):
        """updater 작업이 시작되기 전에 봇이 준비될 때까지 기다립니다."""
        await bot.wait_until_ready()
        print("매입 패널 자동 업데이트 작업 (10초 주기)이 시작됩니다.")

    @tasks.loop(seconds=60) # 60초마다 실제 환율 API를 호출하여 데이터 갱신
    async def price_fetcher(self):
        """USD/KRW 환율을 주기적으로 가져와 저장합니다."""
        print(f"환율 API 호출 시작 (60초 주기): {datetime.now(KST).strftime('%H:%M:%S')}")
        self.last_api_price_str = await get_usd_krw_rate()
        self._price_update_time = datetime.now(KST) # API 호출 성공 시간 기록
        print(f"환율 데이터 갱신 완료: {self.last_api_price_str}")

    @price_fetcher.before_loop
    async def before_price_fetcher(self):
        """price_fetcher 작업이 시작되기 전에 봇이 준비될 때까지 기다립니다."""
        await bot.wait_until_ready()
        print("환율 API 호출 작업 (60초 주기)이 시작됩니다.")
        # 봇 시작 시 한 번은 즉시 환율을 가져옵니다.
        self.last_api_price_str = await get_usd_krw_rate()
        self._price_update_time = datetime.now(KST)
        print(f"초기 환율 데이터 가져옴: {self.last_api_price_str}")


# ============== 봇 이벤트 및 명령어 ==============
@bot.event
async def on_ready():
    print(f"봇 '{bot.user}'이(가) 준비되었습니다!")
    # 봇이 시작될 때 뷰를 한 번만 인스턴스화하고 저장합니다.
    global purchase_panel_view
    purchase_panel_view = PurchasePanel()

# /매입패널 슬래시 명령어
@bot.slash_command(name="매입패널", description="매입 패널 임베드를 표시하고 실시간 USD 환율을 보여줍니다.")
async def purchase_panel_command(interaction: disnake.ApplicationCommandInteraction):
    """
    매입 패널 임베드를 생성하고, 메시지 참조를 뷰에 할당합니다.
    """
    # 현재 저장된 환율 정보를 사용하여 임베드를 생성합니다.
    initial_embed = purchase_panel_view.create_embed(purchase_panel_view.last_api_price_str)

    # 임베드를 메시지로 보내고, 전송된 메시지 객체를 뷰에 저장합니다.
    # 이렇게 해야 뷰의 updater 작업이 이 메시지를 수정할 수 있습니다.
    await interaction.response.send_message(embed=initial_embed, view=purchase_panel_view)
    purchase_panel_view.message = await interaction.original_response() # original_response()를 통해 Message 객체 획득

    print(f"'/매입패널' 명령어가 실행되었습니다. 메시지 ID: {purchase_panel_view.message.id}")

# 봇 실행
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
