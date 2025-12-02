import discord
from discord.ext import commands
from discord import app_commands
import requests
import json
import os # config.json 파일 관리를 위해 필요합니다.

# ====================================================================
# 봇 설정 및 전역 변수
# ====================================================================

# 튜어오오오옹님의 요청대로, TOKEN은 .env 파일을 사용하지 않고 직접 코드에 입력합니다.
# **주의: 이 토큰은 외부에 노출되지 않도록 각별히 주의해주세요.**
TOKEN = '' # 여기에 봇 토큰을 직접 입력해주세요! (예: "YOUR_BOT_TOKEN_HERE")

# GUILD_ID를 설정하지 않고 전역 동기화를 수행합니다.
# ALLOWED_USER_IDS는 슬래시 커맨드의 관리자 권한과는 별개로, 
# 특정 버튼이나 명령어의 사용 권한을 부여할 때 사용됩니다.
ALLOWED_USER_IDS = {502862517043724288, 1402654236570812467}  # 허용된 사용자 ID 목록

# 설정 파일 경로
CONFIG_FILE = 'config.json'

# 초기 수수료율 설정 (config.json이 없거나 읽을 수 없을 경우 사용될 기본값)
FEE_RATE = 0.015  # 1.5%

# ====================================================================
# 설정 파일 로드 및 저장 함수
# ====================================================================

def load_config():
    global FEE_RATE
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            FEE_RATE = config.get('fee_rate', 0.015)
            print(f"config.json에서 수수료율을 {FEE_RATE*100:.1f}%로 불러왔습니다.")
    else:
        # 파일이 없으면 기본값으로 초기화 후 저장
        save_config({'fee_rate': FEE_RATE})
        print(f"config.json 파일이 없어 기본 수수료율 {FEE_RATE*100:.1f}%로 새 파일을 생성했습니다.")


def save_config(config_data):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        print(f"수수료율 {config_data['fee_rate']*100:.1f}%를 config.json에 저장했습니다.")
    except Exception as e:
        print(f"config.json 저장 중 오류가 발생했습니다: {e}")

# ====================================================================
# 헬퍼 함수들 (환율, 김프, 수수료 계산)
# ====================================================================

def get_kimchi_premium():
    """김치 프리미엄을 계산하여 반환합니다. 오류 시 기본값 5%를 반환합니다."""
    try:
        upbit_response = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC").json()
        if not upbit_response: # 응답이 비어있을 경우 예외 처리
            raise ValueError("Upbit API 응답이 비어있습니다.")
        upbit_price = upbit_response[0]['trade_price']

        binance_response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT").json()
        if 'price' not in binance_response: # 응답에 'price' 키가 없을 경우 예외 처리
             raise ValueError("Binance API 응답에 'price'가 없습니다.")
        binance_price_usd = float(binance_response['price'])
        
        exchange_rate_response = requests.get("https://api.exchangerate-api.com/v4/latest/USD").json()
        if 'rates' not in exchange_rate_response or 'KRW' not in exchange_rate_response['rates']:
            raise ValueError("ExchangeRate API 응답에 'KRW' 환율 정보가 없습니다.")
        dollar_to_krw_rate = exchange_rate_response['rates']['KRW']
        
        binance_price_krw = binance_price_usd * dollar_to_krw_rate
        kimchi_premium = ((upbit_price - binance_price_krw) / binance_price_krw) # 소수점 형태
        return kimchi_premium
    except Exception as e:
        print(f"김치 프리미엄 계산 중 오류 발생: {e}")
        return 0.05  # 오류 발생 시 기본값 5%

def get_exchange_rate():
    """실시간 달러-원 환율을 가져오는 함수"""
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD").json()
        return response['rates']['KRW']
    except Exception as e:
        print(f"환율 정보 가져오는 중 오류 발생: {e}")
        return 1450  # 기본 환율 (예비 값)

def calculate_fees(amount, is_dollar=False):
    """
    주어진 금액에 수수료와 김프를 적용하여 필요한 금액과 받을 금액을 계산합니다.
    FEE_RATE는 전역 변수에서 가져옵니다.
    """
    global FEE_RATE # 전역 FEE_RATE 사용
    kimchi_premium = get_kimchi_premium()
    exchange_rate = get_exchange_rate()
    
    if is_dollar:
        amount_krw = amount * exchange_rate  # 달러 -> 원화 변환
    else:
        amount_krw = amount
    
    # 송금 시 필요한 금액: (받고자 하는 금액) / (1 - 수수료율 - 김프)
    amount_needed_for_transfer = amount_krw / (1 - FEE_RATE - kimchi_premium)
    
    # 송금 받은 후 최종 금액: (가지고 있는 금액) * (1 - 수수료율 - 김프)
    amount_after_fee_deduction = amount_krw * (1 - FEE_RATE - kimchi_premium) 
    
    # 반환 값은 원화 기준 (is_dollar가 True일 때 amount_krw에 이미 달러-원 변환이 적용됨)
    return round(amount_needed_for_transfer, 2), round(amount_after_fee_deduction, 2)

# ====================================================================
# Discord UI 구성 요소 (Modal, View)
# ====================================================================

class FeeModal(discord.ui.Modal, title="수수료 계산"):
    """
    수수료 계산을 위한 모달입니다. 원화 또는 달러 입력을 받습니다.
    """
    def __init__(self, is_dollar: bool):
        super().__init__()
        self.is_dollar = is_dollar

        label = "달러" if self.is_dollar else "원화"
        placeholder = f"계산할 금액을 {label} 기준으로 입력해주세요!"
        
        self.amount = discord.ui.TextInput(
            label=label, 
            placeholder=placeholder, 
            required=True
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = float(self.amount.value)
            
            # calculate_fees 함수에서 is_dollar에 따라 amount가 원화로 처리되거나, 
            # 원화 입력을 받은 amount가 그대로 사용됩니다.
            amount_needed_krw, amount_after_fee_krw = calculate_fees(amount, self.is_dollar)
            
            # 여기서 중요한 것은 amount_needed_krw와 amount_after_fee_krw는 항상 '원화' 단위라는 것입니다.
            # 사용자에게 입력된 amount의 단위는 그대로 표시해주어야 합니다.

            embed = discord.Embed(title="💰 수수료 계산 결과 💰", color=discord.Color.gold())
            
            # 첫 번째 필드는 입력받은 단위와 금액으로 시작하여 '수수료 제외 후 받을 금액'이 원화로 얼마인지 보여줍니다.
            embed.add_field(
                name=f"{amount:,.2f} {'달러(USD)' if self.is_dollar else '원(KRW)'}이 있다면", 
                value=f"최종적으로 약 `{amount_after_fee_krw:,.2f}` 원을 송금 받을 수 있습니다.", 
                inline=False
            )
            # 두 번째 필드는 특정 금액을 원화로 받고 싶을 때 얼마가 필요한지 보여줍니다.
            embed.add_field(
                name=f"원하는 금액을 `{amount:,.2f}` {'달러(USD)' if self.is_dollar else '원(KRW)'}만큼 받는다면", 
                value=f"약 `{amount_needed_krw:,.2f}` 원이 필요합니다.", 
                inline=False
            )

            global FEE_RATE # 현재 설정된 수수료율을 사용
            embed.set_footer(text=f"실시간 김프 값과 {FEE_RATE*100:.1f}% 수수료가 적용되어 계산되었습니다.")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ 유효한 숫자를 입력해주세요.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ 계산 중 오류가 발생했습니다: {e}", ephemeral=True)

class CalculatorView(discord.ui.View):
    """
    슬래시 커맨드 `/수수료계산`을 통해 표시될 버튼들을 담는 View입니다.
    """
    def __init__(self, allowed_user_ids: set):
        super().__init__(timeout=None)
        self.allowed_user_ids = allowed_user_ids

    @discord.ui.button(label="원화로 계산", style=discord.ButtonStyle.primary, emoji="💸")
    async def calculate_krw_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FeeModal(False))
    
    @discord.ui.button(label="달러로 계산", style=discord.ButtonStyle.success, emoji="💵")
    async def calculate_dollar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FeeModal(True))
    
    @discord.ui.button(label="현재 환율 및 김프", style=discord.ButtonStyle.secondary, emoji="📊")
    async def show_exchange_rate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.allowed_user_ids:
            await interaction.response.send_message("❌ 이 버튼은 관리자 전용 기능입니다.", ephemeral=True)
            return
        
        exchange_rate = get_exchange_rate()
        kimchi_premium = get_kimchi_premium() * 100  # % 단위 변환
        
        embed = discord.Embed(title="📊 실시간 환율 및 김치 프리미엄", color=discord.Color.green())
        embed.add_field(name="💲 USD/KRW 환율", value=f"`{exchange_rate:,.2f}` 원", inline=False)
        embed.add_field(name="🔥 김치 프리미엄", value=f"`{kimchi_premium:.2f}`%", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ====================================================================
# Discord 봇 및 Cog 정의
# ====================================================================

# 필요한 intents 설정
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True # 메시지 내용 접근 활성화

# 봇 설정
bot = commands.Bot(command_prefix='!', intents=intents)

class Calculator(commands.Cog):
    """
    수수료 계산 및 설정 관련 명령어를 포함하는 Cog입니다.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /수수료계산 슬래시 커맨드
    @app_commands.command(name="수수료계산", description="수수료를 포함한 송금 금액을 계산합니다.")
    async def calculate_fee_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="❄ 수수료 계산기", 
            description="계산할 금액의 단위를 선택해주세요!", 
            color=discord.Color.blue()
        )
        embed.set_footer(text="계산 중 약간의 오차가 발생할 수 있습니다.")
        
        # CalculatorView를 인스턴스화할 때 ALLOWED_USER_IDS를 전달합니다.
        view = CalculatorView(ALLOWED_USER_IDS) 
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True) # ephemeral=True로 메시지를 보낸 사람에게만 보이도록

    # /수수료설정 슬래시 커맨드 (관리자 전용)
    @app_commands.command(name="수수료설정", description="봇의 수수료율을 설정합니다. (관리자 전용)")
    @app_commands.describe(new_fee_rate="새로운 수수료율 (예: 0.015는 1.5%)")
    async def set_fee_command(self, interaction: discord.Interaction, new_fee_rate: float):
        if interaction.user.id not in ALLOWED_USER_IDS:
            await interaction.response.send_message("❌ 이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return

        if not (0 <= new_fee_rate < 0.1): # 0% ~ 10% 범위로 제한 (원하는대로 조절 가능)
            await interaction.response.send_message("❌ 수수료율은 0%에서 10% 사이의 값으로 설정해야 합니다. (예: 0.015)", ephemeral=True)
            return

        global FEE_RATE
        FEE_RATE = new_fee_rate
        
        # 설정 파일에 저장
        config = {'fee_rate': FEE_RATE}
        save_config(config)

        await interaction.response.send_message(
            f"✅ 수수료율이 `{FEE_RATE*100:.1f}%`로 성공적으로 변경되었습니다.", 
            ephemeral=True
        )

# ====================================================================
# 봇 이벤트 핸들러
# ====================================================================

@bot.event
async def on_ready():
    """봇이 준비되었을 때 실행되는 함수입니다."""
    print(f'봇이 준비되었습니다. {bot.user}로 로그인했습니다.')
    try:
        # Cog 로드
        await bot.add_cog(Calculator(bot))

        # 봇 상태 메시지 설정
        activity = discord.Game(name="튜어오오오옹님의 프로젝트")
        await bot.change_presence(activity=activity)
        print("봇 상태 메시지를 설정했습니다.")

        # 슬래시 커맨드 전역 동기화 (GUILD_ID 없이 모든 서버에 동기화)
        synced = await bot.tree.sync() # <--- GUILD_ID 인자 제거
        print(f'모든 길드에 {len(synced)}개의 슬래시 커맨드를 동기화했습니다.')
        print(f"전역 동기화는 Discord API의 지연으로 최대 1시간까지 걸릴 수 있습니다.")
        print(f"커맨드가 바로 보이지 않더라도 잠시 기다려주세요! Discord 앱을 재시작해보는 것도 도움이 될 수 있습니다.")


    except Exception as e:
        print(f"봇 초기화 중 오류가 발생했습니다: {e}")

# ====================================================================
# 봇 실행
# ====================================================================

if __name__ == '__main__':
    load_config() # 봇 시작 시 설정 파일 로드
    bot.run(TOKEN)
