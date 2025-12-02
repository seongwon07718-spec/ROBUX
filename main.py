import discord
from discord.ext import commands
from discord import app_commands
import requests
from discord import PartialEmoji, ui

TOKEN = ''
GUILD_ID = 1323599222423031902  # 서버 ID를 입력하세요
ALLOWED_USER_IDS = {1402654236570812467}  # 허용된 사용자 ID 목록
FEE_RATE = 0.025  # 2.5%

# 필요한 intents 설정
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

# 봇 설정
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'봇이 준비되었습니다. {bot.user}로 로그인했습니다.')
    activity = discord.Game(name="(24) BITHUMB 코인대행 서비스")  # 여기서 원하는 메시지를 넣으면 됩니다.
    await bot.change_presence(activity=activity)  # 봇의 상태 메시지 설정

@bot.event
async def on_ready():
    print(f'봇이 준비되었습니다. {bot.user}로 로그인했습니다.')
    try:
        activity = discord.Game(name="(24) BITHUMB 코인대행 서비스")
        await bot.change_presence(activity=activity)
        print("상태를 변경했습니다.")
    except Exception as e:
        print(f"상태 변경 중 오류가 발생했습니다: {e}")


def get_kimchi_premium():
    try:
        upbit_price = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC").json()[0]['trade_price']
        binance_price = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT").json()['price']
        binance_price = float(binance_price) * requests.get("https://api.exchangerate-api.com/v4/latest/USD").json()['rates']['KRW']
        kimchi_premium = ((upbit_price - binance_price) / binance_price) * 100
        return kimchi_premium / 100
    except:
        return 0.05  # 기본값 5%

intents = discord.Intents.default()
intents.message_content = True  # 메시지 내용 접근 활성화

def get_exchange_rate():
    """실시간 달러-원 환율을 가져오는 함수"""
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD").json()
        return response['rates']['KRW']
    except:
        return 1450  # 기본 환율 (예비 값)

def calculate_fees(amount, is_dollar=False):
    kimchi_premium = get_kimchi_premium()
    exchange_rate = get_exchange_rate()
    
    if is_dollar:
        amount = amount * exchange_rate  # 달러 -> 원화 변환
    
    amount_needed = amount / (1 - FEE_RATE - kimchi_premium)  # 필요한 충전 금액
    amount_after_fee = amount * (1 - FEE_RATE - kimchi_premium)  # 수수료 제외 후 받을 금액
    
    return round(amount_needed, 2), round(amount_after_fee, 2)

intents = discord.Intents.default()
intents.message_content = True  # 메시지 내용 접근 활성화

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands.')
    except Exception as e:
        print(f'Error syncing commands: {e}')
    
    channel = bot.get_channel(1445431156043550730)  # 채널 ID를 입력하세요
    if channel:
        embed = discord.Embed(title="계산기", description="**아래 버튼을 눌러 이용해주세요**", color=0xffffff)
        embed.set_footer(text="계산 중 약간의 오차가 발생할 수 있습니다.")
        view = FeeView()
        await channel.send(embed=embed, view=view)

class FeeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # 버튼이 영구적으로 유지되도록 timeout 제거

    custom_emoji1 = PartialEmoji(name="calculate", id=1441604996519956554)

    @discord.ui.button(label="원화", style=discord.ButtonStyle.gray, emoji=custom_emoji1)
    async def calculate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FeeModal(False))
    
    @discord.ui.button(label="달러", style=discord.ButtonStyle.gray, emoji=custom_emoji1)
    async def calculate_dollar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FeeModal(True))

class FeeModal(discord.ui.Modal, title="수수료 계산"):
    def __init__(self, is_dollar: bool):
        super().__init__()
        self.is_dollar = is_dollar

        # 금액 입력 필드를 동적으로 설정
        if self.is_dollar:
            self.amount = discord.ui.TextInput(
                label="달러", 
                placeholder="계산할 금액을 달러 기준으로 입력해주세요", 
                required=True
            )
        else:
            self.amount = discord.ui.TextInput(
                label="원화", 
                placeholder="계산할 금액을 원화 기준으로 입력해주세요", 
                required=True
            )
        
        # 모달에 필드를 추가
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = float(self.amount.value)
            amount_needed, amount_after_fee = calculate_fees(amount, self.is_dollar)
            
            # 계산 결과에 맞춰 단위도 다르게 표시
            embed = discord.Embed(title="수수료 계산 결과", color=0xffffff)
            embed.add_field(name=f"{amount} {'USD' if self.is_dollar else '원'}이 있으면", 
                            value=f"약 {amount_after_fee} 원을 송금할 수 있어요.", inline=False)
            embed.add_field(name=f"{amount_needed} 원이 있으면", 
                            value=f"약 {amount} {'USD' if self.is_dollar else '원'}을 송금할 수 있어요.", inline=False)
            embed.set_footer(text="실시간 김프 값과 1.5% 수수료를 적용하여 계산되었습니다.")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except ValueError:
            await interaction.response.send_message("유효한 금액을 입력해주세요.", ephemeral=True)

bot.run(TOKEN)
