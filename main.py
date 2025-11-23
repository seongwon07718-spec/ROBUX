import disnake
from disnake.ext import commands, tasks
import requests
from datetime import datetime, timezone, timedelta

# 봇 토큰 (자신의 토큰으로 변경하세요)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# 한국 표준시 타임존 설정
KST = timezone(timedelta(hours=9))

bot = commands.Bot(command_prefix="!", intents=disnake.Intents.default())

# 야후파이낸스 USDKRW 환율 API URL
YAHOO_FINANCE_API_URL = (
    "https://query1.finance.yahoo.com/v7/finance/quote?symbols=USDKRW=X"
)

async def get_usd_krw_rate_yahoo():
    """
    야후파이낸스 API를 통해 USD/KRW 환율을 실시간으로 가져옵니다.
    실패 시 상세 로그를 출력하고, 사용자가 볼 수 있게 오류 메시지를 반환합니다.
    """
    try:
        response = requests.get(YAHOO_FINANCE_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # JSON 구조 확인 후 환율 추출
        result = data.get("quoteResponse", {}).get("result", [])
        if not result:
            print("[환율조회 오류] 야후파이낸스 응답에 결과 없음")
            return "환율 조회 실패 (결과 없음)"
        
        usdkrw_data = result[0]
        price = usdkrw_data.get("regularMarketPrice")  # 실시간 환율
        if price is None:
            print("[환율조회 오류] 환율 데이터 없음")
            return "환율 조회 실패 (가격 없음)"
        
        # 소수점 둘째자리까지 표현, 천 단위 콤마 포함
        return f"{price:,.2f} KRW"
    except requests.exceptions.HTTPError as e:
        print(f"[환율조회 HTTP 오류] {e}")
        return "환율 조회 실패 (HTTP 오류)"
    except requests.exceptions.ConnectionError as e:
        print(f"[환율조회 연결 오류] {e}")
        return "환율 조회 실패 (연결 오류)"
    except requests.exceptions.Timeout as e:
        print(f"[환율조회 시간초과] {e}")
        return "환율 조회 실패 (시간 초과)"
    except Exception as e:
        print(f"[환율조회 알수없는 오류] {e}")
        return "환율 조회 실패 (알 수 없는 오류)"

class PurchasePanel(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self._last_update_time = datetime.now(KST)
        self._current_rate = "환율을 가져오는 중..."
        self.message = None
        
        self.updater.start()
        self.price_fetcher.start()
    
    def create_embed(self):
        embed = disnake.Embed(
            title="매입하기",
            color=disnake.Color.blue()
        )
        embed.add_field(name="1 USD 실시간 환율 (야후파이낸스 기준)", value=self._current_rate, inline=False)
        
        now = datetime.now(KST)
        seconds_passed = int((now - self._last_update_time).total_seconds())
        embed.add_field(name="마지막 갱신", value=f"{seconds_passed}초 전 (60초마다 환율 갱신)", inline=False)
        embed.set_footer(text=f"데이터 기준 시각: {self._last_update_time.strftime('%Y-%m-%d %H:%M:%S KST')}")
        return embed
    
    @tasks.loop(seconds=10)
    async def updater(self):
        if self.message:
            try:
                await self.message.edit(embed=self.create_embed(), view=self)
            except disnake.errors.NotFound:
                self.updater.stop()
                self.price_fetcher.stop()
            except Exception as e:
                print(f"[업데이트 오류] {e}")

    @updater.before_loop
    async def before_updater(self):
        await bot.wait_until_ready()
    
    @tasks.loop(seconds=60)
    async def price_fetcher(self):
        rate = await get_usd_krw_rate_yahoo()
        self._current_rate = rate
        self._last_update_time = datetime.now(KST)
        print(f"[환율 갱신] {self._current_rate} at {self._last_update_time.strftime('%H:%M:%S')}")
    
    @price_fetcher.before_loop
    async def before_price_fetcher(self):
        await bot.wait_until_ready()
        await self.price_fetcher()

@bot.event
async def on_ready():
    print(f"{bot.user} 로그인 완료")
    global purchase_panel_view
    purchase_panel_view = PurchasePanel()

@bot.slash_command(name="매입패널", description="야후파이낸스 기준 1 USD 실시간 환율을 보여줍니다.")
async def purchase_panel_command(interaction: disnake.ApplicationCommandInteraction):
    embed = purchase_panel_view.create_embed()
    await interaction.response.send_message(embed=embed, view=purchase_panel_view)
    purchase_panel_view.message = await interaction.original_response()

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
