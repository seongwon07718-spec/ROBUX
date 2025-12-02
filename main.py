import discord
from discord.ext import commands
from discord import app_commands, PartialEmoji, ui
import requests
import asyncio

# --- 설정 변수 ---
TOKEN = ''  # 봇 토큰 입력
GUILD_ID = 1323599222423031902  # 서버 ID를 입력하세요 (Integer)
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
        return 1300  # 기본 환율 (예비 값, 1450 대신 현실적인 값으로 변경)

def get_kimchi_premium():
    """실시간 김치 프리미엄을 가져오는 함수 (소수점 형태)"""
    try:
        # 김치 프리미엄 계산 로직은 시간이 걸릴 수 있으므로, 
        # 비동기 환경에서 안전하게 실행되도록 주의해야 합니다.
        upbit_price = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC").json()[0]['trade_price']
        binance_price = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT").json()['price']
        
        # 환율 가져오기
        exchange_rate = get_exchange_rate()
        
        binance_price_krw = float(binance_price) * exchange_rate
        kimchi_premium = ((upbit_price - binance_price_krw) / binance_price_krw)
        return kimchi_premium
    except Exception as e:
        print(f"김치 프리미엄 계산 오류: {e}")
        return 0.05  # 기본값 5%

def calculate_fees(amount, is_dollar=False):
    """
    수수료를 계산하는 함수. 전역 FEE_RATE을 사용합니다.
    주의: 이 함수는 외부 API 호출을 포함하므로 비동기 컨텍스트에서 호출 시 await bot.loop.run_in_executor() 등을 사용하는 것이 안전합니다.
    """
    global FEE_RATE # 전역 변수 사용 명시
    
    kimchi_premium = get_kimchi_premium()
    exchange_rate = get_exchange_rate()
    
    if is_dollar:
        amount = amount * exchange_rate  # 달러 -> 원화 변환
    
    # 필요한 충전 금액 및 수수료 적용 후 받을 금액 계산
    # 수수료율 = FEE_RATE + kimchi_premium
    total_deduction_rate = FEE_RATE + kimchi_premium
    
    # amount_after_fee: 요청한 금액(원화 기준) * (1 - total_deduction_rate)
    amount_after_fee = amount * (1 - total_deduction_rate)
    
    # amount_needed: 송금 후 요청한 금액(원화 기준)을 받기 위해 필요한 충전 금액
    # 필요한 충전 금액 X (1 - total_deduction_rate) = amount
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
        
    # 슬래시 명령어 동기화
    try:
        # 특정 서버(GUILD)에 동기화
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f'Synced {len(synced)} commands to Guild ID {GUILD_ID}.')
    except Exception as e:
        print(f'Error syncing commands: {e}')

# --- 슬래시 명령어: 임베드 전송 ---
@app_commands.command(name="수수료임베드", description="수수료 계산기 임베드 메시지를 전송합니다.")
@app_commands.checks.has_permissions(administrator=True) # 관리자 권한 체크
async def fee_embed_command(interaction: discord.Interaction):
    if interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("이 명령어는 허용된 사용자만 사용할 수 있습니다.", ephemeral=True)
        return
    
    embed = discord.Embed(title="💳 수수료 계산기", description="**아래 버튼을 눌러 이용해주세요**", color=0x5865F2)
    embed.set_footer(text="계산 시 실시간 김치 프리미엄 및 현재 설정된 수수료율이 적용됩니다.")
    view = FeeView()
    
    # 메시지를 보내고 임베드를 전송
    await interaction.response.send_message(embed=embed, view=view)

# --- 슬래시 명령어: 수수료 설정 ---
@app_commands.command(name="수수료설정", description="수수료율을 설정합니다. 예: 0.025 (2.5%)")
@app_commands.checks.has_permissions(administrator=True) # 관리자 권한 체크
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

# 슬래시 명령어 그룹 등록
bot.tree.add_command(fee_embed_command, guild=discord.Object(id=GUILD_ID))
bot.tree.add_command(fee_set_command, guild=discord.Object(id=GUILD_ID))

# -----------------------------------------------------
# 🖼️ View (버튼) 및 Modal (팝업) 클래스
# -----------------------------------------------------

class FeeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # 버튼이 영구적으로 유지되도록 timeout 제거

    # 이모지 ID는 봇이 접근 가능한 서버에 있어야 합니다.
    # 해당 이모지 ID가 봇이 접근 가능한 서버에 있는지 확인하세요.
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

        # 금액 입력 필드를 동적으로 설정
        unit = "USD" if self.is_dollar else "원화"
        self.amount = discord.ui.TextInput(
            label=f"금액 ({unit})", 
            placeholder=f"계산할 금액을 {unit} 기준으로 입력해주세요. (숫자만)", 
            required=True
        )
        
        # 모달에 필드를 추가
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        # ⚠️ 중요: 상호작용 타임아웃 방지를 위해 defer 사용
        # 계산에 시간이 걸릴 수 있으므로, 봇이 처리 중임을 Discord에 알려줍니다.
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            amount = float(self.amount.value)
            
            # API 호출이 포함된 함수를 executor에서 실행하여 메인 스레드 블로킹 방지
            amount_needed, amount_after_fee, kimchi_premium = await bot.loop.run_in_executor(
                None, calculate_fees, amount, self.is_dollar
            )
            
            kimchi_premium_percent = round(kimchi_premium * 100, 2)
            fee_rate_percent = round(FEE_RATE * 100, 2)
            
            # 계산 결과에 맞춰 단위도 다르게 표시
            embed = discord.Embed(title="✅ 수수료 계산 결과", color=0x34A853)
            
            # 원화 입력 시:
            if not self.is_dollar:
                embed.add_field(name=f"💰 충전 금액 기준: **{amount:,} 원**", 
                                value=f"약 **{amount_after_fee:,} 원**을 송금할 수 있어요.", inline=False)
                
                # 금액이 크면 달러 환산 금액도 보여줌 (참고용)
                exchange_rate = get_exchange_rate()
                amount_in_usd = round(amount_after_fee / exchange_rate, 2)
                embed.add_field(name="💵 참고 정보",
                                value=f"약 **{amount_in_usd:,} USD**에 해당합니다.", inline=False)
            
            # 달러 입력 시:
            else:
                embed.add_field(name=f"💵 송금 원하는 금액 기준: **{amount:,} USD**", 
                                value=f"이 금액을 받으려면 약 **{amount_needed:,} 원**이 필요합니다.", inline=False)
                
                amount_in_krw = round(amount * get_exchange_rate(), 2)
                embed.add_field(name="💰 참고 정보",
                                value=f"**{amount:,} USD**는 현재 환율로 약 **{amount_in_krw:,} 원**입니다.", inline=False)
            
            embed.set_footer(text=f"현재 김프: {kimchi_premium_percent}% | 설정 수수료: {fee_rate_percent}% | 총 수수료율: {round((FEE_RATE + kimchi_premium) * 100, 2)}%")
            
            # defer로 연장된 상호작용에 후속 응답 전송
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.followup.send("⚠️ 유효한 금액을 입력해주세요. (숫자만 입력)", ephemeral=True)
        except Exception as e:
            print(f"모달 제출 중 예기치 않은 오류 발생: {e}")
            await interaction.followup.send("❌ 계산 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", ephemeral=True)

# 봇 실행
bot.run(TOKEN)
