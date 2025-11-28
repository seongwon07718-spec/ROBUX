import disnake
import requests
import time
import hashlib
import hmac
import sqlite3
from datetime import datetime
import urllib.parse
from disnake import PartialEmoji, ui
import asyncio

# 웹훅 사용 제거 (주석 처리)

# MEXC API 설정 (실제 사용 시 반드시 채워야 합니다)
API_KEY = ""
SECRET_KEY = ""
BASE_URL = "https://api.mexc.com"

# 입고 로그 채널 ID (실제 봇에서 사용 시 봇 객체를 통해 채널을 가져와야 함)
CHANNEL_DEPOSIT_LOG = 1436584475407548416

# 서비스 수수료율 (기본값, get_user_tier_and_fee에서 동적으로 결정될 수 있음)
SERVICE_FEE_RATE = 0.025 

def set_service_fee_rate(rate: float):
    global SERVICE_FEE_RATE
    try:
        if 0 <= rate <= 0.25:
            SERVICE_FEE_RATE = rate
            return True
        return False
    except Exception:
        return False

def get_service_fee_rate() -> float:
    try:
        return SERVICE_FEE_RATE
    except Exception:
        return 0.025

def sign_params(params, secret):
    """MEXC API 요청 서명 생성"""
    try:
        # 파라미터를 알파벳 순으로 정렬 후 쿼리 스트링 생성
        sorted_params = sorted(params.items())
        # 'amount' 같은 값은 문자열로 변환하여 쿼리스트링에 포함
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
        signature = hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        return signature
    except Exception as e:
        print(f"Error signing params: {e}")
        return ""

def get_exchange_rate():
    """USD/KRW 환율 조회"""
    try:
        # 안정적인 환율 API 사용 (예시)
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        response.raise_for_status()
        data = response.json()
        rate = data.get("rates", {}).get("KRW")
        return rate if rate and rate > 0 else 1350.0
    except (requests.RequestException, ValueError, KeyError):
        return 1350.0
    except Exception:
        return 1350.0

def get_kimchi_premium():
    """김치 프리미엄 계산 (%)"""
    try:
        # 1. 업비트 (KRW-BTC) 가격 조회
        upbit_response = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC", timeout=5)
        upbit_response.raise_for_status()
        upbit_data = upbit_response.json()
        upbit_price = upbit_data[0]['trade_price']

        # 2. 바이낸스 (BTCUSDT) 가격 조회
        binance_response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=5)
        binance_response.raise_for_status()
        binance_data = binance_response.json()
        binance_price_usd = float(binance_data['price'])

        # 3. USD/KRW 환율 조회
        krw_rate = get_exchange_rate()
        if krw_rate <= 0: return 0.0

        # 4. 김치 프리미엄 계산
        binance_price_krw = binance_price_usd * krw_rate
        if binance_price_krw <= 0: return 0.0
            
        kimchi_premium = ((upbit_price - binance_price_krw) / binance_price_krw) * 100

        return round(kimchi_premium, 2)
    except (requests.RequestException, ValueError, KeyError, IndexError) as e:
        # print(f"Kimchi Premium Error: {e}")
        return 0.0
    except Exception:
        return 0.0
    
def get_upbit_coin_price(coin_symbol):
    """업비트에서 코인 가격을 USD로 조회"""
    try:
        if coin_symbol.upper() == 'USDT':
            return 1.0 # USDT는 $1로 고정 가정

        url = f"https://api.upbit.com/v1/ticker?markets=KRW-{coin_symbol.upper()}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        data = response.json()
        if data and len(data) > 0:
            krw_price = float(data[0].get('trade_price', 0))
            # KRW를 USD로 변환
            usd_krw_rate = get_exchange_rate()
            if usd_krw_rate > 0:
                usd_price = krw_price / usd_krw_rate
                return usd_price
        return 0.0
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return 0.0
    except Exception:
        return 0.0

def get_mexc_coin_price(coin_symbol):
    """MEXC에서 코인 가격 조회 (백업용)"""
    try:
        endpoint = "/api/v3/ticker/price"
        params = {'symbol': f"{coin_symbol.upper()}USDT"} # symbol은 대문자로

        response = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=5)
        response.raise_for_status()

        data = response.json()
        return float(data.get('price', 0))
    except (requests.RequestException, ValueError, KeyError):
        return 0.0
    except Exception:
        return 0.0

def get_coin_price(coin_symbol):
    """특정 코인의 현재 가격을 USD로 조회 (업비트 우선, MEXC 백업)"""
    if coin_symbol.upper() == 'USDT':
        return 1.0 

    try:
        upbit_price = get_upbit_coin_price(coin_symbol)
        if upbit_price > 0:
            return upbit_price
    except Exception:
        pass 

    return get_mexc_coin_price(coin_symbol)

def get_all_coin_prices():
    """모든 지원 코인의 현재 가격을 조회 (업비트 우선, MEXC 백업)"""
    try:
        prices = {}
        supported_coins = ['USDT', 'TRX', 'LTC', 'BNB']

        for coin in supported_coins:
            prices[coin] = get_coin_price(coin) 

        return prices
    except Exception:
        return {}

def mexc_swap_coins(from_coin, to_coin, amount):
    """MEXC Convert 시뮬레이션: from_coin을 to_coin으로 변환"""
    # 실제 API 호출 대신 시뮬레이션 로직을 유지합니다.
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키가 설정되지 않았습니다.'}

    if from_coin.upper() == to_coin.upper():
        return {'success': True, 'orderId': f"SWAP_SAME_{int(time.time())}", 'status': 'success',
                'from_coin': from_coin.upper(), 'to_coin': to_coin.upper(), 'amount': amount,
                'swapped_amount': amount, 'fee': 0.0}

    try:
        from_price = get_coin_price(from_coin.upper())
        to_price = get_coin_price(to_coin.upper())

        if from_price <= 0 or to_price <= 0:
            return {'success': False, 'error': f'{from_coin.upper()} 또는 {to_coin.upper()} 가격 조회 실패'}

        usdt_value = amount * from_price
        converted_amount_before_fee = usdt_value / to_price

        # 스왑 수수료 적용 (예: 0.1%)
        swap_fee_rate = 0.001
        final_amount = converted_amount_before_fee * (1 - swap_fee_rate)

        print(f"Debug: {from_coin.upper()} {amount:.6f} -> {to_coin.upper()} {final_amount:.6f} (시뮬레이션, 수수료: {swap_fee_rate * 100:.1f}%)")

        return {
            'success': True,
            'orderId': f"SWAP_{int(time.time())}",
            'status': 'success',
            'from_coin': from_coin.upper(),
            'to_coin': to_coin.upper(),
            'amount': amount,
            'swapped_amount': final_amount,
            'fee_rate': swap_fee_rate,
            'fee_amount_in_target_coin': converted_amount_before_fee * swap_fee_rate
        }
    except Exception as e:
        return {'success': False, 'error': f'시뮬레이션 스왑 오류: {str(e)}'}

def get_transaction_fee(coin, network):
    """송금 수수료 조회 (코인 단위)"""
    fees = {
        'USDT': {'BSC': 0.8, 'TRX': 1.0}, # 예시 값
        'TRX': {'TRX': 1.0},
        'LTC': {'LTC': 0.001},
        'BNB': {'BSC': 0.0005}
    }

    coin_fees = fees.get(coin.upper(), {})
    return coin_fees.get(network.upper(), 0.0) 

def send_coin_transaction(amount, address, network, coin='USDT', skip_min_check=False, skip_address_check=False):
    """
    MEXC에서 코인 송금 (출금) - MEXC API v3 기준
    **오류 발생 주요 지점 수정: amount 포맷, network 코드 매핑, 서명 파라미터**
    """
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키가 설정되지 않았습니다'}

    # MEXC 최소 송금 금액 확인 (skip_min_check가 True면 건너뛰기)
    min_amount = get_minimum_amount_coin(coin.upper())
    if not skip_min_check and amount < min_amount:
        return {'success': False, 'error': f'최소 송금 금액 미달: 약 {min_amount:.6f} {coin.upper()} 필요'}
        
    # Discord/사용자 입력 네트워크 이름 -> MEXC API 네트워크 코드 매핑
    network_mapping = {
        'bep20': 'BSC',      # BSC 네트워크 (BEP20)
        'trc20': 'TRX',      # TRON 네트워크 (TRC20)
        'ltc': 'LTC',        # Litecoin 네트워크
        'bnb': 'BSC'         # BNB는 BEP20으로 간주
    }

    network_code = network_mapping.get(network.lower())
    if not network_code:
        return {'success': False, 'error': f'지원하지 않는 네트워크: {network}'}

    print(f"Debug: Coin={coin}, Network={network}, NetworkCode={network_code}, Amount={amount:.8f}, Address={address}")

    try:
        endpoint = "/api/v3/capital/withdraw"
        timestamp = int(time.time() * 1000)

        # 서명 생성 시 'amount'는 문자열로 정확히 전달
        params = {
            'coin': coin.upper(),
            'address': str(address).strip(),
            'amount': f"{amount:.8f}", # **수정: 정밀도 유지 및 문자열 변환**
            'network': network_code, # MEXC API V3는 'network' 파라미터 사용
            'recvWindow': 60000,
            'timestamp': timestamp
        }

        signature = sign_params(params, SECRET_KEY)
        if not signature:
            return {'success': False, 'error': 'API 서명 생성 실패'}

        # POST 요청 시 서명을 파라미터에 추가하고, API Key는 헤더에 추가
        params['signature'] = signature

        headers = {
            'X-MEXC-APIKEY': API_KEY
        }

        response = requests.post(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=30)
        response.raise_for_status() 

        data = response.json()
        print(f"Debug: Withdraw response: {data}")
        
        if data.get('id'): # 출금 성공 시 id (TXID) 반환
            txid = str(data.get('id', ''))
            share_link = get_txid_link(txid, coin.upper())

            result = {
                'success': True,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'txid': txid,
                'network': network_code,
                'sent_amount': amount,
                'to_address': str(address).strip(),
                'share_link': share_link,
                'coin': coin.upper()
            }
            return result
        else:
            # 거래소에서 오류 메시지 반환 시
            error_msg = data.get('msg', '알 수 없는 거래소 오류')
            error_code = data.get('code', 'N/A')
            return {'success': False, 'error': f'거래소 오류 ({error_code}): {error_msg}'}

    except requests.exceptions.RequestException as e:
        error_details = ""
        if hasattr(e, 'response') and e.response is not None:
            try: 
                error_details = e.response.json()
            except: 
                error_details = e.response.text[:200]
        return {'success': False, 'error': f'네트워크 또는 API 통신 오류: {str(e)} ({error_details})'}
    except Exception as e:
        return {'success': False, 'error': f'예상치 못한 오류: {str(e)}'}

def simple_send_coin(target_coin, amount, address, network):
    """
    모든 코인 재고를 활용하여 목표 코인으로 Convert 후 송금 시도
    (기존 로직 유지)
    """
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키가 설정되지 않았습니다.'}

    try:
        balances = get_all_balances()
        prices = get_all_coin_prices() 
        target_coin = target_coin.upper()
        target_balance = balances.get(target_coin, 0.0)
        target_coin_price_usd = prices.get(target_coin, 0.0)

        if target_coin_price_usd <= 0:
            return {'success': False, 'error': f'목표 코인 {target_coin}의 가격을 조회할 수 없습니다.'}

        print(f"Debug: 목표 코인={target_coin}, 필요량={amount:.6f}, 현재 잔액={target_balance:.6f}")

        # 1. 목표 코인이 충분하면 바로 송금
        if target_balance >= amount:
            print(f"Debug: {target_coin} 잔액 충분, 바로 송금 진행")
            return send_coin_transaction(amount, address, network, target_coin)

        # 2. 목표 코인이 부족하면 다른 코인 활용 로직 (Convert 시뮬레이션)
        needed_usdt_value = amount * target_coin_price_usd
        current_usdt_balance = balances.get('USDT', 0.0)
        total_usdt_after_conversions = current_usdt_balance

        convert_log = []

        # 2.b. 보유 코인들을 USDT로 전환 시도 (BNB, TRX, LTC 순)
        convert_priority = ['BNB', 'TRX', 'LTC'] 

        for coin_to_convert in convert_priority:
            if total_usdt_after_conversions >= needed_usdt_value:
                break 

            coin_balance = balances.get(coin_to_convert, 0.0)
            if coin_balance <= 0:
                continue

            print(f"Debug: {coin_to_convert} {coin_balance:.6f}을 USDT로 Convert 시도 (시뮬레이션)")
            convert_result = mexc_swap_coins(coin_to_convert, 'USDT', coin_balance)

            if convert_result and convert_result.get('success', False):
                converted_usdt = convert_result.get('swapped_amount', 0.0)
                total_usdt_after_conversions += converted_usdt
                convert_log.append(f"  {coin_to_convert} {coin_balance:.6f} → USDT {converted_usdt:.6f}")
                print(f"Debug: {coin_to_convert} Convert 성공, 현재 확보된 USDT: {total_usdt_after_conversions:.6f}")
            else:
                error_msg = convert_result.get('error', 'Convert 실패') if convert_result else 'Convert 실패'
                convert_log.append(f"  {coin_to_convert} Convert 실패: {error_msg}")
                print(f"Debug: {coin_to_convert} Convert 실패: {error_msg}")

        print(f"Debug: 총 확보된 USDT (변환 후): {total_usdt_after_conversions:.6f}, 필요한 USDT 가치: {needed_usdt_value:.6f}")

        # 2.c. 최종 확보된 USDT로 목표 코인으로 Convert 시도
        if total_usdt_after_conversions >= needed_usdt_value:
            usdt_to_convert_for_target = needed_usdt_value 

            print(f"Debug: 확보된 USDT {total_usdt_after_conversions:.6f}로 {target_coin} {amount:.6f} 생성 시도")
            convert_to_target_result = mexc_swap_coins('USDT', target_coin, usdt_to_convert_for_target)

            if convert_to_target_result and convert_to_target_result.get('success', False):
                final_target_amount = convert_to_target_result.get('swapped_amount', 0.0)
                convert_log.append(f"  USDT {usdt_to_convert_for_target:.6f} → {target_coin} {final_target_amount:.6f}")
                print(f"Debug: 최종 {target_coin} 확보량: {final_target_amount:.6f}")

                if final_target_amount >= amount:
                    return send_coin_transaction(amount, address, network, target_coin)
                else:
                    debug_msg = "\n".join(convert_log)
                    return {'success': False, 'error': f'코인 변환 후에도 {target_coin} 잔액이 부족합니다.\n{debug_msg}\n(최종 확보량: {final_target_amount:.6f}, 필요량: {amount:.6f})'}
            else:
                error_msg = convert_to_target_result.get('error', 'Convert 실패') if convert_to_target_result else 'Convert 실패'
                debug_msg = "\n".join(convert_log)
                return {'success': False, 'error': f'USDT를 {target_coin}로 변환 실패: {error_msg}\n{debug_msg}'}
        else:
            debug_msg = "\n".join(convert_log)
            return {'success': False, 'error': f'모든 코인을 변환해도 필요한 USDT를 확보하지 못했습니다.\n{debug_msg}\n(확보 USDT: {total_usdt_after_conversions:.6f}, 필요 USDT: {needed_usdt_value:.6f})'}
    except Exception as e:
        return {'success': False, 'error': f'자동 Convert/송금 오류: {str(e)}'}

def get_balance(coin='USDT') -> float:
    """단일 코인의 잔액을 조회 (float 반환)"""
    if not API_KEY or not SECRET_KEY:
        return 0.0
    # MEXC API 호출 (기존 로직 유지)

    try:
        endpoint = "/api/v3/account"
        timestamp = int(time.time() * 1000)

        params = { 'timestamp': timestamp }
        signature = sign_params(params, SECRET_KEY)
        if not signature: return 0.0
        params['signature'] = signature

        headers = { 'X-MEXC-APIKEY': API_KEY }
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        balances = data.get('balances', [])

        for balance in balances:
            if balance.get('asset') == coin.upper():
                free_balance = float(balance.get('free', 0))
                return max(0.0, free_balance)
        return 0.0
    except (requests.RequestException, ValueError, KeyError):
        return 0.0
    except Exception:
        return 0.0

def get_all_balances():
    """모든 지원 코인의 잔액을 조회"""
    if not API_KEY or not SECRET_KEY:
        return {}
    # MEXC API 호출 (기존 로직 유지)

    try:
        endpoint = "/api/v3/account"
        timestamp = int(time.time() * 1000)

        params = { 'timestamp': timestamp }
        signature = sign_params(params, SECRET_KEY)
        if not signature: return {}
        params['signature'] = signature

        headers = { 'X-MEXC-APIKEY': API_KEY }
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        balances = data.get('balances', [])

        supported_coins = ['USDT', 'TRX', 'LTC', 'BNB']
        result = {coin: 0.0 for coin in supported_coins} 

        for balance in balances:
            asset = balance.get('asset', '')
            if asset in supported_coins:
                free_balance = float(balance.get('free', 0))
                result[asset] = max(0.0, free_balance)
        return result
    except (requests.RequestException, ValueError, KeyError):
        return {}
    except Exception:
        return {}


# --- SQLite DB Helpers (기존 로직 유지) ---
def get_verified_user(user_id):
    conn = None
    try:
        conn = sqlite3.connect('DB/verify_user.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        return user
    except (sqlite3.Error, OSError) as e:
        print(f"DB Error (get_verified_user): {e}")
        return None
    finally:
        if conn: conn.close()

def subtract_balance(user_id, amount):
    conn = None
    try:
        conn = sqlite3.connect('DB/verify_user.db')
        cursor = conn.cursor()
        cursor.execute('SELECT now_amount FROM users WHERE user_id = ?', (user_id,))
        current = cursor.fetchone()

        if current and current[0] >= amount:
            new_balance = current[0] - amount
            cursor.execute('UPDATE users SET now_amount = ? WHERE user_id = ?', (new_balance, user_id))
            conn.commit()
            return True
        else:
            return False
    except (sqlite3.Error, OSError) as e:
        print(f"DB Error (subtract_balance): {e}")
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()

def add_transaction_history(user_id, amount, transaction_type):
    conn = None
    try:
        conn = sqlite3.connect('DB/history.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO transaction_history (user_id, amount, type, timestamp) VALUES (?, ?, ?, ?)', 
                      (user_id, amount, transaction_type, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
    except (sqlite3.Error, OSError) as e:
        print(f"DB Error (add_transaction_history): {e}")
    finally:
        if conn: conn.close()

# --- Utility Functions (기존 로직 유지) ---
def get_txid_link(txid, coin='USDT'):
    try:
        if txid and len(str(txid)) > 0:
            explorer_links = {
                'USDT': f"https://bscscan.com/tx/{txid}", 
                'BNB': f"https://bscscan.com/tx/{txid}",  
                'TRX': f"https://tronscan.org/#/transaction/{txid}", 
                'LTC': f"https://blockchair.com/litecoin/transaction/{txid}" 
            }
            # TXID가 숫자(MEXC ID)인 경우 링크를 생성하지 않거나, 거래소 내역 조회 링크로 변경해야 함.
            # 여기서는 블록체인 TXID라고 가정하고 링크를 생성합니다.
            return explorer_links.get(coin.upper(), f"https://bscscan.com/tx/{txid}") 
        return "https://bscscan.com/" 
    except Exception:
        return "https://bscscan.com/"

def get_minimum_amounts_krw():
    """최소 송금 금액을 KRW로 변환하여 반환"""
    min_amounts = {
        'USDT': 10,     
        'TRX': 10,      
        'LTC': 0.015,   
        'BNB': 0.008    
    }

    prices = get_all_coin_prices()
    krw_rate = get_exchange_rate()
    kimchi_premium = get_kimchi_premium()
    actual_krw_rate = krw_rate * (1 + kimchi_premium / 100) 

    min_amounts_krw = {}
    for coin, min_amount_coin_unit in min_amounts.items():
        coin_price = prices.get(coin, 0)
        if coin_price > 0 and actual_krw_rate > 0:
            krw_value = min_amount_coin_unit * coin_price * actual_krw_rate
            min_amounts_krw[coin] = int(krw_value)
        else:
            min_amounts_krw[coin] = 0

    return min_amounts_krw

def get_user_tier_and_fee(user_id: int):
    """Return (tier, service_fee_rate, purchase_bonus_rate). tier: 'VIP' or 'BUYER'"""
    try:
        total_amount = 0
        conn = None
        try:
            conn = sqlite3.connect('DB/verify_user.db')
            cursor = conn.cursor()
            cursor.execute('SELECT Total_amount FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                total_amount = int(row[0] or 0)
        except Exception:
            pass 
        finally:
            if conn: conn.close()

        if total_amount >= 10_000_000:
            return ('VIP', 0.03, 0.01) # VIP: 서비스 수수료 3%, 구매 보너스 1%
        else:
            return ('BUYER', 0.05, 0.0) # BUYER: 서비스 수수료 5%, 구매 보너스 0%
    except Exception:
        return ('BUYER', 0.05, 0.0) 

def get_minimum_amount_coin(coin_symbol):
    """특정 코인의 최소 송금 금액을 코인 단위로 반환"""
    min_amounts = {
        'USDT': 10,     
        'TRX': 10,      
        'LTC': 0.015,   
        'BNB': 0.008    
    }

    return min_amounts.get(coin_symbol.upper(), 10.0)

def krw_to_coin_amount(krw_amount, coin_symbol):
    """KRW 금액을 코인 단위로 변환"""
    krw_rate = get_exchange_rate()
    coin_price = get_coin_price(coin_symbol.upper())
    kimchi_premium = get_kimchi_premium()
    actual_krw_rate = krw_rate * (1 + kimchi_premium / 100) 

    if actual_krw_rate <= 0 or coin_price <= 0:
        return 0.0 

    # KRW → USD (김프 반영) → Coin
    return krw_amount / (actual_krw_rate * coin_price)

# --- Discord UI Components (수정된 부분) ---
custom_emoji11 = PartialEmoji(name="47311ltc", id=1438899347453509824)
custom_emoji12 = PartialEmoji(name="6798bnb", id=1438899349110390834)
custom_emoji13 = PartialEmoji(name="tron", id=1438899350582591701)
custom_emoji14 = PartialEmoji(name="7541tetherusdt", id=1439510997730721863)

class AmountModal(disnake.ui.Modal):
    """
    송금 금액 및 주소 입력 모달
    **수정: __init__ 함수 내에서 변수 초기화 및 최소 송금액 조회 로직 안정화**
    """
    def __init__(self, network, coin='usdt'): 
        self.network = network
        self.coin = coin
        self.coin_unit = self.coin.upper()

        # 실시간 최소송금 금액 조회 (안정적인 위치로 이동)
        min_amounts_krw = get_minimum_amounts_krw()
        min_krw = min_amounts_krw.get(self.coin_unit, 10000)

        components = [
            disnake.ui.TextInput(
                label="금액",
                placeholder=f"금액을 입력해주세요 (최소 {min_krw:,}원)",
                custom_id="amount",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=15,
            ),
            disnake.ui.TextInput(
                label="코인 주소",
                placeholder="송금 받으실 지갑 주소를 입력해주세요",
                custom_id="address",
                style=disnake.TextInputStyle.short,
                min_length=10,
                max_length=100,
            )
        ]
        super().__init__(
            title=f"{self.coin_unit} 송금 정보 ({self.network.upper()})",
            custom_id=f"amount_modal_{network}_{coin}",
            components=components,
        )

class ChargeModal(disnake.ui.Modal):
    """충전 금액 입력 모달 (기존 로직 유지)"""
    def __init__(self): 
        components = [
            disnake.ui.TextInput(
                label="충전 금액",
                placeholder="숫자만 입력해주세요",
                custom_id="charge_amount",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=15,
            )
        ]
        super().__init__(
            title="충전 금액 입력",
            custom_id="charge_modal",
            components=components,
        )

class CoinDropdown(disnake.ui.Select):
    """코인 선택 드롭다운 (기존 로직 유지)"""
    def __init__(self):
        options = [
            disnake.SelectOption(label="USDT", description="테더 선택", value="usdt", emoji=custom_emoji14),
            disnake.SelectOption(label="TRX", description="트론 선택", value="trx", emoji=custom_emoji13),
            disnake.SelectOption(label="LTC", description="라이트코인 선택", value="ltc", emoji=custom_emoji11),
            disnake.SelectOption(label="BNB", description="바이낸스코인 산텍", value="bnb", emoji=custom_emoji12)
        ]
        super().__init__(placeholder="송금할 코인을 선택해주세요", options=options)

    async def callback(self, interaction: disnake.MessageInteraction):
        try:
            # 🚨 상호작용 실패 방지를 위해 defer 호출
            await interaction.response.defer(ephemeral=True)
        except Exception:
            return

        try:
            user_data = get_verified_user(interaction.author.id)
            if not user_data:
                embed = disnake.Embed(title="오류", description="인증되지 않은 고객님입니다.", color=0xff6200)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            selected_coin = self.values[0]
            min_amounts_krw = get_minimum_amounts_krw() 
            min_krw = min_amounts_krw.get(selected_coin.upper(), 10000)
            min_amount = f"{min_krw:,}"
                
            embed = disnake.Embed(
                title=f"{selected_coin.upper()} 송금",
                description=f"최소 송금 금액 = **{min_amount}원**",
                color=0xffffff
            )
            view = disnake.ui.View()
            view.add_item(NetworkDropdown(selected_coin))
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            print(f"CoinDropdown callback 에러: {e}")
            embed = disnake.Embed(title="오류", description="처리 중 오류가 발생했습니다.", color=0xff6200)
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception:
                pass

class NetworkDropdown(disnake.ui.Select):
    """
    네트워크 선택 드롭다운
    **수정: init 대신 __init__ 사용**
    """
    def __init__(self, selected_coin): # init을 __init__으로 수정
        self.selected_coin = selected_coin

        network_options = {
            'usdt': [
                disnake.SelectOption(label="BEP20", description="BSC Network (Binance Smart Chain)", value="bep20"),
                disnake.SelectOption(label="TRC20", description="TRON Network", value="trc20")
            ],
            'trx': [
                disnake.SelectOption(label="TRC20", description="TRON Network", value="trc20")
            ],
            'ltc': [
                disnake.SelectOption(label="LTC", description="Litecoin Network", value="ltc")
            ],
            'bnb': [
                disnake.SelectOption(label="BEP20", description="BSC Network (Binance Smart Chain)", value="bep20")
            ]
        }

        options = network_options.get(selected_coin.lower(), [
            disnake.SelectOption(label="BEP20", description="BSC Network", value="bep20")
        ])

        super().__init__(placeholder="네트워크를 선택해주세요", options=options)

    async def callback(self, interaction: disnake.MessageInteraction):
        try:
            # 모달 호출은 response.send_modal을 사용하여 3초 제한 내에 응답해야 합니다.
            await interaction.response.send_modal(AmountModal(self.values[0], self.selected_coin))
        except Exception as e:
            print(f"NetworkDropdown callback 예외 발생 (Modal Call Failed): {e}")
            # 모달 호출이 실패하면 이미 응답하지 못했으므로, followup으로 에러 메시지 전송
            embed = disnake.Embed(title="오류", description="모달 호출 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", color=0xff6200)
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass

# --- Transaction Handlers ---
pending_transactions = {}

async def handle_amount_modal(interaction: disnake.ModalInteraction):
    """
    송금 금액/주소 입력 후 최종 확인 로직
    **수정: 오류 메시지 전송을 edit_original_response 대신 followup.send로 안정화**
    """
    try:
        # 응답 지연 (3초 제한 해결). 모달 제출 후 로직은 시간이 걸릴 수 있으므로 필수.
        await interaction.response.defer(ephemeral=True)

        amount_str = interaction.text_values.get("amount", "").strip().replace(',', '') # 쉼표 제거
        address = interaction.text_values.get("address", "").strip()

        if not amount_str or not address:
            embed = disnake.Embed(title="**오류**", description="**모든 필드를 입력해주세요.**", color=0xff6200)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            krw_amount_input = float(amount_str) # 사용자가 입력한 KRW 금액
            if krw_amount_input <= 0:
                raise ValueError("양수여야 합니다")
        except (ValueError, TypeError):
            embed = disnake.Embed(title="**오류**", description="**올바른 숫자(금액)를 입력해주세요.**", color=0xff6200)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        custom_id_parts = interaction.custom_id.split('_')
        network = custom_id_parts[-2] 
        coin = custom_id_parts[-1] 

        min_amounts_krw = get_minimum_amounts_krw()
        min_amount_krw = min_amounts_krw.get(coin.upper(), 10000)
        coin_unit = coin.upper()

        if krw_amount_input < min_amount_krw:
            embed = disnake.Embed(title="**오류**", description=f"**출금 최소 금액은 {min_amount_krw:,}원입니다.**", color=0xff6200)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        user_data = get_verified_user(interaction.author.id)
        if not user_data:
            embed = disnake.Embed(title="**오류**", description="**인증되지 않은 고객님 입니다.**", color=0xff6200)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        current_balance = user_data[6] if len(user_data) > 6 else 0
        if current_balance < krw_amount_input:
            embed = disnake.Embed(title="잔액 부족", description=f"보유 금액 = {current_balance:,}원\n필요금액 = {int(krw_amount_input):,}원", color=0xff6200)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # --- 수수료 계산 로직 ---
        krw_rate = get_exchange_rate()
        coin_price_usd = get_coin_price(coin.upper())
        kimchi_premium = get_kimchi_premium()
        actual_krw_rate = krw_rate * (1 + kimchi_premium / 100) 

        if coin_price_usd <= 0 or actual_krw_rate <= 0:
            embed = disnake.Embed(title="**오류**", description="**코인 가격 또는 환율 정보를 조회할 수 없습니다.**", color=0xff6200)
            await interaction.followup.send(embed=embed, ephemeral=True) # defer 후 followup 사용
            return

        # 2. 서비스 수수료 계산
        user_tier, service_fee_base_rate, _ = get_user_tier_and_fee(interaction.author.id)
        total_service_fee_rate = service_fee_base_rate + (kimchi_premium / 100)
        service_fee_krw = krw_amount_input * total_service_fee_rate 

        # 3. 거래소 송금 수수료 (코인 -> KRW)
        # 네트워크 코드 매핑 확인
        network_code = {'bep20': 'BSC', 'trc20': 'TRX', 'ltc': 'LTC', 'bnb': 'BSC'}.get(network.lower(), network.upper())
        transaction_fee_coin = get_transaction_fee(coin.upper(), network_code) # network_code 사용
        exchange_fee_krw = transaction_fee_coin * coin_price_usd * actual_krw_rate 

        # 4. 최종 송금에 필요한 총 KRW 금액
        total_fee_krw = service_fee_krw + exchange_fee_krw
        actual_send_krw_pre_convert = krw_amount_input - total_fee_krw

        if actual_send_krw_pre_convert <= 0:
            embed = disnake.Embed(title="오류", description="수수료 제외 후 송금할 금액이 부족합니다.", color=0xff6200)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # 실제 송금될 코인 양 (KRW에서 코인으로 변환)
        actual_send_amount_coin = krw_to_coin_amount(actual_send_krw_pre_convert, coin.upper())

        if actual_send_amount_coin < get_minimum_amount_coin(coin.upper()):
            embed = disnake.Embed(title="오류", description=f"최소 송금 수량 미달 (수수료 제외 후)\n최소 {get_minimum_amount_coin(coin.upper()):.6f} {coin_unit} 필요", color=0xff6200)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # --- 거래 정보 저장 ---
        pending_transactions[interaction.author.id] = {
            'krw_amount_input': krw_amount_input, 
            'send_amount_coin': actual_send_amount_coin, 
            'network': network,
            'address': address,
            'coin': coin.upper(),
            'coin_price_usd': coin_price_usd,
            'krw_rate': krw_rate,
            'kimchi_premium': kimchi_premium,
            'actual_krw_rate': actual_krw_rate,
            'total_service_fee_rate': total_service_fee_rate, 
            'service_fee_krw': service_fee_krw, 
            'exchange_fee_krw': exchange_fee_krw, 
            'total_fee_krw': total_fee_krw, 
            'actual_send_krw_equivalent': actual_send_krw_pre_convert 
        }

        # --- 확인 Embed 생성 ---
        embed = disnake.Embed(
            title=f"✅ {coin_unit} 송금 최종 확인",
            color=0x4caf50 # 초록색 계열로 변경
        )

        embed.add_field(
            name="실제 송금 코인 양",
            value=f"**{actual_send_amount_coin:.8f} {coin_unit}**",
            inline=False
        )
        embed.add_field(
            name="차감 금액 (KRW)",
            value=f"**{int(krw_amount_input):,}원** (잔액에서 차감)",
            inline=True
        )
        embed.add_field(
            name="실제 송금 가치 (KRW)",
            value=f"{int(actual_send_krw_pre_convert):,}원",
            inline=True
        )
        embed.add_field(name="\u200B", value="\u200B", inline=False) # 공백 필드

        embed.add_field(
            name="수수료 상세 (KRW)",
            value=f"*서비스 수수료:* {int(service_fee_krw):,}원\n*거래소 수수료:* {int(exchange_fee_krw):,}원\n**총합:** {int(total_fee_krw):,}원",
            inline=True
        ) 
        embed.add_field(
            name="네트워크 / 주소",
            value=f"**{network.upper()}**\n`{address}`",
            inline=True
        )

        custom_emoji1 = PartialEmoji(name="send", id=1439222645035106436)

        send_btn = disnake.ui.Button(
            label="✅ 송금하기",
            style=disnake.ButtonStyle.green, # 초록색 버튼으로 변경
            custom_id="송금하기",
            emoji=custom_emoji1
        )

        view = disnake.ui.View()
        view.add_item(send_btn)

        await interaction.edit_original_response(embed=embed, view=view)
    except Exception as e: 
        print(f"Error in handle_amount_modal: {e}") 
        embed = disnake.Embed(
            title="오류",
            description="처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            color=0xff6200
        )
        # 예외 발생 시에도 defer되었으므로 edit_original_response 사용
        try:
            await interaction.edit_original_response(embed=embed)
        except:
            await interaction.followup.send(embed=embed, ephemeral=True)


async def handle_send_button(interaction: disnake.MessageInteraction):
    """
    송금 버튼 클릭 시 실제 거래 실행 로직
    **수정: 잔액 환불 로직 안정화 및 오류 메시지 개선**
    """
    try:
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.author.id
        user_data = get_verified_user(user_id)
        if not user_data:
            embed = disnake.Embed(title="오류", description="인증되지 않은 고객님 입니다.", color=0xff6200)
            await interaction.edit_original_response(embed=embed, view=None)
            return

        transaction_data = pending_transactions.get(user_id)
        if not transaction_data:
            embed = disnake.Embed(title="오류", description="송금 정보를 찾을 수 없습니다. 다시 시도해주세요.", color=0xff6200)
            await interaction.edit_original_response(embed=embed, view=None)
            return

        krw_amount_to_subtract = transaction_data.get('krw_amount_input', 0)
        send_amount_coin = transaction_data.get('send_amount_coin', 0)
        network = transaction_data.get('network', 'BEP20').lower()
        address = transaction_data.get('address', '')
        coin = transaction_data.get('coin', 'USDT')

        if send_amount_coin <= 0 or krw_amount_to_subtract <= 0 or not address:
            embed = disnake.Embed(title="**오류**", description="**유효하지 않은 거래 정보입니다.**", color=0xff6200)
            await interaction.edit_original_response(embed=embed, view=None)
            return

        processing_embed = disnake.Embed(
            title="**⏳ 송금 처리중...**",
            description="**MEXC 거래소로 송금 요청을 보내고 있습니다. 잠시만 기다려주세요.**",
            color=0x2196f3 # 파란색
        )
        await interaction.edit_original_response(embed=processing_embed, view=None)

        # 1. 사용자 잔액 차감
        if not subtract_balance(user_id, krw_amount_to_subtract):
            embed = disnake.Embed(title="**잔액 부족**", description="**잔액이 부족합니다. 시스템 오류일 경우 관리자에게 문의해주세요.**", color=0xff6200)
            await interaction.edit_original_response(embed=embed, view=None)
            return

        add_transaction_history(user_id, krw_amount_to_subtract, "송금(차감)")
        add_transaction_history(user_id, int(transaction_data.get('service_fee_krw', 0)), "서비스수수료")

        # 2. 실제 MEXC 송금 실행 (Convert/Withdraw 포함)
        transaction_result = simple_send_coin(coin, send_amount_coin, address, network)

        if transaction_result and transaction_result.get('success', False):
            # --- 송금 성공 ---
            coin_name = transaction_result.get('coin', coin.upper())
            txid = transaction_result.get('txid', 'N/A')

            success_embed = disnake.Embed(
                title=f"**🎉 {coin_name} 전송 성공! 🎉**",
                color=0x4caf50
            )
            success_embed.add_field(name="**전송 코인 수량**", value=f"**{send_amount_coin:.8f} {coin_name}**", inline=True)
            success_embed.add_field(name="**차감된 KRW (원금)**", value=f"{int(krw_amount_to_subtract):,}원", inline=True)
            success_embed.add_field(name="**총 수수료**", value=f"{int(transaction_data['total_fee_krw']):,}원", inline=True)
            success_embed.add_field(name="**전송 금액 (KRW 환산)**", value=f"{int(transaction_data['actual_send_krw_equivalent']):,}원", inline=True)
            success_embed.add_field(name="**네트워크**", value=f"{network.upper()}", inline=True)
            success_embed.add_field(name="\u200B", value="\u200B", inline=True) 
            success_embed.add_field(name="**TXID**", value=f"[{txid}]({get_txid_link(txid, coin)})", inline=False)
            success_embed.add_field(name="**보낸주소**", value=f"`{address}`", inline=False)
            success_embed.set_footer(text=f"전송 시간: {transaction_result.get('time', 'N/A')}")

            await interaction.edit_original_response(embed=success_embed, view=None)
            print(f"로그 전송: {user_id}가 {int(krw_amount_to_subtract):,}원 상당의 {send_amount_coin:.6f} {coin}을 {address}로 송금했습니다. TXID: {txid}")

        else:
            # --- 송금 실패: 잔액 환불 ---
            error_message = transaction_result.get('error', '알 수 없는 오류')
            
            # 잔액 환불 처리
            conn = None
            try:
                conn = sqlite3.connect('DB/verify_user.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET now_amount = now_amount + ? WHERE user_id = ?', 
                            (krw_amount_to_subtract, user_id))
                conn.commit()
                add_transaction_history(user_id, krw_amount_to_subtract, "송금실패_환불")
                refund_success = True
            except Exception as refund_e:
                print(f"잔액 환불 중 오류 발생: {refund_e}")
                if conn: conn.rollback()
                refund_success = False
            finally:
                if conn: conn.close()

            refund_embed = disnake.Embed(
                title="**⚠️ 전송 실패**",
                description=f"전송 중 오류가 발생하여 **{int(krw_amount_to_subtract):,}원**이 {'성공적으로 환불되었습니다.' if refund_success else '환불 실패했습니다. 관리자에게 문의해주세요.'}",
                color=0xff6200
            )
            refund_embed.add_field(name="**오류 원인**", value=f"```\n{error_message}\n```", inline=False)
            refund_embed.add_field(name="**요청 코인/금액**", value=f"{coin} / {send_amount_coin:.8f}", inline=True)
            refund_embed.add_field(name="**네트워크/주소**", value=f"{network.upper()} / `{address[:8]}...`", inline=True)


            await interaction.edit_original_response(embed=refund_embed, view=None)
            print(f"송금 실패 로그: {user_id} - 오류: {error_message} (환불: {int(krw_amount_to_subtract):,}원)")

        if user_id in pending_transactions:
            del pending_transactions[user_id]

    except Exception as e:
        print(f"Critical error in handle_send_button: {e}") 
        try:
            embed = disnake.Embed(title="처리 중 예상치 못한 오류 발생", description="직원에게 문의해주세요.", color=0xff6200)
            await interaction.edit_original_response(embed=embed, view=None)
        except:
            pass


# --- MEXC Deposit Check (입고 감지) ---
# **수정: MEXC API 응답 형식에 맞게 데이터 파싱 로직 수정**
async def check_mexc_deposits(bot=None):
    """
    MEXC 입금 내역을 확인하고, 새로운 입금이 있으면 Discord로 로그 전송
    (Discord 봇 객체가 필요하므로 외부에서 `bot` 인수로 전달되어야 합니다.)
    """
    if not API_KEY or not SECRET_KEY:
        print("MEXC API 키가 설정되지 않아 입금 감지 기능을 사용할 수 없습니다.")
        return

    try:
        endpoint = "/api/v3/capital/deposit/hisrec"
        timestamp = int(time.time() * 1000)

        params = {
            'timestamp': timestamp,
            'status': 1, # 1: 성공적인 입금
            'limit': 50,
            'recvWindow': 60000 
        }
        signature = sign_params(params, SECRET_KEY)
        if not signature:
            print("MEXC 입금 감지: API 서명 생성 실패")
            return
        params['signature'] = signature 

        headers = { 'X-MEXC-APIKEY': API_KEY }
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        response.raise_for_status() 

        api_response = response.json()
        
        # MEXC API V3의 입금 내역은 'data' 필드 없이 바로 리스트 반환 (API 문서에 따라 다를 수 있음)
        deposits = api_response if isinstance(api_response, list) else api_response.get('data', [])

        if not deposits:
             # 오류가 아닌 경우 (ex: 입금 내역 없음)
            return

        for deposit in deposits:
            coin_symbol = deposit.get('coin')
            amount = float(deposit.get('amount', 0))
            network = deposit.get('network')
            txid = deposit.get('txId', deposit.get('txid')) # txId 또는 txid

            if amount > 0: 
                # --- DB 비교 로직 필요 ---
                # 실제 구현 시: DB에서 마지막 처리된 TXID와 비교하여 중복 처리 방지
                # -------------------------

                # Discord 로그 전송
                if bot:
                    # await send_deposit_log_to_discord(bot, coin_symbol, amount, network, txid) 
                    pass # 실제 봇 객체를 통해 전송해야 함
                
                print(f"✅ 입금 감지: {coin_symbol} {amount:.6f} on {network}, TXID: {txid}")


    except requests.exceptions.RequestException as e:
        print(f"MEXC 입금 감지 네트워크 오류: {e}")
    except Exception as e:
        print(f"MEXC 입금 감지 중 예상치 못한 오류: {e}")

async def send_deposit_log_to_discord(bot, coin_symbol, amount, network, txid):
    """Discord에 입금 로그를 전송하는 함수 (개념적)"""
    try:
        # 봇 객체를 통해 채널 객체 획득
        deposit_log_channel = bot.get_channel(CHANNEL_DEPOSIT_LOG)

        krw_rate = get_exchange_rate()
        coin_price_usd = get_coin_price(coin_symbol)
        krw_value = amount * coin_price_usd * krw_rate

        embed = disnake.Embed(
            title=f"🛒 입고 완료 ({coin_symbol})",
            description=f"**{amount:.8f} {coin_symbol}** 입고 확인",
            color=0x4caf50 
        )
        embed.add_field(name="입고 금액 (KRW 환산)", value=f"**{int(krw_value):,}원**", inline=False)
        embed.add_field(name="네트워크", value=f"{network}", inline=True)
        embed.add_field(name="TXID", value=f"[{txid}]({get_txid_link(txid, coin_symbol)})", inline=True)
        embed.set_footer(text=f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if deposit_log_channel:
            await deposit_log_channel.send(embed=embed)
            # 여기에서 DB에 입금 내역을 기록하여 중복 처리 방지
        else:
            print(f"Discord 입금 로그 채널을 찾을 수 없습니다. (입금: {coin_symbol} {amount:.6f}, {int(krw_value):,}원, TXID: {txid})")
    except Exception as e:
        print(f"Discord 입금 로그 전송 실패: {e}")


# --- Selenium Functions (기존 로직 유지) ---
def init_coin_selenium():
    return True

def quit_driver():
    pass
