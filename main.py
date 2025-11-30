import disnake
import requests
import time
import hashlib
import hmac
import sqlite3
from datetime import datetime
from disnake import PartialEmoji, ui

# ... (기존 상단 코드 및 함수들은 그대로 유지) ...

# MEXC API 설정
API_KEY = "YOUR_API_KEY"
SECRET_KEY = "YOUR_SECRET_KEY"
BASE_URL = "https://api.mexc.com"

# 입고 로그를 전송할 디스코드 웹훅 URL (위에 생성한 웹훅 URL로 교체!)
WEBHOOK_DEPOSIT_LOG_URL = "YOUR_DISCORD_WEBHOOK_URL_HERE" # <------------------- **여기를 복사한 웹훅 URL로 바꿔주세요!**

# 입금 내역 중복 알림 방지를 위한 마지막 타임스탬프 메모리 저장
last_deposit_checked_timestamp = 0 

# ... (set_service_fee_rate, get_service_fee_rate, sign_params, get_exchange_rate 등 다른 함수들 그대로 유지) ...

# ====================================================================
# [수정] check_mexc_deposits 함수 - bot 객체 대신 웹훅 URL 사용하도록 변경
async def check_mexc_deposits(): # bot 객체는 더 이상 인수로 받지 않습니다.
    global last_deposit_checked_timestamp
    print(f"\n[check_mexc_deposits] 입금 감지 함수 시작. 마지막 체크 타임스탬프: {last_deposit_checked_timestamp}")

    if not API_KEY or not SECRET_KEY:
        print("[check_mexc_deposits] API 키 또는 시크릿 키가 설정되지 않았습니다. 입금 감지 중단.")
        return
    if not WEBHOOK_DEPOSIT_LOG_URL: # 웹훅 URL 설정 확인
        print("[check_mexc_deposits] 입고 로그 웹훅 URL이 설정되지 않았습니다. 입금 감지 중단.")
        return

    try:
        endpoint = "/api/v3/capital/deposit/hisrec"
        current_timestamp = int(time.time() * 1000)
        params = {
            'timestamp': current_timestamp,
            'status': 1, # 1: 성공적인 입금
            'recvWindow': 60000,
            'limit': 50
        }
        print(f"[check_mexc_deposits] API 요청 파라미터 준비: {params}")
        signature = sign_params(params, SECRET_KEY)
        if not signature:
            print("[check_mexc_deposits] 서명 생성 실패. 입금 감지 중단.")
            return

        params['signature'] = signature
        headers = {'X-MEXC-APIKEY': API_KEY}
        
        print(f"[check_mexc_deposits] MEXC API 요청 시도: {BASE_URL}{endpoint}, Headers: {headers}, Params: {params}")
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        print(f"[check_mexc_deposits] MEXC API 응답 수신: {data}")
        
        deposits = data.get('data', []) if 'data' in data and isinstance(data.get('data'), list) else []
        if not deposits and isinstance(data, list):
             deposits = data

        print(f"[check_mexc_deposits] 수신된 입금 내역 항목 수: {len(deposits)}")
        
        new_deposits = []
        max_current_deposit_timestamp = last_deposit_checked_timestamp

        for d in deposits:
            deposit_time = d.get('created_time') or d.get('time') or d.get('createdAt')
            print(f"[check_mexc_deposits] 처리 중인 입금 항목: {d.get('coin')}, 시간: {deposit_time}")
            if deposit_time is None:
                print(f"[check_mexc_deposits] 입금 항목에서 유효한 타임스탬프(created_time, time, createdAt)를 찾을 수 없습니다: {d}")
                continue
            
            if isinstance(deposit_time, str) and deposit_time.isdigit():
                deposit_time = int(deposit_time)
            elif isinstance(deposit_time, str):
                try:
                    dt_obj = datetime.fromisoformat(deposit_time.replace('Z', '+00:00'))
                    deposit_time = int(dt_obj.timestamp() * 1000)
                except ValueError:
                    print(f"[check_mexc_deposits] 타임스탬프 {deposit_time} ISO 변환 실패. 0으로 처리.")
                    deposit_time = 0
            
            print(f"[check_mexc_deposits] 항목 시간: {deposit_time}, 마지막 체크 시간: {last_deposit_checked_timestamp}")
            
            if deposit_time > last_deposit_checked_timestamp:
                new_deposits.append(d)
                if deposit_time > max_current_deposit_timestamp:
                    max_current_deposit_timestamp = deposit_time

        if not new_deposits:
            print("[check_mexc_deposits] 새로운 입금 내역이 없습니다.")
            return

        last_deposit_checked_timestamp = max_current_deposit_timestamp
        print(f"[check_mexc_deposits] 새로운 입금 내역 발견! 총 {len(new_deposits)}건. last_deposit_checked_timestamp 갱신: {last_deposit_checked_timestamp}")

        for deposit in new_deposits:
            coin = deposit.get('coin', 'UNKNOWN')
            amount = float(deposit.get('amount', 0))
            network = deposit.get('network', 'UNKNOWN')
            txid = deposit.get('txId') or deposit.get('txid') or 'N/A'
            
            # [수정] send_deposit_log_to_discord 함수 호출 변경
            await send_deposit_log_to_discord(coin, amount, network, txid) # bot 객체를 전달하지 않습니다.

    except requests.exceptions.RequestException as e:
        print(f"[check_mexc_deposits] MEXC 입금 감지 네트워크/HTTP 오류: {e}. 응답: {e.response.text if e.response else '없음'}")
    except Exception as e:
        print(f"[check_mexc_deposits] MEXC 입금 감지 중 예상치 못한 오류: {e}", exc_info=True)

# ====================================================================
# [수정] send_deposit_log_to_discord 함수 - 웹훅 사용
async def send_deposit_log_to_discord(coin, amount, network, txid): # bot 객체는 더 이상 인수로 받지 않습니다.
    print(f"[send_deposit_log_to_discord] 디스코드 웹훅 알림 전송 함수 시작.")
    if not WEBHOOK_DEPOSIT_LOG_URL:
        print("[send_deposit_log_to_discord] 웹훅 URL이 설정되지 않아 알림을 보낼 수 없습니다.")
        return

    try:
        krw_rate = get_exchange_rate() or 1350.0
        coin_price_usd = get_coin_price(coin)
        krw_value = int(amount * coin_price_usd * krw_rate) if coin_price_usd > 0 else 0
        
        print(f"[send_deposit_log_to_discord] 환율: {krw_rate}, 코인 가격(USD): {coin_price_usd}, KRW 환산 값: {krw_value}")

        # 임베드 생성 (Discord 웹훅 규격에 맞춤)
        embed = {
            "title": f"🛒 입고 완료 ({coin})",
            "description": f"**{amount:.8f} {coin}** 입고 확인되었습니다.",
            "color": 0x4caf50, # 십진수 (초록색)
            "fields": [
                {"name": "입고 금액 (KRW 환산)", "value": f"**{krw_value:,}원**", "inline": False},
                {"name": "네트워크", "value": network, "inline": True}
            ],
            "footer": {
                "text": f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }
        
        explorer_base_url = "https://www.blockchain.com"
        if network.upper() == 'TRX' or (coin.upper() == 'USDT' and network.upper() == 'TRC20'):
            explorer_base_url = "https://tronscan.org/#/transaction"
        elif network.upper() == 'BSC' or (coin.upper() == 'USDT' and network.upper() == 'BEP20'):
            explorer_base_url = "https://bscscan.com/tx"
        elif coin.upper() == 'LTC':
            explorer_base_url = "https://blockchair.com/litecoin/transaction"
        
        # TXID 필드는 웹훅 임베드 필드로 바로 추가
        embed['fields'].append({"name": "TXID", "value": f"[{txid}]({explorer_base_url}/{txid})", "inline": True})


        # 웹훅 페이로드 (embeds 리스트에 임베드를 넣음)
        webhook_payload = {
            "embeds": [embed]
        }

        print(f"[send_deposit_log_to_discord] 디스코드 웹훅 전송 시도. URL: {WEBHOOK_DEPOSIT_LOG_URL}")
        # requests.post는 비동기 함수가 아니지만, async context에서 실행 가능
        response = requests.post(WEBHOOK_DEPOSIT_LOG_URL, json=webhook_payload, timeout=10)
        response.raise_for_status() # HTTP 오류가 발생하면 예외 발생
        
        print("[send_deposit_log_to_discord] 디스코드 웹훅 메시지 전송 성공!")

    except requests.exceptions.RequestException as e:
        print(f"[send_deposit_log_to_discord] 웹훅 전송 네트워크/HTTP 오류: {e}. 응답: {e.response.text if e.response else '없음'}")
    except Exception as e:
        print(f"[send_deposit_log_to_discord] 디스코드 웹훅 알림 전송 중 예상치 못한 오류: {e}", exc_info=True)

# ... (나머지 코드 그대로 유지) ...
