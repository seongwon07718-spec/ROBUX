# main.py
import disnake
from disnake.ext import commands, tasks
import asyncio
import json
import time
from datetime import datetime, timedelta
import hashlib
import hmac
import urllib.parse
import aiohttp # 비동기 HTTP 요청을 위해 사용
import pytz # 시간대 처리를 위해 사용

# data/database.py 파일을 임포트
from data.database import get_db_connection, init_db 

# --- 설정 (🚨🚨 보안 경고: 민감 정보를 직접 코드에 넣는 것은 좋지 않습니다! 🚨🚨) ---
# 실제 사용 시에는 환경 변수 또는 안전한 설정 파일 사용을 강력히 권장합니다.
BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN_HERE" # 🚨 디스코드 봇 토큰 (필수)
MEXC_API_KEY = "YOUR_MEXC_API_KEY_HERE" # 🚨 MEXC API Key (필수)
MEXC_SECRET_KEY = "YOUR_MEXC_SECRET_KEY_HERE" # 🚨 MEXC Secret Key (필수)
ADMIN_CHANNEL_ID = YOUR_ADMIN_CHANNEL_ID # 🚨 관리자 로그 채널 ID (숫자만, 필수)
ADMIN_USER_ID = 1402654236570812467 # 🚨 관리자 사용자 ID (튜어오오오옹님의 ID, 필수)

# 한국수출입은행 환율 API (사용 전에 KEY를 발급받아 교체해주세요)
EXIMBANK_API_URL = "https://www.koreaexim.go.kr/site/program/financial/exchangeJSON?authkey={authkey}&searchdate={date}&data=AP01"
EXIMBANK_API_KEY = "YOUR_EXIMBANK_API_KEY_HERE" # 🚨 한국수출입은행 API Key (필수)

# 봇 초기화
intents = disnake.Intents.default()
intents.message_content = True 
intents.dm_messages = True 
intents.members = True # 유저에게 DM을 보내기 위해 필요

bot = commands.Bot(command_prefix="!", intents=intents)

# 코인 선택 드롭다운 메뉴 (지원할 코인 목록)
SUPPORTED_COINS = ["USDT", "BTC", "ETH", "LTC", "BNB", "TRON"]

MEXC_API_HOST = "api.mexc.com"

# --- MEXC API 서명 생성 함수 (MEXC Spot API v3 문서 기반) ---
def get_mexc_signature(secret_key: str, method: str, path: str, params: dict) -> str:
    """
    MEXC API 요청에 필요한 HMAC SHA256 서명을 생성합니다.
    MEXC Spot API v3 문서의 서명 규칙을 정확히 따릅니다.
    (https://mexc-api.github.io/apidocs/spot_v3_en/#signed)
    """
    # 딕셔너리 정렬 후 URL 인코딩하여 쿼리 문자열 생성
    sorted_params = sorted(params.items())
    query_string = urllib.parse.urlencode(sorted_params)
    
    string_to_sign = f"{method.upper()}{MEXC_API_HOST}{path}{query_string}"
    
    # Secret Key로 HMAC-SHA256 서명 생성
    h = hmac.new(secret_key.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha256)
    return h.hexdigest()

# --- 도우미 함수 ---
async def get_current_krw_rate(currency_code: str) -> float | None:
    """지정된 통화의 현재 KRW 환율을 한국수출입은행 API에서 가져옵니다."""
    kst = pytz.timezone('Asia/Seoul')
    
    async def fetch_rate_for_date(target_date: str) -> float | None:
        api_url = EXIMBANK_API_URL.format(authkey=EXIMBANK_API_KEY, date=target_date)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if not data: # 데이터가 없는 경우 (예: 공휴일)
                            return None
                        for item in data:
                            # 통화 코드 매핑 (USDT는 USD와 동일하게 취급)
                            if currency_code == "USDT":
                                target_currency = "USD"
                            else:
                                target_currency = currency_code
                            
                            if item['cur_unit'].replace(' ', '') == target_currency:
                                # deal_bas_r (매매기준율) 사용, 쉼표 제거 후 float 변환
                                return float(item['deal_bas_r'].replace(',', ''))
                        print(f"환율 정보를 가져왔으나 {currency_code}를 찾지 못했습니다.")
                        return None
                    else:
                        print(f"환율 API 요청 실패 (HTTP {response.status}): {await response.text()}")
                        return None
        except aiohttp.ClientError as e:
            print(f"환율 API 통신 중 오류 발생: {e}")
            return None
        except Exception as e:
            print(f"환율 정보 처리 중 예기치 않은 오류 발생: {e}")
            return None

    # 한국 시간 기준으로 현재 날짜 설정
    today_kst = datetime.now(kst)
    # 평일 11시 이후부터 당일 데이터, 그 전에는 전날 데이터 우선 조회 (API 업데이트 시각 고려)
    fetch_date = today_kst.strftime("%Y%m%d")
    
    rate = await fetch_rate_for_date(fetch_date)
    if rate is None: # 오늘 데이터가 없으면 어제 데이터 시도
        yesterday_kst = today_kst - timedelta(days=1)
        fetch_date = yesterday_kst.strftime("%Y%m%d")
        rate = await fetch_rate_for_date(fetch_date)
        if rate is not None:
            print(f"Info: {currency_code} 환율, 오늘 데이터 없어 어제({fetch_date}) 데이터 사용.")
    
    if rate is None:
        print(f"Error: {currency_code}의 유효한 환율 정보를 가져올 수 없습니다.")
    
    return rate

async def get_mexc_coin_price_usd(coin_symbol: str) -> float | None:
    """MEXC API에서 특정 코인의 USDT(USD) 가격을 가져옵니다."""
    try:
        symbol = f"{coin_symbol}USDT" # BTCUSDT, ETHUSDT 등
        url = f"https://{MEXC_API_HOST}/api/v3/ticker/price?symbol={symbol}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status() # HTTP 오류가 있으면 예외 발생
                data = await response.json()
                if 'price' in data:
                    return float(data['price'])
                print(f"MEXC {symbol} 가격 정보에 'price' 필드가 없습니다: {data}")
                return None
    except aiohttp.ClientError as e:
        print(f"MEXC 가격 API 통신 중 오류 발생: {e}")
        return None
    except Exception as e:
        print(f"MEXC {symbol} 가격 정보를 가져오는 중 오류 발생: {e}")
        return None

async def get_mexc_deposit_history(coin_symbol: str, expected_txid: str) -> dict | None:
    """
    MEXC API를 통해 특정 코인의 입금 내역을 조회하고,
    제출된 TXID와 일치하는 입금을 감지합니다.
    """
    print(f"MEXC 입금 내역 확인 시작: 코인={coin_symbol}, 예상 TXID={expected_txid}")
    
    path = "/api/v3/capital/deposit/hisrec"
    timestamp = str(int(time.time() * 1000))
    params = {
        "coin": coin_symbol,
        "status": 1, # 1: 성공 (MEXC 문서 기준)
        "timestamp": timestamp,
        "recvWindow": "5000" # 5000ms (5초) 이내 유효한 요청
    }
    
    # 서명 생성
    signature = get_mexc_signature(MEXC_SECRET_KEY, "GET", MEXC_API_HOST, path, params)

    headers = {
        "X-MEXC-APIKEY": MEXC_API_KEY,
        "X-MEXC-SIGNATURE": signature,
        "X-MEXC-REQUEST-SOURCE": "spot" 
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://{MEXC_API_HOST}{path}", headers=headers, params=params) as response:
                response.raise_for_status() # HTTP 상태 코드 200번대가 아니면 예외 발생
                deposits = await response.json()
                
                # API 응답에서 TXID 일치하는 입금 내역 찾기
                for deposit in deposits:
                    if deposit.get('txId') == expected_txid and deposit.get('status') == 1: # 1은 입금 완료
                        print(f"MEXC API에서 입금 감지 성공: {deposit}")
                        return {
                            'txid': deposit.get('txId'),
                            'amount': float(deposit.get('amount')),
                            'coin': deposit.get('coin'),
                            'address': deposit.get('toAddress') # MEXC API 필드명 'toAddress'
                        }
                print(f"MEXC API에서 TXID '{expected_txid}'에 해당하는 완료된 입금 내역을 찾을 수 없습니다.")
                return None
    except aiohttp.ClientResponseError as e:
        print(f"MEXC 입금 내역 API 응답 오류 (HTTP {e.status}): {await e.response.text()}")
        return None
    except aiohttp.ClientError as e:
        print(f"MEXC 입금 내역 API 통신 중 오류 발생: {e}")
        return None
    except Exception as e:
        print(f"MEXC 입금 내역 처리 중 예기치 않은 오류 발생: {e}")
        return None


# --- 봇 준비 완료 이벤트 ---
@bot.event
async def on_ready():
    print(f"로그인 봇: {bot.user} (ID: {bot.user.id})")
    mexc_deposit_monitor.start() # 입금 감지 작업을 시작합니다.
    print("MEXC 입금 모니터링 태스크 시작.")

# --- Background Task: MEXC 입금 모니터링 ---
@tasks.loop(seconds=30) # 30초마다 한 번씩 입금 내역 확인
async def mexc_deposit_monitor():
    print("MEXC 입금 모니터링 태스크 실행...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 'txid_submitted' 상태인 트랜잭션들을 조회합니다.
    # 관리자 채널에 메시지가 보내져서 admin_msg_id가 null이 아닌 경우만 처리.
    cursor.execute("""
        SELECT transaction_id, user_id, coin_type, txid, discord_admin_message_id
        FROM transactions
        WHERE status = 'txid_submitted' AND discord_admin_message_id IS NOT NULL
    """)
    pending_transactions = cursor.fetchall()
    
    for tx_id, user_id, coin_type, user_submitted_txid, admin_msg_id in pending_transactions:
        try:
            detected_deposit = await get_mexc_deposit_history(coin_type, user_submitted_txid)
            
            if detected_deposit:
                # 입금 감지 성공!
                print(f"입금 감지 성공! TXID: {detected_deposit['txid']}, 금액: {detected_deposit['amount']} {detected_deposit['coin']}")
                
                # KRW 환산
                coin_price_usd = await get_mexc_coin_price_usd(coin_type)
                krw_rate_usd = await get_current_krw_rate("USD")
                
                actual_krw_amount = 0.0
                if coin_type == "USDT": 
                    if krw_rate_usd:
                        actual_krw_amount = detected_deposit['amount'] * krw_rate_usd
                elif coin_price_usd and krw_rate_usd:
                    actual_krw_amount = detected_deposit['amount'] * coin_price_usd * krw_rate_usd
                else:
                    print(f"Warning: {coin_type}의 시세 또는 환율 정보를 가져오지 못하여 KRW 환산 불가 (트랜잭션 {tx_id}).")

                # DB 업데이트: 실제 입금량과 KRW 환산액, 상태 업데이트
                cursor.execute("""
                    UPDATE transactions SET 
                        status = 'deposit_detected', 
                        amount_coin = ?, 
                        amount_krw = ?,
                        deposit_txid = ?
                    WHERE transaction_id = ?
                """, (detected_deposit['amount'], actual_krw_amount, detected_deposit['txid'], tx_id))
                conn.commit()

                # 관리자 채널 메시지 업데이트 (버튼은 유지)
                admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
                if admin_channel and admin_msg_id:
                    try:
                        admin_message = await admin_channel.fetch_message(admin_msg_id)
                        original_embed = admin_message.embeds[0] if admin_message.embeds else disnake.Embed()
                        
                        # 새로운 임베드 생성 및 기존 정보 복사
                        new_embed = disnake.Embed(
                            title="✅ 코인 매입 입금 감지 완료 (확인 필요) ✅",
                            description="사용자의 입금 내역이 감지되었습니다. 최종 확인 후 처리해주세요.",
                            color=disnake.Color.orange()
                        )
                        # 기존 필드 내용을 가져와 새 임베드에 추가 (특정 필드는 업데이트)
                        for field in original_embed.fields:
                            # 기존에 '예상 매입 금액'이 있으면 새 값으로 교체
                            if field.name == "매입 금액 (KRW)":
                                new_embed.add_field(name="매입 금액 (KRW)", value=f"{actual_krw_amount:,.2f}원 (감지됨)", inline=True)
                            elif field.name == "유저가 제출한 TXID": # 제출 TXID와 감지된 TXID 함께 표시
                                new_embed.add_field(name="유저가 제출한 TXID", value=field.value, inline=False)
                                new_embed.add_field(name="감지된 입금 TXID", value=f"```\n{detected_deposit['txid']}\n```", inline=False)
                            else:
                                new_embed.add_field(name=field.name, value=field.value, inline=field.inline)

                        new_embed.add_field( # 실제 입금 코인량 필드 추가
                            name="실제 입금 코인량",
                            value=f"{detected_deposit['amount']:.4f} {detected_deposit['coin']}",
                            inline=True
                        )
                        new_embed.set_footer(text=f"트랜잭션 ID: {tx_id} | 상태: 입금 감지됨")

                        await admin_message.edit(embed=new_embed, view=AdminActionView(tx_id)) # 버튼 뷰는 그대로 유지
                        print(f"관리자 채널 메시지 {admin_msg_id} (트랜잭션 ID: {tx_id}) 업데이트 완료.")
                    except disnake.NotFound:
                        print(f"Warning: 관리자 메시지 {admin_msg_id} (트랜잭션 ID: {tx_id})를 찾을 수 없습니다. (삭제되었을 수 있음)")
                    except Exception as e:
                        print(f"관리자 채널 메시지 업데이트 중 오류 발생: {e}")
                else:
                    print(f"Warning: 관리자 채널 {ADMIN_CHANNEL_ID} 또는 메시지 ID {admin_msg_id}를 찾을 수 없습니다.")

            # 이미 'deposit_detected' 상태인데 API에서 아직 감지가 안된 경우 (API 문제 또는 입금 지연)
            elif cursor.execute("SELECT status FROM transactions WHERE transaction_id = ?", (tx_id,)).fetchone()[0] == 'deposit_detected':
                pass # 이미 감지됨 상태이면 특별히 할 일 없음
                
        except Exception as e:
            print(f"입금 모니터링 중 예기치 않은 오류 발생 (트랜잭션 ID: {tx_id}): {e}")
    
    conn.close()
    print("MEXC 입금 모니터링 태스크 완료.")


# --- /매입임베드 슬래시 명령어 ---
@bot.slash_command(name="매입임베드", description="코인 매입을 시작하는 임베드를 전송합니다.")
async def create_purchase_embed(inter: disnake.ApplicationCommandInteraction):
    if inter.author.id != ADMIN_USER_ID:
        await inter.response.send_message("이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
        return

    embed = disnake.Embed(
        title="✨ 코인 매입 서비스 ✨",
        description="안전하고 신속하게 코인을 매입해 드립니다!\n아래 '매입하기' 버튼을 눌러 매입 과정을 시작하세요.",
        color=disnake.Color.blue()
    )
    embed.set_footer(text="궁금한 점은 관리자에게 문의해주세요.")
    
    class PurchaseStartView(disnake.ui.View):
        def __init__(self):
            super().__init__(timeout=300)
        
        @disnake.ui.button(label="매입하기", style=disnake.ButtonStyle.green, custom_id="purchase_start_button")
        async def purchase_start_button_callback(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
            await inter.response.send_modal(modal=AccountSetupModal(inter.author.id))

    await inter.response.send_message(embed=embed, view=PurchaseStartView())

# --- 계좌 설정 모달 (구매 시작 시) ---
class AccountSetupModal(disnake.ui.Modal):
    def __init__(self, user_id: int):
        self.user_id = user_id
        components = [
            disnake.ui.TextInput(
                label="입금자명 (예: 홍길동)",
                placeholder="입금자명을 정확히 입력해주세요.",
                custom_id="depositor_name",
                style=disnake.TextInputStyle.short,
                max_length=50,
            ),
            disnake.ui.TextInput(
                label="계좌번호 (예: 1001-XXXX-XXXX 정)",
                placeholder="예: 토스뱅크 1001-1234-5678 정",
                custom_id="account_number",
                style=disnake.TextInputStyle.short,
                max_length=50,
            ),
        ]
        super().__init__(title="매입 계좌 정보 입력", custom_id=f"account_setup_modal_{user_id}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        depositor_name = inter.text_values["depositor_name"].strip()
        account_number = inter.text_values["account_number"].strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # users 테이블에 사용자 정보 저장 또는 업데이트
            cursor.execute("INSERT OR REPLACE INTO users (user_id, depositor_name, account_number) VALUES (?, ?, ?)",
                           (self.user_id, depositor_name, account_number))
            conn.commit()
            print(f"사용자 {self.user_id} 계좌 정보 저장/업데이트 완료.")
        except Exception as e:
            print(f"사용자 {self.user_id} 계좌 정보 DB 저장 중 오류 발생: {e}")
            await inter.response.send_message("계좌 정보 저장 중 오류가 발생했습니다. 다시 시도해 주세요.", ephemeral=True)
            conn.close()
            return
        finally:
            conn.close()

        await inter.response.send_message("계좌 정보가 성공적으로 저장되었습니다. 이제 매입할 코인을 선택해 주세요!", ephemeral=True)
        await self.send_coin_selection_dm(inter.author)

    async def send_coin_selection_dm(self, user: disnake.User):
        embed = disnake.Embed(
            title="코인 매입 - 코인 선택 🪙",
            description=f"안녕하세요, {user.display_name}님! 매입을 원하시는 코인을 아래 드롭다운에서 선택해 주세요.",
            color=disnake.Color.purple()
        )
        embed.set_footer(text="이 메시지에서 코인을 선택해 주세요.")
        try:
            dm_channel = await user.create_dm()
            await dm_channel.send(embed=embed, view=CoinSelectionView(user.id))
            print(f"사용자 {user.id}에게 코인 선택 DM 전송 완료.")
        except disnake.Forbidden:
            print(f"Warning: 사용자 {user.name} ({user.id})에게 DM 전송 실패 (DM 차단).")
            # DM이 차단된 경우를 대비한 추가 안내 (이메랄 메시지로 전송)
            await user.send(f"{user.mention}님, DM이 차단되어 매입 진행 메시지를 보낼 수 없습니다. DM을 허용해 주세요.", ephemeral=False)
        except Exception as e:
            print(f"사용자 {user.id}에게 DM 전송 중 오류 발생: {e}")

# --- 코인 선택 드롭다운 ---
class CoinSelectionView(disnake.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=600)
        self.user_id = user_id
        
        options = [
            disnake.SelectOption(label=coin, value=coin) for coin in SUPPORTED_COINS
        ]
        
        self.add_item(disnake.ui.Select(
            placeholder="매입할 코인을 선택하세요...",
            custom_id="coin_selector_dropdown",
            options=options,
            min_values=1,
            max_values=1
        ))

    @disnake.ui.select(custom_id="coin_selector_dropdown")
    async def select_coin_callback(self, select: disnake.ui.Select, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True) # 상호작용 딜레이 방지
        selected_coin = select.values[0]

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT address FROM user_coin_addresses WHERE user_id = ? AND coin_type = ?",
                           (self.user_id, selected_coin))
            result = cursor.fetchone()
            
            if result:
                coin_address = result[0]
                # 새 매입 트랜잭션 DB에 기록
                cursor.execute("INSERT INTO transactions (user_id, coin_type, status) VALUES (?, ?, ?)",
                               (self.user_id, selected_coin, "pending_txid"))
                transaction_id = cursor.lastrowid # 방금 삽입된 트랜잭션의 ID
                conn.commit()
                print(f"새 트랜잭션 {transaction_id} (사용자 {self.user_id}, 코인 {selected_coin}) DB에 기록 완료.")

                embed = disnake.Embed(
                    title=f"{selected_coin} 매입 진행 - 주소 확인 ✅",
                    description=f"선택하신 {selected_coin} 매입을 위해 다음 주소로 코인을 전송해 주세요.",
                    color=disnake.Color.gold()
                )
                embed.add_field(name="코인 종류", value=selected_coin, inline=True)
                embed.add_field(name="보낼 주소", value=f"```\n{coin_address}\n```", inline=False)
                embed.set_footer(text=f"트랜잭션 ID: {transaction_id}\n입금 후 'TXID 전송' 버튼을 눌러주세요.")
                
                dm_channel = await inter.author.create_dm()
                msg = await dm_channel.send(embed=embed, view=TxidSubmitView(transaction_id))

                cursor.execute("UPDATE transactions SET discord_dm_message_id = ? WHERE transaction_id = ?",
                               (msg.id, transaction_id))
                conn.commit()
                print(f"트랜잭션 {transaction_id} DM 메시지 ID 저장 완료.")

                await inter.followup.send(f"DM으로 [{selected_coin} 매입] 안내가 전송되었습니다. DM을 확인해주세요!", ephemeral=True)
            else:
                await inter.followup.send(
                    f"죄송합니다. {selected_coin}에 대한 매입 주소가 아직 설정되지 않았습니다.\n"
                    f"관리자에게 문의하여 주소 설정을 요청하거나, "
                    f"관리자님이 `/코인주소설정 {inter.author.id} {selected_coin} [주소]` 명령어로 설정해 주세요.",
                    ephemeral=True
                )
        except Exception as e:
            print(f"코인 선택 및 DM 전송 중 오류 발생: {e}")
            await inter.followup.send("코인 선택 처리 중 오류가 발생했습니다. 다시 시도해 주세요.", ephemeral=True)
        finally:
            conn.close()

# --- 유저 DM의 "TXID 전송" 버튼 및 모달 ---
class TxidSubmitView(disnake.ui.View):
    def __init__(self, transaction_id: int):
        super().__init__(timeout=600)
        self.transaction_id = transaction_id
    
    @disnake.ui.button(label="TXID 전송", style=disnake.ButtonStyle.primary, custom_id=f"submit_txid_{transaction_id}")
    async def submit_txid_button_callback(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(modal=TxidInputModal(self.transaction_id, inter.message.id))

class TxidInputModal(disnake.ui.Modal):
    def __init__(self, transaction_id: int, dm_message_id: int):
        self.transaction_id = transaction_id
        self.dm_message_id = dm_message_id
        components = [
            disnake.ui.TextInput(
                label="전송하신 코인의 TXID를 입력해주세요.",
                placeholder="블록체인 explorer에서 복사한 TXID를 붙여넣으세요.",
                custom_id="txid_input_field",
                style=disnake.TextInputStyle.short,
                max_length=200,
            ),
        ]
        super().__init__(title="TXID 입력", custom_id=f"txid_input_modal_{transaction_id}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True) # 응답 딜레이 방지
        user_txid = inter.text_values["txid_input_field"].strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 트랜잭션에 TXID 저장 및 상태 변경
            cursor.execute("UPDATE transactions SET txid = ?, status = 'txid_submitted' WHERE transaction_id = ?",
                           (user_txid, self.transaction_id))
            conn.commit()
            print(f"트랜잭션 {self.transaction_id} TXID '{user_txid}' 저장 및 상태 'txid_submitted'로 변경 완료.")
            
            # 유저 정보 가져오기 (관리자 알림 임베드 생성을 위해)
            cursor.execute("""
                SELECT u.user_id, u.depositor_name, u.account_number, t.coin_type
                FROM transactions t JOIN users u ON t.user_id = u.user_id
                WHERE t.transaction_id = ?
            """, (self.transaction_id,))
            user_data = cursor.fetchone()
            
            if user_data:
                user_id, depositor_name, account_number, coin_type = user_data
                
                # --- 관리자 채널에 전송될 임베드 생성 ---
                admin_embed = disnake.Embed(
                    title="🚨 새로운 코인 매입 요청 감지 🚨",
                    description="새로운 매입 요청이 접수되었습니다. 입금 감지 및 최종 확인을 기다립니다.",
                    color=disnake.Color.red()
                )
                admin_embed.add_field(name="매입 종류 코인", value=coin_type, inline=True)
                admin_embed.add_field(name="매입 금액 (KRW)", value=f"입금 감지 후 업데이트 예정", inline=True)
                admin_embed.add_field(name="유저가 제출한 TXID", value=f"```\n{user_txid}\n```", inline=False)
                admin_embed.add_field(name="유저 계좌 정보", value=f"```\n{account_number} ({depositor_name})\n```", inline=False)
                admin_embed.set_footer(text=f"트랜잭션 ID: {self.transaction_id} | 사용자 ID: {user_id}")

                admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
                if admin_channel:
                    admin_msg = await admin_channel.send(embed=admin_embed, view=AdminActionView(self.transaction_id))
                    cursor.execute("UPDATE transactions SET discord_admin_message_id = ? WHERE transaction_id = ?",
                                   (admin_msg.id, self.transaction_id))
                    conn.commit()
                    print(f"관리자 채널에 새 매입 요청 {self.transaction_id} 전송 완료. 메시지 ID: {admin_msg.id}")
                else:
                    print(f"Error: 관리자 채널 {ADMIN_CHANNEL_ID}를 찾을 수 없습니다. 관리자 알림을 보낼 수 없습니다.")

            # 유저 DM의 기존 임베드 수정: "잠시만 기다려주세요"로 변경
            try:
                user_dm_channel = await inter.author.create_dm()
                original_dm_message = await user_dm_channel.fetch_message(self.dm_message_id)
                
                edited_embed = disnake.Embed(
                    title="✅ TXID 전송 완료",
                    description=f"{inter.author.display_name}님, TXID가 성공적으로 제출되었습니다!\n관리자가 확인 중이니 잠시만 기다려 주세요.",
                    color=disnake.Color.green()
                )
                edited_embed.add_field(name="제출된 TXID", value=f"```\n{user_txid}\n```", inline=False)
                edited_embed.set_footer(text=f"트랜잭션 ID: {self.transaction_id}")
                await original_dm_message.edit(embed=edited_embed, view=None) # 버튼 제거

                await inter.followup.send("TXID가 성공적으로 제출되었습니다. 관리자가 확인 후 처리해 드릴 예정입니다.", ephemeral=True)
                print(f"사용자 {inter.author.id}에게 TXID 제출 확인 DM 전송 완료.")
            except disnake.NotFound:
                print(f"Warning: 사용자 {inter.author.id}의 원본 DM 메시지 {self.dm_message_id}를 찾을 수 없습니다. (수정 불가)")
                await inter.followup.send("TXID는 제출되었으나, 이전 메시지를 수정할 수 없습니다. 잠시 후 관리자가 처리해 드릴 예정입니다.", ephemeral=True)
            except Exception as e:
                print(f"사용자 DM 메시지 수정 중 오류 발생: {e}")
                await inter.followup.send("TXID는 제출되었으나, DM 메시지 수정에 오류가 발생했습니다. 잠시 후 관리자가 처리해 드릴 예정입니다.", ephemeral=True)
        except Exception as e:
            print(f"TXID 입력 및 처리 중 오류 발생: {e}")
            await inter.followup.send("TXID 처리 중 오류가 발생했습니다. 다시 시도해 주세요.", ephemeral=True)
        finally:
            conn.close()

# --- 관리자 채널의 완료/취소 버튼 ---
class AdminActionView(disnake.ui.View):
    def __init__(self, transaction_id: int):
        super().__init__(timeout=None)
        self.transaction_id = transaction_id
        self.add_item(disnake.ui.Button(label="매입 완료", style=disnake.ButtonStyle.success, custom_id=f"admin_complete_{transaction_id}"))
        self.add_item(disnake.ui.Button(label="매입 취소", style=disnake.ButtonStyle.danger, custom_id=f"admin_cancel_{transaction_id}"))

    @disnake.ui.button(label="매입 완료", custom_id=lambda id: id.startswith("admin_complete_"))
    async def complete_purchase_callback(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True) # 응답 딜레이 방지
        # 관리자만 버튼 클릭 가능 확인
        if inter.author.id != ADMIN_USER_ID:
            await inter.followup.send("이 버튼은 관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 트랜잭션 상태 업데이트
            cursor.execute("UPDATE transactions SET status = 'completed' WHERE transaction_id = ?", (self.transaction_id,))
            conn.commit()
            print(f"트랜잭션 {self.transaction_id} 상태 'completed'로 변경 완료.")

            # 유저에게 DM으로 완료 메시지 전송
            cursor.execute("SELECT user_id, coin_type, amount_coin, amount_krw FROM transactions WHERE transaction_id = ?", (self.transaction_id,))
            result = cursor.fetchone()
            
            if result:
                user_id, coin_type, amount_coin, amount_krw = result
                user = bot.get_user(user_id) or await bot.fetch_user(user_id)
                
                if user:
                    dm_channel = await user.create_dm()
                    complete_embed = disnake.Embed(
                        title="🎉 매입 완료 안내 🎉",
                        description=f"{user.display_name}님, 요청하신 코인 매입이 성공적으로 완료되었습니다! :)",
                        color=disnake.Color.green()
                    )
                    complete_embed.add_field(name="코인 종류", value=coin_type, inline=True)
                    complete_embed.add_field(name="매입 코인량", value=f"{amount_coin:.4f} {coin_type}", inline=True)
                    complete_embed.add_field(name="확인된 매입 금액 (KRW)", value=f"{amount_krw:,.0f}원", inline=False)
                    complete_embed.set_footer(text=f"트랜잭션 ID: {self.transaction_id}\n감사합니다!")
                    await dm_channel.send(embed=complete_embed)
                    print(f"사용자 {user_id}에게 매입 완료 DM 전송 완료.")
                else:
                    print(f"Warning: 사용자 {user_id}를 찾을 수 없어 완료 DM을 보낼 수 없습니다.")
            else:
                print(f"Warning: 트랜잭션 {self.transaction_id} 데이터를 찾을 수 없어 유저에게 완료 DM을 보낼 수 없습니다.")
        
            # 관리자 채널 메시지 수정 (버튼 제거, 상태 표시)
            completed_embed = disnake.Embed(
                title="✅ 코인 매입 처리 완료",
                description=f"이 매입 요청은 관리자({inter.author.display_name})에 의해 성공적으로 완료되었습니다. (트랜잭션 ID: {self.transaction_id})",
                color=disnake.Color.green()
            )
            if inter.message.embeds:
                original_embed = inter.message.embeds[0]
                for field in original_embed.fields:
                    if field.name not in ["예상 매입 금액 (KRW)", "매입 금액 (KRW)", "실제 입금 코인량", "감지된 입금 TXID"]:
                        completed_embed.add_field(name=field.name, value=field.value, inline=field.inline)
                
                if amount_krw is not None:
                    completed_embed.add_field(name="최종 처리 금액 (KRW)", value=f"{amount_krw:,.0f}원", inline=False)
            
            completed_embed.set_footer(text=f"최종 처리 완료: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}")
            
            await inter.message.edit(embed=completed_embed, view=None) # 버튼 제거
            await inter.followup.send(f"트랜잭션 {self.transaction_id}을(를) 성공적으로 완료 처리했습니다.", ephemeral=True)
            print(f"관리자 메시지 {inter.message.id} (트랜잭션 ID: {self.transaction_id}) '완료'로 업데이트 완료.")

        except Exception as e:
            print(f"매입 완료 처리 중 오류 발생 (트랜잭션 ID: {self.transaction_id}): {e}")
            await inter.followup.send(f"매입 완료 처리 중 오류가 발생했습니다: {e}", ephemeral=True)
        finally:
            conn.close()

    @disnake.ui.button(label="매입 취소", custom_id=lambda id: id.startswith("admin_cancel_"))
    async def cancel_purchase_callback(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True) # 응답 딜레이 방지
        # 관리자만 버튼 클릭 가능 확인
        if inter.author.id != ADMIN_USER_ID:
            await inter.followup.send("이 버튼은 관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 트랜잭션 상태 업데이트
            cursor.execute("UPDATE transactions SET status = 'cancelled' WHERE transaction_id = ?", (self.transaction_id,))
            conn.commit()
            print(f"트랜잭션 {self.transaction_id} 상태 'cancelled'로 변경 완료.")

            # 유저에게 DM으로 취소 메시지 전송
            cursor.execute("SELECT user_id, coin_type FROM transactions WHERE transaction_id = ?", (self.transaction_id,))
            result = cursor.fetchone()

            if result:
                user_id, coin_type = result
                user = bot.get_user(user_id) or await bot.fetch_user(user_id)
                
                if user:
                    dm_channel = await user.create_dm()
                    cancel_embed = disnake.Embed(
                        title="❌ 매입 취소 안내 ❌",
                        description=f"{user.display_name}님, 죄송합니다. 요청하신 {coin_type} 매입이 관리자({inter.author.display_name})에 의해 취소되었습니다.",
                        color=disnake.Color.red()
                    )
                    cancel_embed.add_field(name="사유", value="자세한 내용은 관리자에게 문의해주세요.", inline=False)
                    cancel_embed.set_footer(text=f"트랜잭션 ID: {self.transaction_id}")
                    await dm_channel.send(embed=cancel_embed)
                    print(f"사용자 {user_id}에게 매입 취소 DM 전송 완료.")
                else:
                    print(f"Warning: 사용자 {user_id}를 찾을 수 없어 취소 DM을 보낼 수 없습니다.")
            else:
                print(f"Warning: 트랜잭션 {self.transaction_id} 데이터를 찾을 수 없어 유저에게 취소 DM을 보낼 수 없습니다.")

            # 관리자 채널 메시지 수정 (버튼 제거, 상태 표시)
            cancelled_embed = disnake.Embed(
                title="❌ 코인 매입 처리 취소",
                description=f"이 매입 요청은 관리자({inter.author.display_name})에 의해 취소되었습니다. (트랜잭션 ID: {self.transaction_id})",
                color=disnake.Color.red()
            )
            if inter.message.embeds:
                original_embed = inter.message.embeds[0]
                for field in original_embed.fields:
                    cancelled_embed.add_field(name=field.name, value=field.value, inline=field.inline)
            
            cancelled_embed.set_footer(text=f"최종 처리 완료: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}")
            
            await inter.message.edit(embed=cancelled_embed, view=None) # 버튼 제거
            await inter.followup.send(f"트랜잭션 {self.transaction_id}을(를) 성공적으로 취소 처리했습니다.", ephemeral=True)
            print(f"관리자 메시지 {inter.message.id} (트랜잭션 ID: {self.transaction_id}) '취소'로 업데이트 완료.")
            
        except Exception as e:
            print(f"매입 취소 처리 중 오류 발생 (트랜잭션 ID: {self.transaction_id}): {e}")
            await inter.followup.send(f"매입 취소 처리 중 오류가 발생했습니다: {e}", ephemeral=True)
        finally:
            conn.close()


# --- /코인주소설정 슬래시 명령어 (관리자 전용) ---
@bot.slash_command(name="코인주소설정", description="사용자별 코인 매입 주소를 설정합니다. (관리자 전용)")
async def set_coin_address(inter: disnake.ApplicationCommandInteraction,
                          user_id: str = commands.Param(description="주소를 설정할 사용자 ID (숫자)"),
                          coin_type: str = commands.Param(description="코인 종류 (예: USDT)", choices=SUPPORTED_COINS),
                          address: str = commands.Param(description="설정할 코인 주소")):
    await inter.response.defer(ephemeral=True) # 응답 딜레이 방지
    if inter.author.id != ADMIN_USER_ID:
        await inter.followup.send("이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
        return
    
    try:
        target_user_id = int(user_id)
    except ValueError:
        await inter.followup.send("유효하지 않은 사용자 ID 형식입니다. 숫자를 입력해주세요.", ephemeral=True)
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT OR REPLACE INTO user_coin_addresses (user_id, coin_type, address) VALUES (?, ?, ?)",
                       (target_user_id, coin_type.upper(), address))
        conn.commit()
        await inter.followup.send(f"사용자 ID `{target_user_id}` 님의 `{coin_type.upper()}` 주소 `{address}`가 성공적으로 설정/업데이트되었습니다.", ephemeral=True)
        print(f"관리자에 의해 사용자 {target_user_id}의 {coin_type} 주소 설정/업데이트 완료.")
    except Exception as e:
        print(f"코인 주소 설정 중 오류 발생: {e}")
        await inter.followup.send(f"코인 주소 설정 중 오류가 발생했습니다: {e}", ephemeral=True)
    finally:
        conn.close()


# 봇 실행
if __name__ == "__main__":
    print("봇을 실행합니다...")
    try:
        bot.run(BOT_TOKEN)
    except disnake.LoginFailure:
        print("🚨🚨🚨 봇 토큰이 유효하지 않습니다. 'BOT_TOKEN' 변수를 올바르게 설정해주세요! 🚨🚨🚨")
    except Exception as e:
        print(f"봇 실행 중 치명적인 오류 발생: {e}")
