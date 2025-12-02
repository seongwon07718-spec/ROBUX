import discord
from discord.ext import commands
from discord import app_commands, PartialEmoji, ui
import requests
import asyncio

# --- 설정 변수 ---
TOKEN = ''  # 봇 토큰 입력
# GUILD_ID는 글로벌 명령어 등록을 위해 사용하지 않습니다.
ALLOWED_USER_IDS = {1402654236570812467}  # 슬래시 명령어를 사용할 수 있는 허용된 사용자 ID 목록
FEE_RATE = 0.025  # 2.5% (기본 수수료)
# -----------------

# 필요한 intents 설정
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

# 봇 설정
bot = commands.Bot(command_prefix='!', intents=intents)

# -----------------------------------------------------
# 📚 외부 API 및 계산 로직
# -----------------------------------------------------

def get_exchange_rate():
    """실시간 달러-원 환율을 가져오는 함수"""
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD").json()
        return response['rates']['KRW']
    except:
        return 1300

def get_kimchi_premium():
    """실시간 김치 프리미엄을 가져오는 함수 (소수점 형태)"""
    try:
        upbit_price = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC").json()[0]['trade_price']
        binance_price = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT").json()['price']
        
        exchange_rate = get_exchange_rate()
        
        binance_price_krw = float(binance_price) * exchange_rate
        kimchi_premium = ((upbit_price - binance_price_krw) / binance_price_krw)
        return kimchi_premium
    except Exception as e:
        print(f"김치 프리미엄 계산 오류: {e}")
        return 0.05

def calculate_fees(amount, is_dollar=False):
    """
    수수료를 계산하는 함수. 전역 FEE_RATE을 사용합니다.
    """
    global FEE_RATE
    
    kimchi_premium = get_kimchi_premium()
    exchange_rate = get_exchange_rate()
    
    if is_dollar:
        amount = amount * exchange_rate
    
    total_deduction_rate = FEE_RATE + kimchi_premium
    
    amount_after_fee = amount * (1 - total_deduction_rate)
    amount_needed = amount / (1 - total_deduction_rate)
    
    return round(amount_needed, 2), round(amount_after_fee, 2), kimchi_premium

# -----------------------------------------------------
# 🤖 봇 이벤트 및 슬래시 명령어
# -----------------------------------------------------

@bot.event
async def on_ready():
    print(f'봇이 준비되었습니다. {bot.user}로 로그인했습니다.')
    
    # 상태 메시지 설정
    try:
        activity = discord.Game(name="(24) BITHUMB 코인대행 서비스")
        await bot.change_presence(activity=activity)
        print("상태를 변경했습니다.")
    except Exception as e:
        print(f"상태 변경 중 오류가 발생했습니다: {e}")
        
    # 슬래시 명령어 동기화 (글로벌 명령어는 최대 1시간 소요)
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} global commands.')
    except Exception as e:
        # 이전에 발생했던 403 Forbidden 오류는 대부분 권한 문제입니다. 
        # 글로벌 동기화 시에도 봇에 'applications.commands' 권한이 없으면 발생합니다.
        print(f'Error syncing commands: {e}')

# --- 슬래시 명령어: 임베드 전송 ---
@app_commands.command(name="수수료임베드", description="수수료 계산기 임베드 메시지를 전송합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def fee_embed_command(interaction: discord.Interaction):
    if interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("이 명령어는 허용된 사용자만 사용할 수 있습니다.", ephemeral=True)
        return
    
    embed = discord.Embed(title="💳 수수료 계산기", description="**아래 버튼을 눌러 이용해주세요**", color=0x5865F2)
    embed.set_footer(text="계산 시 실시간 김치 프리미엄 및 현재 설정된 수수료율이 적용됩니다.")
    view = FeeView()
    
    await interaction.response.send_message(embed=embed, view=view)

# --- 슬래시 명령어: 수수료 설정 ---
@app_commands.command(name="수수료설정", description="수수료율을 설정합니다. 예: 0.025 (2.5%)")
@app_commands.checks.has_permissions(administrator=True)
async def fee_set_command(interaction: discord.Interaction, 비율: float):
    global FEE_RATE
    
    if interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("이 명령어는 허용된 사용자만 사용할 수 있습니다.", ephemeral=True)
        return
    
    if 0.0 <= 비율 <= 1.0:
        FEE_RATE = 비율
        percentage = round(비율 * 100, 2)
        await interaction.response.send_message(f"✅ 수수료율을 **{percentage}%** ({비율})로 성공적으로 설정했습니다.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ 수수료율은 0.0과 1.0 (0%와 100%) 사이의 값으로 입력해주세요.", ephemeral=True)

# 슬래시 명령어 글로벌 등록
# (주의: bot.tree.sync() 호출 시 글로벌로 동기화됩니다.)
bot.tree.add_command(fee_embed_command)
bot.tree.add_command(fee_set_command)

# -----------------------------------------------------
# 🖼️ View (버튼) 및 Modal (팝업) 클래스 (이전과 동일)
# -----------------------------------------------------

class FeeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    custom_emoji1 = PartialEmoji(name="calculate", id=1441604996519956554) 

    @discord.ui.button(label="원화", style=discord.ButtonStyle.gray, emoji="🇰🇷")
    async def calculate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FeeModal(False))
    
    @discord.ui.button(label="달러", style=discord.ButtonStyle.gray, emoji="💵")
    async def calculate_dollar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FeeModal(True))

class FeeModal(discord.ui.Modal, title="수수료 계산"):
    def __init__(self, is_dollar: bool):
        super().__init__()
        self.is_dollar = is_dollar

        unit = "USD" if self.is_dollar else "원화"
        self.amount = discord.ui.TextInput(
            label=f"금액 ({unit})", 
            placeholder=f"계산할 금액을 {unit} 기준으로 입력해주세요. (숫자만)", 
            required=True
        )
        
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            amount = float(self.amount.value)
            
            # API 호출이 포함된 함수를 executor에서 실행하여 메인 스레드 블로킹 방지
            amount_needed, amount_after_fee, kimchi_premium = await bot.loop.run_in_executor(
                None, calculate_fees, amount, self.is_dollar
            )
            
            kimchi_premium_percent = round(kimchi_premium * 100, 2)
            fee_rate_percent = round(FEE_RATE * 100, 2)
            
            embed = discord.Embed(title="✅ 수수료 계산 결과", color=0x34A853)
            
            if not self.is_dollar:
                embed.add_field(name=f"💰 충전 금액 기준: **{amount:,} 원**", 
                                value=f"약 **{amount_after_fee:,} 원**을 송금할 수 있어요.", inline=False)
                
                exchange_rate = get_exchange_rate()
                amount_in_usd = round(amount_after_fee / exchange_rate, 2)
                embed.add_field(name="💵 참고 정보",
                                value=f"약 **{amount_in_usd:,} USD**에 해당합니다.", inline=False)
            
            else:
                embed.add_field(name=f"💵 송금 원하는 금액 기준: **{amount:,} USD**", 
                                value=f"이 금액을 받으려면 약 **{amount_needed:,} 원**이 필요합니다.", inline=False)
                
                amount_in_krw = round(amount * get_exchange_rate(), 2)
                embed.add_field(name="💰 참고 정보",
                                value=f"**{amount:,} USD**는 현재 환율로 약 **{amount_in_krw:,} 원**입니다.", inline=False)
            
            embed.set_footer(text=f"현재 김프: {kimchi_premium_percent}% | 설정 수수료: {fee_rate_percent}% | 총 수수료율: {round((FEE_RATE + kimchi_premium) * 100, 2)}%")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.followup.send("⚠️ 유효한 금액을 입력해주세요. (숫자만 입력)", ephemeral=True)
        except Exception as e:
            print(f"모달 제출 중 예기치 않은 오류 발생: {e}")
            await interaction.followup.send("❌ 계산 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", ephemeral=True)

# 봇 실행
bot.run(TOKEN)
