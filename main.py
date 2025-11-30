import disnake
import requests
import time
import hashlib
import hmac
import sqlite3
from datetime import datetime
from disnake import PartialEmoji, ui

# --- MEXC API 설정 (YOUR_API_KEY와 YOUR_SECRET_KEY를 실제 키로 채워주세요) ---
API_KEY = "YOUR_API_KEY" # 실제 MEXC API Key
SECRET_KEY = "YOUR_SECRET_KEY" # 실제 MEXC Secret Key
BASE_URL = "https://api.mexc.com"

# 입고 로그 채널 ID (실제 디스코드 채널 ID로 변경해주세요)
CHANNEL_DEPOSIT_LOG = 1436584475407548416 # <---------- 이 부분도 실제 채널 ID로 바꿔주세요!

# 서비스 수수료율 (기본값 2.5%)
SERVICE_FEE_RATE = 0.025 

# 입금 내역 중복 알림 방지를 위한 마지막 타임스탬프 메모리 저장
# **중요**: 봇이 재시작되면 이 값은 0으로 초기화됩니다. 실제 운영 시에는 DB에 저장하여 지속성을 확보해야 합니다.
last_deposit_checked_timestamp = 0 

# ====================================================================
# [디버깅 추가] MEXC API 서명 생성 함수
def sign_params(params: dict, secret: str) -> str:
    print(f"[sign_params] 함수 시작, 받은 params: {params}") # 디버깅
    try:
        temp = {}
        for k, v in params.items():
            if k == 'amount' and isinstance(v, float):
                temp[k] = f"{v:.8f}"
            else:
                temp[k] = str(v)
        sorted_items = sorted(temp.items())
        query_string = '&'.join(f"{k}={v}" for k, v in sorted_items)
        signature = hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        print(f"[sign_params] 서명 생성 완료. 쿼리 스트링: {query_string}, 서명: {signature[:10]}...") # 디버깅
        return signature
    except Exception as e:
        print(f"[sign_params] 서명 생성 중 오류 발생: {e}") # 디버깅
        return ""

# ====================================================================
# [디버깅 추가] MEXC 입금 감지 함수
async def check_mexc_deposits(bot):
    global last_deposit_checked_timestamp
    print(f"\n[check_mexc_deposits] 입금 감지 함수 시작. 마지막 체크 타임스탬프: {last_deposit_checked_timestamp}") # 디버깅

    if not API_KEY or not SECRET_KEY:
        print("[check_mexc_deposits] API 키 또는 시크릿 키가 설정되지 않았습니다. 입금 감지 중단.") # 디버깅
        return

    try:
        endpoint = "/api/v3/capital/deposit/hisrec"
        current_timestamp = int(time.time() * 1000) # 이름 충돌 방지
        params = {
            'timestamp': current_timestamp,
            'status': 1, # 1: 성공적인 입금
            'recvWindow': 60000,
            'limit': 50
        }
        print(f"[check_mexc_deposits] API 요청 파라미터 준비: {params}") # 디버깅
        signature = sign_params(params, SECRET_KEY)
        if not signature:
            print("[check_mexc_deposits] 서명 생성 실패. 입금 감지 중단.") # 디버깅
            return

        params['signature'] = signature
        headers = {'X-MEXC-APIKEY': API_KEY}
        
        print(f"[check_mexc_deposits] MEXC API 요청 시도: {BASE_URL}{endpoint}, Headers: {headers}, Params: {params}") # 디버깅
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        response.raise_for_status() # HTTP 오류가 발생하면 예외 발생

        data = response.json()
        print(f"[check_mexc_deposits] MEXC API 응답 수신: {data}") # 디버깅: API 응답 전체 출력
        
        deposits = data.get('data', []) if 'data' in data and isinstance(data.get('data'), list) else [] # API 응답 구조에 맞게 수정
        if not deposits and isinstance(data, list): # 가끔 API가 바로 리스트를 반환할 수도 있음
             deposits = data

        print(f"[check_mexc_deposits] 수신된 입금 내역 항목 수: {len(deposits)}") # 디버깅
        
        new_deposits = []
        max_current_deposit_timestamp = last_deposit_checked_timestamp # 현재 루프에서 발견된 가장 최신 타임스탬프

        for d in deposits:
            deposit_time = d.get('created_time') or d.get('time') or d.get('createdAt')
            print(f"[check_mexc_deposits] 처리 중인 입금 항목: {d.get('coin')}, 시간: {deposit_time}") # 디버깅
            if deposit_time is None:
                print(f"[check_mexc_deposits] 입금 항목에서 유효한 타임스탬프(created_time, time, createdAt)를 찾을 수 없습니다: {d}") # 디버깅
                continue
            
            if isinstance(deposit_time, str) and deposit_time.isdigit():
                deposit_time = int(deposit_time)
            elif isinstance(deposit_time, str):
                try:
                    dt_obj = datetime.fromisoformat(deposit_time.replace('Z', '+00:00')) # ISO 포맷 Z 처리
                    deposit_time = int(dt_obj.timestamp() * 1000)
                except ValueError:
                    print(f"[check_mexc_deposits] 타임스탬프 {deposit_time} ISO 변환 실패. 0으로 처리.") # 디버깅
                    deposit_time = 0
            
            # [디버깅 추가] 현재 입금 항목의 시간과 마지막 체크 시간을 비교
            print(f"[check_mexc_deposits] 항목 시간: {deposit_time}, 마지막 체크 시간: {last_deposit_checked_timestamp}")
            
            if deposit_time > last_deposit_checked_timestamp:
                new_deposits.append(d)
                if deposit_time > max_current_deposit_timestamp:
                    max_current_deposit_timestamp = deposit_time

        if not new_deposits:
            print("[check_mexc_deposits] 새로운 입금 내역이 없습니다.") # 디버깅
            return

        # 최신 입금 시간 갱신
        last_deposit_checked_timestamp = max_current_deposit_timestamp
        print(f"[check_mexc_deposits] 새로운 입금 내역 발견! 총 {len(new_deposits)}건. last_deposit_checked_timestamp 갱신: {last_deposit_checked_timestamp}") # 디버깅

        # 디스코드 알림 전송
        for deposit in new_deposits:
            coin = deposit.get('coin', 'UNKNOWN')
            amount = float(deposit.get('amount', 0))
            network = deposit.get('network', 'UNKNOWN')
            txid = deposit.get('txId') or deposit.get('txid') or 'N/A'
            
            await send_deposit_log_to_discord(bot, coin, amount, network, txid)

    except requests.exceptions.RequestException as e:
        print(f"[check_mexc_deposits] MEXC 입금 감지 네트워크/HTTP 오류: {e}. 응답: {e.response.text if e.response else '없음'}") # 디버깅
    except Exception as e:
        print(f"[check_mexc_deposits] MEXC 입금 감지 중 예상치 못한 오류: {e}", exc_info=True) # 디버깅: 전체 스택 트레이스 출력

# ====================================================================
# [디버깅 추가] 디스코드 입금 로그 전송 함수
async def send_deposit_log_to_discord(bot, coin, amount, network, txid):
    print(f"[send_deposit_log_to_discord] 디스코드 알림 전송 함수 시작. 채널 ID: {CHANNEL_DEPOSIT_LOG}") # 디버깅
    try:
        channel = bot.get_channel(CHANNEL_DEPOSIT_LOG)
        if channel is None:
            print(f"[send_deposit_log_to_discord] 입고 로그 채널을 찾을 수 없습니다. 채널 ID({CHANNEL_DEPOSIT_LOG}) 확인 필요.") # 디버깅
            # 봇이 켜진 후 얼마 안 되었거나, 인텐트 문제, 또는 채널 ID가 틀렸을 가능성
            guilds = bot.guilds
            found_in_guild = False
            for guild in guilds:
                if any(c.id == CHANNEL_DEPOSIT_LOG for c in guild.channels):
                    print(f"채널 ID {CHANNEL_DEPOSIT_LOG}이(가) {guild.name} 서버에 존재하지만, bot.get_channel()이 반환하지 못했습니다. 인텐트 또는 캐시 문제일 수 있습니다.")
                    found_in_guild = True
                    break
            if not found_in_guild:
                 print(f"채널 ID {CHANNEL_DEPOSIT_LOG}이(가) 봇이 접속한 어떤 서버에서도 발견되지 않았습니다.")
            return

        krw_rate = get_exchange_rate() or 1350.0
        coin_price_usd = get_coin_price(coin)
        krw_value = int(amount * coin_price_usd * krw_rate) if coin_price_usd > 0 else 0
        
        # [디버깅 추가] 환율 및 가격 정보 확인
        print(f"[send_deposit_log_to_discord] 환율: {krw_rate}, 코인 가격(USD): {coin_price_usd}, KRW 환산 값: {krw_value}")

        embed = disnake.Embed(
            title=f"🛒 입고 완료 ({coin})",
            description=f"**{amount:.8f} {coin}** 입고 확인되었습니다.",
            color=0x4caf50
        )
        embed.add_field(name="입고 금액 (KRW 환산)", value=f"**{krw_value:,}원**", inline=False)
        embed.add_field(name="네트워크", value=network, inline=True)
        # TXID 링크 수정 시 coin.lower() 부분을 실제 익스플로러에 맞게 조정 (예: USDT TRC20은 tronscan, USDT BEP20은 bscscan)
        # 지금은 블록체인 닷컴으로 일반화 해두었습니다.
        explorer_base_url = "https://www.blockchain.com"
        if network.upper() == 'TRX' or (coin.upper() == 'USDT' and network.upper() == 'TRC20'):
            explorer_base_url = "https://tronscan.org/#/transaction"
        elif network.upper() == 'BSC' or (coin.upper() == 'USDT' and network.upper() == 'BEP20'):
            explorer_base_url = "https://bscscan.com/tx"
        elif coin.upper() == 'LTC':
            explorer_base_url = "https://blockchair.com/litecoin/transaction"
        
        embed.add_field(name="TXID", value=f"[{txid}]({explorer_base_url}/{txid})", inline=True)
        embed.set_footer(text=f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print(f"[send_deposit_log_to_discord] 디스코드 채널로 임베드 메시지 전송 시도. 채널: {channel.name}") # 디버깅
        await channel.send(embed=embed)
        print("[send_deposit_log_to_discord] 디스코드 임베드 메시지 전송 성공!") # 디버깅

    except Exception as e:
        print(f"[send_deposit_log_to_discord] 디스코드 입고 알림 전송 실패: {e}", exc_info=True) # 디버깅: 전체 스택 트레이스 출력
