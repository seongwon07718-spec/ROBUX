import disnake
from disnake.ext import commands, tasks
import requests
from datetime import datetime, timezone, timedelta
import asyncio # 비동기 대기 로직을 위해 필요

# ============== 중요: 여기에 실제 봇 토큰을 입력해주세요! ==============
# 실제 서비스에서는 .env 파일을 사용하여 관리하는 것이 보안상 매우 중요합니다!
# 현재 요청에 따라 코드 내부에 직접 명시하지만, 실제 배포 시에는 반드시 변경을 권장합니다.
BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN_HERE"  # <<<<< 이 부분을 자신의 디스코드 봇 토큰으로 바꿔주세요!

# 봇 생성 (disnake.Intents.default()는 대부분의 이벤트에 충분)
intents = disnake.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# UTC+9 (한국 표준시) 타임존 설정
KST = timezone(timedelta(hours=9))

# Frankfurter.app 환율 API URL
FRANKFURTER_API_URL = "https://api.frankfurter.app/latest?from=USD&to=KRW"

# API 호출 제한 방어를 위한 플래그 (쿨다운 시간)
last_api_error_time = None
ERROR_COOLDOWN_SECONDS = 300 # 오류 발생 시 5분 동안 API 호출 시도 안함 (429 에러 방어)

async def get_usd_krw_rate_frankfurter():
    """
    frankfurter.app API를 사용하여 USD/KRW 환율을 가져옵니다.
    네트워크 문제, API 응답 오류 등 다양한 상황을 처리합니다.
    """
    global last_api_error_time
    
    # 이전에 오류가 발생하여 쿨다운 상태인 경우
    if last_api_error_time and (datetime.now() - last_api_error_time).total_seconds() < ERROR_COOLDOWN_SECONDS:
        remaining_time = int(ERROR_COOLDOWN_SECONDS - (datetime.now() - last_api_error_time).total_seconds())
        print(f"[Frankfurter API] 오류 쿨다운 중. {remaining_time}초 후 재시도 가능.")
        return f"환율 조회 지연 (오류 쿨다운: {remaining_time}초 남음)"

    try:
        print(f"[Frankfurter API] 요청 시도: {FRANKFURTER_API_URL}")
        response = requests.get(FRANKFURTER_API_URL, timeout=15) # 타임아웃 15초로 좀 더 여유있게 설정
        
        print(f"[Frankfurter API] 응답 상태 코드: {response.status_code}")
        # 응답 텍스트를 일부만 출력하여 너무 길어지는 것을 방지
        print(f"[Frankfurter API] 응답 텍스트 미리보기: {response.text[:200]}{'...' if len(response.text) > 200 else ''}") 

        response.raise_for_status() # HTTP 오류 (4xx, 5xx)가 발생하면 예외를 발생시킴
        data = response.json()
        
        rate = data.get("rates", {}).get("KRW")

        if rate:
            last_api_error_time = None # 성공 시 오류 플래그 초기화
            # 소수점 둘째 자리까지 표시하고 천 단위 구분 기호와 'KRW'를 붙여 포맷합니다.
            return f"{rate:,.2f} KRW"
        else:
            print("[Frankfurter API 오류] 응답에 'KRW' 환율 데이터가 없습니다.")
            last_api_error_time = datetime.now() # 오류 발생 시 시간 기록
            return "환율 조회 실패 (데이터 없음)"
            
    except requests.exceptions.HTTPError as e:
        last_api_error_time = datetime.now() # 오류 발생 시 시간 기록
        print(f"[Frankfurter API 오류] HTTP 오류 발생 (상태 코드: {e.response.status_code}): {e}")
        return f"환율 조회 실패 (HTTP 오류: {e.response.status_code})"
    except requests.exceptions.ConnectionError as e:
        last_api_error_time = datetime.now() # 오류 발생 시 시간 기록
        print(f"[Frankfurter API 오류] 서버 연결 오류 발생: {e}")
        return "환율 조회 실패 (연결 오류)"
    except requests.exceptions.Timeout as e:
        last_api_error_time = datetime.now() # 오류 발생 시 시간 기록
        print(f"[Frankfurter API 오류] 요청 시간 초과 발생: {e}")
        return "환율 조회 실패 (시간 초과)"
    except requests.exceptions.RequestException as e:
        last_api_error_time = datetime.now() # 오류 발생 시 시간 기록
        print(f"[Frankfurter API 오류] 기타 요청 오류 발생: {e}")
        return "환율 조회 실패 (요청 오류)"
    except ValueError as e: # JSON 디코딩 오류 처리
        last_api_error_time = datetime.now() # 오류 발생 시 시간 기록
        print(f"[Frankfurter API 오류] JSON 파싱 오류 발생: {e}. 응답: {response.text if 'response' in locals() else '없음'}")
        return "환율 조회 실패 (JSON 파싱 오류)"
    except Exception as e:
        last_api_error_time = datetime.now() # 오류 발생 시 시간 기록
        print(f"[Frankfurter API 오류] 예상치 못한 오류 발생: {type(e).__name__}: {e}")
        return "환율 조회 실패 (알 수 없는 오류)"

# ============== 임베드 및 자동 업데이트 뷰 정의 ==============
class PurchasePanel(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 
        self._price_fetch_time = datetime.now(KST) # API를 마지막으로 성공적으로 호출한 시간
        self._current_usd_krw_rate_str = "환율을 가져오는 중..." # 최신 환율 값 (문자열)
        self.message = None # 임베드 메시지 참조 변수
        
        self.updater.start() 
        self.price_fetcher.start()
        
        print("[PurchasePanel] 뷰가 초기화되었습니다.")

    def create_embed(self) -> disnake.Embed:
        """
        현재 저장된 USD/KRW 환율 정보와 갱신 시간을 포함하는 임베드를 생성합니다.
        """
        embed = disnake.Embed(
            title="매입하기",
            color=disnake.Color.blue() 
        )
        embed.add_field(name="1 USD 실시간 환율 (Frankfurter.app 기준)", value=self._current_usd_krw_rate_str, inline=False)
        
        now = datetime.now(KST)
        time_diff = now - self._price_fetch_time
        seconds_ago = int(time_diff.total_seconds())

        embed.add_field(
            name="마지막 갱신", 
            value=f"{seconds_ago}초 전 (환율 데이터는 60초마다 API 갱신)", 
            inline=False
        )
        embed.set_footer(text=f"데이터 기준 시각: {self._price_fetch_time.strftime('%Y-%m-%d %H:%M:%S')} KST")
        return embed

    @tasks.loop(seconds=10) # 10초마다 UI의 'X초 전' 부분을 업데이트
    async def updater(self):
        if self.message: 
            new_embed = self.create_embed()
            
            try:
                await self.message.edit(embed=new_embed, view=self)
            except disnake.errors.NotFound:
                print("[updater 오류] 메시지를 찾을 수 없어 업데이트 실패. 메시지가 삭제되었을 수 있습니다. Updater 및 Price Fetcher 중지.")
                self.updater.stop() 
                self.price_fetcher.stop() 
            except Exception as e:
                print(f"[updater 오류] 임베드 UI 업데이트 중 예상치 못한 오류 발생: {e}")

    @updater.before_loop
    async def before_updater(self):
        await bot.wait_until_ready()
        print("[updater] 매입 패널 자동 업데이트 작업 (10초 주기)이 시작됩니다.")

    @tasks.loop(seconds=60) # 60초마다 실제 API를 호출하여 최신 환율 데이터 가져오기
    async def price_fetcher(self):
        print(f"[price_fetcher] Frankfurter API 호출 시작: {datetime.now(KST).strftime('%H:%M:%S')}")
        fetched_rate = await get_usd_krw_rate_frankfurter()
        
        # 오류 메시지로 시작하지 않는 경우에만 갱신
        if not fetched_rate.startswith("환율 조회 실패") and not fetched_rate.startswith("환율 조회 지연"): 
            self._current_usd_krw_rate_str = fetched_rate
            self._price_fetch_time = datetime.now(KST) # API 호출 성공 시 시간 기록
            print(f"[price_fetcher] Frankfurter 환율 데이터 갱신 완료: {self._current_usd_krw_rate_str}")
        else:
            self._current_usd_krw_rate_str = fetched_rate # 오류 메시지를 저장하여 사용자에게 표시
            print(f"[price_fetcher 오류] Frankfurter 환율 데이터 갱신 실패/지연: {fetched_rate}")

    @price_fetcher.before_loop
    async def before_price_fetcher(self):
        await bot.wait_until_ready()
        print("[price_fetcher] Frankfurter API 호출 작업 (60초 주기)이 시작됩니다.")
        await self.price_fetcher() # 봇 시작 시 한 번은 즉시 환율을 가져옵니다.

# ============== 봇 이벤트 및 명령어 ==============
@bot.event
async def on_ready():
    print(f"봇 '{bot.user}'이(가) 준비되었습니다!")
    global purchase_panel_view
    purchase_panel_view = PurchasePanel()
    
# /매입패널 슬래시 명령어
@bot.slash_command(name="매입패널", description="Frankfurter.app 기준 1 USD 실시간 환율을 보여줍니다.")
async def purchase_panel_command(interaction: disnake.ApplicationCommandInteraction):
    """
    매입 패널 임베드를 생성하고, 메시지 참조를 뷰에 할당합니다.
    """
    initial_embed = purchase_panel_view.create_embed()

    await interaction.response.send_message(embed=initial_embed, view=purchase_panel_view)
    purchase_panel_view.message = await interaction.original_response() 

    print(f"'/매입패널' 명령어가 실행되었습니다. 메시지 ID: {purchase_panel_view.message.id}")

# 봇 실행
if __name__ == "__main__":
    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f"봇 실행 중 오류 발생: {e}")
