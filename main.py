import disnake
from disnake.ext import commands, tasks
import asyncio
import requests
from datetime import datetime, timezone, timedelta

# ============== 중요: 여기에 실제 봇 토큰을 입력해주세요! ==============
# 실제 서비스에서는 .env 파일을 사용하여 토큰을 관리하는 것이 보안상 매우 중요합니다!
# 현재 요청에 따라 코드 내부에 직접 명시하지만, 실제 배포 시에는 반드시 변경을 권장합니다.
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" # <<<<< 이 부분을 자신의 봇 토큰으로 바꿔주세요!

# 봇 생성 (disnake.Intents.default()는 대부분의 이벤트에 충분하지만, 특정 기능 필요 시 추가)
intents = disnake.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# UTC+9 (한국 표준시) 타임존 설정
KST = timezone(timedelta(hours=9))

# ============== 업비트 API에서 USDT/KRW 실시간 환율(가격) 가져오는 함수 ==============
async def get_usdt_krw_price_from_upbit():
    """
    업비트 API를 사용하여 USDT(테더)의 원화(KRW) 실시간 거래 가격을 가져옵니다.
    이 가격은 업비트 내에서 1 USD에 상응하는 가치로 간주될 수 있습니다.
    """
    # 업비트 티커 조회 API: KRW-USDT 마켓 조회
    # 공식 문서: https://docs.upbit.com/reference/%EC%8B%9C%EC%84%B8-%EC%A0%95%EB%B3%B4
    api_url = "https://api.upbit.com/v1/ticker?markets=KRW-USDT"
    try:
        print(f"[업비트 USDT 조회] API 요청 시도: {api_url}")
        response = requests.get(api_url, timeout=10) 
        
        print(f"[업비트 USDT 조회] API 응답 상태 코드: {response.status_code}")
        print(f"[업비트 USDT 조회] API 응답 텍스트 미리보기: {response.text[:200]}{'...' if len(response.text) > 200 else ''}") 

        response.raise_for_status() # HTTP 오류 (4xx, 5xx)가 발생하면 예외를 발생시킴
        data = response.json()
        
        if data and isinstance(data, list) and len(data) > 0:
            trade_price = data[0].get("trade_price") # 현재가
            
            if trade_price is not None:
                # 소수점 둘째 자리까지 표시하고 천 단위 구분 기호와 'KRW'를 붙여 포맷합니다.
                # USDT 가격은 원화 환율처럼 소수점 이하까지 중요합니다.
                return f"{trade_price:,.2f} KRW" 
            else:
                print("[업비트 USDT 조회 오류] 'trade_price' 데이터가 없습니다.")
                return "1 USD(USDT 기준) 조회 실패 (데이터 없음)"
        else:
            print("[업비트 USDT 조회 오류] API 응답에 KRW-USDT 시장 데이터가 없습니다.")
            return "1 USD(USDT 기준) 조회 실패 (시장 없음)"
            
    except requests.exceptions.HTTPError as e:
        print(f"[업비트 USDT 조회 오류] HTTP 오류 발생 (상태 코드: {e.response.status_code}): {e}")
        return "1 USD(USDT 기준) 조회 실패 (HTTP 오류)"
    except requests.exceptions.ConnectionError as e:
        print(f"[업비트 USDT 조회 오류] API 서버 연결 오류 발생: {e}")
        return "1 USD(USDT 기준) 조회 실패 (연결 오류)"
    except requests.exceptions.Timeout as e:
        print(f"[업비트 USDT 조회 오류] API 요청 시간 초과 발생: {e}")
        return "1 USD(USDT 기준) 조회 실패 (시간 초과)"
    except requests.exceptions.RequestException as e:
        print(f"[업비트 USDT 조회 오류] 기타 요청 오류 발생: {e}")
        return "1 USD(USDT 기준) 조회 실패 (요청 오류)"
    except ValueError as e: # JSON 디코딩 오류 처리
        print(f"[업비트 USDT 조회 오류] API 응답 JSON 파싱 오류 발생: {e}. 응답: {response.text if 'response' in locals() else '없음'}")
        return "1 USD(USDT 기준) 조회 실패 (JSON 파싱 오류)"
    except Exception as e:
        print(f"[업비트 USDT 조회 오류] 예상치 못한 오류 발생: {type(e).__name__}: {e}")
        return "1 USD(USDT 기준) 조회 실패 (알 수 없는 오류)"

# ============== 임베드 및 자동 업데이트 뷰 정의 ==============
class PurchasePanel(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 
        self._price_fetch_time = datetime.now(KST) # 업비트 API를 마지막으로 성공적으로 호출한 시간
        # 초기 메시지를 "환율을 가져오는 중..."으로 설정하여 시작 시 사용자에게 안내
        self._current_usdt_krw_price_str = "환율을 가져오는 중..." 
        self.message = None # 임베드 메시지 참조 변수
        
        self.updater.start() 
        self.price_fetcher.start()
        
        print("[PurchasePanel] 뷰가 초기화되었습니다.")

    def create_embed(self) -> disnake.Embed:
        """
        현재 저장된 USDT/KRW 가격 정보와 갱신 시간을 포함하는 임베드를 생성합니다.
        """
        embed = disnake.Embed(
            title="매입하기",
            color=disnake.Color.blue() 
        )
        # 필드 이름을 '1 USD (USDT 기준) 실시간 환율'로 명확히 표시
        embed.add_field(name="1 USD (USDT 기준) 실시간 환율", value=self._current_usdt_krw_price_str, inline=False)
        
        now = datetime.now(KST)
        time_diff = now - self._price_fetch_time
        seconds_ago = int(time_diff.total_seconds())

        embed.add_field(
            name="마지막 갱신", 
            value=f"{seconds_ago}초 전 (환율 데이터는 60초마다 API 갱신)", 
            inline=False
        )
        embed.set_footer(text=f"데이터 기준 시각: {self._price_fetch_time.strftime('%Y-%m-%d %H:%M:%S KST')}")
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

    @tasks.loop(seconds=60) # 60초마다 실제 업비트 API를 호출하여 최신 USDT 가격 데이터 가져오기
    async def price_fetcher(self):
        print(f"[price_fetcher] 업비트 USDT API 호출 시작: {datetime.now(KST).strftime('%H:%M:%S')}")
        fetched_price = await get_usdt_krw_price_from_upbit()
        
        if not fetched_price.startswith("1 USD(USDT 기준) 조회 실패"): # 오류가 아닌 경우에만 갱신
            self._current_usdt_krw_price_str = fetched_price
            self._price_fetch_time = datetime.now(KST) # API 호출 성공 시간 기록
            print(f"[price_fetcher] USDT 가격 데이터 갱신 완료: {self._current_usdt_krw_price_str}")
        else:
            self._current_usdt_krw_price_str = fetched_price # 오류 메시지를 저장하여 사용자에게 표시
            print(f"[price_fetcher 오류] USDT 가격 데이터 갱신 실패: {fetched_price}")

    @price_fetcher.before_loop
    async def before_price_fetcher(self):
        await bot.wait_until_ready()
        print("[price_fetcher] 업비트 USDT API 호출 작업 (60초 주기)이 시작됩니다.")
        # 봇 시작 시 한 번은 즉시 가격을 가져와 초기 값을 설정합니다.
        await self.price_fetcher() 

# ============== 봇 이벤트 및 명령어 ==============
@bot.event
async def on_ready():
    print(f"봇 '{bot.user}'이(가) 준비되었습니다!")
    global purchase_panel_view
    purchase_panel_view = PurchasePanel()
    
# /매입패널 슬래시 명령어
@bot.slash_command(name="매입패널", description="매입 패널 임베드를 표시하고 업비트 USDT/KRW 실시간 환율을 보여줍니다.")
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
