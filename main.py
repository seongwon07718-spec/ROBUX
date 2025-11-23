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
# 만약 메시지 내용을 직접 읽는 기능 (예: 일반 채팅 메시지에서 명령어 분석)이 필요하다면 아래 주석 해제
# intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# UTC+9 (한국 표준시) 타임존 설정
KST = timezone(timedelta(hours=9))

# ============== 실시간 USD/KRW 환율 가져오는 함수 ==============
async def get_usd_krw_rate():
    """
    frankfurter.app API를 사용하여 1 USD의 KRW 환율을 가져옵니다.
    네트워크 문제, API 응답 오류 등 다양한 상황을 처리합니다.
    """
    api_url = "https://api.frankfurter.app/latest?from=USD&to=KRW"
    try:
        print(f"[환율조회] API 요청 시도: {api_url}")
        # 타임아웃을 설정하여 무한 대기를 방지합니다. (예: 10초)
        response = requests.get(api_url, timeout=10) 
        
        print(f"[환율조회] API 응답 상태 코드: {response.status_code}")
        # 응답 텍스트를 일부만 출력하여 너무 길어지는 것을 방지
        print(f"[환율조회] API 응답 텍스트 미리보기: {response.text[:200]}{'...' if len(response.text) > 200 else ''}") 

        response.raise_for_status() # HTTP 오류 (4xx, 5xx)가 발생하면 예외를 발생시킴
        data = response.json()
        
        rate = data.get("rates", {}).get("KRW")

        if rate:
            # 소수점 둘째 자리까지 표시하고 천 단위 구분 기호와 'KRW'를 붙여 포맷합니다.
            return f"{rate:,.2f} KRW"
        else:
            print("[환율조회 오류] API 응답에 'KRW' 환율 데이터가 없습니다.")
            return "환율 조회 실패 (데이터 없음)"
            
    except requests.exceptions.HTTPError as e:
        print(f"[환율조회 오류] HTTP 오류 발생 (상태 코드: {e.response.status_code}): {e}")
        return "환율 조회 실패 (HTTP 오류)"
    except requests.exceptions.ConnectionError as e:
        print(f"[환율조회 오류] API 서버 연결 오류 발생: {e}")
        return "환율 조회 실패 (연결 오류)"
    except requests.exceptions.Timeout as e:
        print(f"[환율조회 오류] API 요청 시간 초과 발생: {e}")
        return "환율 조회 실패 (시간 초과)"
    except requests.exceptions.RequestException as e:
        print(f"[환율조회 오류] 기타 요청 오류 발생: {e}")
        return "환율 조회 실패 (요청 오류)"
    except ValueError as e: # JSON 디코딩 오류 처리
        print(f"[환율조회 오류] API 응답 JSON 파싱 오류 발생: {e}. 응답: {response.text if 'response' in locals() else '없음'}")
        return "환율 조회 실패 (JSON 파싱 오류)"
    except Exception as e:
        print(f"[환율조회 오류] 예상치 못한 오류 발생: {type(e).__name__}: {e}")
        return "환율 조회 실패 (알 수 없는 오류)"

# ============== 임베드 및 자동 업데이트 뷰 정의 ==============
class PurchasePanel(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # timeout=None 설정으로 봇 재시작 후에도 뷰 유지 (영속적인 뷰)
        self._price_fetch_time = datetime.now(KST) # 환율 API를 마지막으로 성공적으로 호출한 시간
        self._current_usd_krw_rate_str = "환율을 가져오는 중..." # API에서 가져온 최신 환율 값 (문자열)
        self.message = None # 임베드 메시지를 참조할 변수 (메시지 편집에 사용)
        
        # 10초마다 임베드 UI를 갱신하는 태스크 시작 (마지막 갱신 시간 'X초 전' 업데이트)
        self.updater.start() 
        # 60초마다 외부 API를 호출하여 최신 환율 데이터를 가져오는 태스크 시작
        self.price_fetcher.start()
        
        print("[PurchasePanel] 뷰가 초기화되었습니다.")

    def create_embed(self) -> disnake.Embed:
        """
        현재 저장된 환율 정보와 갱신 시간을 포함하는 임베드를 생성합니다.
        """
        embed = disnake.Embed(
            title="매입하기",
            color=disnake.Color.blue() # 원하는 색상으로 변경 가능
        )
        embed.add_field(name="1 USD 실시간 환율", value=self._current_usd_krw_rate_str, inline=False)
        
        # 임베드가 표시되는 시점의 현재 시간 (실제 시간 흐름 반영)
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
        """
        임베드 메시지를 갱신합니다. (주로 '마지막 갱신' 필드 업데이트)
        실제 API 호출 없이, 저장된 환율과 현재 시간을 기준으로 UI만 수정합니다.
        """
        if self.message: # 메시지가 전송되어 할당된 경우에만 업데이트
            # print(f"[updater] 임베드 UI 자동 업데이트 시작: {datetime.now(KST).strftime('%H:%M:%S')}")
            
            # 현재 저장된 환율 데이터로 새 임베드를 생성하여 업데이트
            new_embed = self.create_embed()
            
            try:
                await self.message.edit(embed=new_embed, view=self)
                # print(f"[updater] 임베드가 성공적으로 업데이트되었습니다.")
            except disnake.errors.NotFound:
                print("[updater 오류] 메시지를 찾을 수 없어 업데이트 실패. 메시지가 삭제되었을 수 있습니다. Updater 중지.")
                self.updater.stop() 
                self.price_fetcher.stop() # 관련 태스크도 함께 중지
            except Exception as e:
                print(f"[updater 오류] 임베드 UI 업데이트 중 예상치 못한 오류 발생: {e}")

    @updater.before_loop
    async def before_updater(self):
        """updater 작업이 시작되기 전에 봇이 준비될 때까지 기다립니다."""
        await bot.wait_until_ready()
        print("[updater] 매입 패널 자동 업데이트 작업 (10초 주기)이 시작됩니다.")

    @tasks.loop(seconds=60) # 60초마다 실제 환율 API를 호출하여 최신 데이터 가져오기
    async def price_fetcher(self):
        """
        USD/KRW 환율을 주기적으로 외부 API에서 가져와 내부 변수에 저장합니다.
        """
        print(f"[price_fetcher] 환율 API 호출 시작: {datetime.now(KST).strftime('%H:%M:%S')}")
        fetched_rate = await get_usd_krw_rate()
        
        if not fetched_rate.startswith("환율 조회 실패"): # 오류가 아닌 경우에만 갱신
            self._current_usd_krw_rate_str = fetched_rate
            self._price_fetch_time = datetime.now(KST) # API 호출 성공 시간 기록
            print(f"[price_fetcher] 환율 데이터 갱신 완료: {self._current_usd_krw_rate_str}")
        else:
            # API 호출 실패 시 오류 메시지를 저장하여 사용자에게 표시
            self._current_usd_krw_rate_str = fetched_rate
            print(f"[price_fetcher 오류] 환율 데이터 갱신 실패: {fetched_rate}")

    @price_fetcher.before_loop
    async def before_price_fetcher(self):
        """price_fetcher 작업이 시작되기 전에 봇이 준비될 때까지 기다립니다."""
        await bot.wait_until_ready()
        print("[price_fetcher] 환율 API 호출 작업 (60초 주기)이 시작됩니다.")
        # 봇 시작 시 한 번은 즉시 환율을 가져옵니다.
        # 이렇게 하면 `/매입패널` 명령어를 사용하자마자 초기 환율이 표시됩니다.
        await self.price_fetcher() # 첫 호출 실행

# ============== 봇 이벤트 및 명령어 ==============
@bot.event
async def on_ready():
    print(f"봇 '{bot.user}'이(가) 준비되었습니다!")
    # 봇이 시작될 때 PurchasePanel 뷰를 한 번만 인스턴스화하고 전역 변수에 저장합니다.
    # 이렇게 해야 모든 `/매입패널` 명령이 동일한 뷰 인스턴스를 공유하며, tasks.loop가 정상 작동합니다.
    global purchase_panel_view
    purchase_panel_view = PurchasePanel()
    
# /매입패널 슬래시 명령어
@bot.slash_command(name="매입패널", description="매입 패널 임베드를 표시하고 실시간 USD 환율을 보여줍니다.")
async def purchase_panel_command(interaction: disnake.ApplicationCommandInteraction):
    """
    매입 패널 임베드를 생성하고, 메시지 참조를 뷰에 할당합니다.
    """
    # 현재 저장된 환율 정보를 사용하여 임베드를 생성합니다.
    initial_embed = purchase_panel_view.create_embed()

    # 임베드를 메시지로 보내고, 전송된 메시지 객체를 뷰에 저장합니다.
    # 이렇게 해야 뷰의 updater 태스크가 이 메시지를 수정할 수 있습니다.
    await interaction.response.send_message(embed=initial_embed, view=purchase_panel_view)
    purchase_panel_view.message = await interaction.original_response() # Message 객체를 획득

    print(f"'/매입패널' 명령어가 실행되었습니다. 메시지 ID: {purchase_panel_view.message.id}")

# 봇 실행
if __name__ == "__main__":
    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f"봇 실행 중 오류 발생: {e}")
