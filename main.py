import disnake
import requests
import time
import hashlib
import hmac
import sqlite3
from datetime import datetime
import urllib.parse
from disnake import PartialEmoji, ui

# 웹훅 사용 제거

# MEXC API 설정
API_KEY = "mxglhHWGbJ"
SECRET_KEY = "13f382a54"
BASE_URL = "https://api.mexc.com"

# 서비스 수수료율 (기본값, get_user_tier_and_fee에서 동적으로 결정될 수 있음)
SERVICE_FEE_RATE = 0.025 

def set_service_fee_rate(rate: float):
    global SERVICE_FEE_RATE
    try:
        if rate < 0 or rate > 0.25:
            return False
        SERVICE_FEE_RATE = rate
        return True
    except Exception:
        return False

def get_service_fee_rate() -> float:
    try:
        return SERVICE_FEE_RATE
    except Exception:
        return 0.025

def sign_params(params, secret):
    try:
        # 파라미터를 알파벳 순으로 정렬 후 쿼리 스트링 생성
        sorted_params = sorted(params.items())
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
        signature = hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        return signature
    except Exception:
        return ""

def get_exchange_rate():
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
        response.raise_for_status()
        data = response.json()
        rate = data.get("rates", {}).get("KRW")
        return rate if rate and rate > 0 else 1350
    except (requests.RequestException, ValueError, KeyError):
        return 1350
    except Exception:
        return 1350

def get_kimchi_premium():
    try:
        upbit_response = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC", timeout=10)
        if upbit_response.status_code == 200:
            upbit_data = upbit_response.json()
            upbit_price = upbit_data[0]['trade_price']
        else:
            return 0
        
        binance_response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10)
        if binance_response.status_code == 200:
            binance_data = binance_response.json()
            binance_price_usd = float(binance_data['price'])
        else:
            return 0
        
        # USD/KRW 환율
        krw_rate = get_exchange_rate()
        if krw_rate <= 0: return 0 # 환율 조회 실패 시

        # 김치프리미엄 계산
        binance_price_krw = binance_price_usd * krw_rate
        kimchi_premium = ((upbit_price - binance_price_krw) / binance_price_krw) * 100
        
        return round(kimchi_premium, 2)
        
    except Exception:
        return 0

def get_coin_price(coin_symbol):
    """특정 코인의 현재 가격을 USD로 조회 (업비트 우선, MEXC 백업)"""
    if coin_symbol.upper() == 'USDT':
        return 1.0 # USDT는 항상 $1

    try:
        # 업비트에서 가격 조회 시도
        upbit_price = get_upbit_coin_price(coin_symbol)
        if upbit_price > 0:
            return upbit_price
    except Exception:
        pass # 업비트 조회 실패 시 MEXC로 넘어감
        
    # 업비트 실패 시 MEXC에서 조회
    endpoint = "/api/v3/ticker/price"
    params = {'symbol': f"{coin_symbol.upper()}USDT"} # symbol은 대문자로
    
    response = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        return float(data.get('price', 0))
    else:
        return 0
    except (requests.RequestException, ValueError, KeyError):
        return 0
    except Exception:
        return 0

def get_upbit_coin_price(coin_symbol):
    """업비트에서 코인 가격을 USD로 조회"""
    try:
        # 업비트 코인 매핑 (USD 페어가 아니라 KRW 페어를 조회)
        upbit_mapping = {
            'USDT': 'USDT-KRW',
            'BNB': 'BNB-KRW', 
            'TRX': 'TRX-KRW',
            'LTC': 'LTC-KRW'
        }
        
        if coin_symbol.upper() == 'USDT':
            return 1.0 # USDT는 $1로 고정 가정

        upbit_symbol_for_url = upbit_mapping.get(coin_symbol.upper())
        if not upbit_symbol_for_url:
            return 0 # 지원하지 않는 코인
        
        # 업비트 API 호출 (KRW 마켓)
        # 예: KRW-BTC, KRW-ETH 형태
        url = f"https://api.upbit.com/v1/ticker?markets=KRW-{coin_symbol.upper()}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                krw_price = float(data[0].get('trade_price', 0))
                # KRW를 USD로 변환
                usd_krw_rate = get_exchange_rate()
                if usd_krw_rate > 0:
                    usd_price = krw_price / usd_krw_rate
                    return usd_price
        return 0
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return 0
    except Exception:
        return 0

def get_mexc_coin_price(coin_symbol):
    """MEXC에서 코인 가격 조회 (백업용)"""
    try:
        endpoint = "/api/v3/ticker/price"
        params = {'symbol': f"{coin_symbol.upper()}USDT"} # symbol은 대문자로
        
        response = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return float(data.get('price', 0))
        else:
            return 0
    except (requests.RequestException, ValueError, KeyError):
        return 0
    except Exception:
        return 0

def get_all_coin_prices():
    """모든 지원 코인의 현재 가격을 조회 (업비트 우선, MEXC 백업)"""
    try:
        prices = {}
        supported_coins = ['USDT', 'TRX', 'LTC', 'BNB']
        
        # 각 코인별로 업비트에서 가격 조회 시도
        for coin in supported_coins:
            prices[coin] = get_coin_price(coin) # get_coin_price에서 USDT 1.0 처리됨
        
        return prices
    except Exception:
        return {}

def mexc_swap_coins(from_coin, to_coin, amount):
    """MEXC Convert 시뮬레이션: from_coin을 to_coin으로 변환"""
    # 실제 MEXC에는 'Convert' API가 명확히 제공되지 않으며, 현물 거래 API를 통해 이루어짐.
    # 사용자의 요청에 따라 Convert 로직을 시뮬레이션합니다.
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
        
        # From 코인을 USDT 가치로 변환
        usdt_value = amount * from_price
        
        # USDT 가치를 To 코인으로 변환
        converted_amount_before_fee = usdt_value / to_price
        
        # 스왑 수수료 적용 (예: 0.1%)
        swap_fee_rate = 0.001
        final_amount = converted_amount_before_fee * (1 - swap_fee_rate)
        
        print(f"Debug: {from_coin.upper()} {amount:.6f} → {to_coin.upper()} {final_amount:.6f} (시뮬레이션, 수수료: {swap_fee_rate * 100:.1f}%)")
        
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
    return coin_fees.get(network.upper(), 0.0) # 기본 0.0 수수료 (조회 불가 시)

def send_coin_transaction(amount, address, network, coin='USDT', skip_min_check=False, skip_address_check=False):
    """MEXC에서 코인 송금 (출금)"""
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키가 설정되지 않았습니다'}
    
    # MEXC 최소 송금 금액 확인 (skip_min_check가 True면 건너뛰기)
    if not skip_min_check:
        min_amount = get_minimum_amount_coin(coin.upper())
        # KRW로 변환된 최소 금액은 여기서는 불필요. 코인 단위로만 체크
        
        if amount < min_amount:
            return {'success': False, 'error': f'최소 송금 금액 미달: 약 {min_amount:.6f} {coin.upper()} 필요'}
    
    # 네트워크 매핑 (MEXC API 기준)
    network_mapping = {
        'bep20': 'BSC',      # BSC 네트워크 (BEP20)
        'trc20': 'TRX',      # TRON 네트워크 (TRC20)
        'ltc': 'LTC',        # Litecoin 네트워크
        'bnb': 'BSC'         # BSC 네트워크 (BNB)
    }
    
    network_code = network_mapping.get(network.lower())
    if not network_code:
        return {'success': False, 'error': f'지원하지 않는 네트워크: {network}'}
    
    # 디버깅을 위한 로그 (실제 운영 시에는 제거)
    print(f"Debug: Coin={coin}, Network={network}, NetworkCode={network_code}, Amount={amount}, Address={address}")
    
    try:
        endpoint = "/api/v3/capital/withdraw"
        timestamp = int(time.time() * 1000)
        
        params = {
            'coin': coin.upper(),
            'address': str(address).strip(),
            'amount': f"{amount:.8f}", # 정밀도 유지
            'network': network_code, # MEXC API V3는 'network' 파라미터 사용
            'recvWindow': 60000,
            'timestamp': timestamp
        }
        
        signature = sign_params(params, SECRET_KEY)
        if not signature:
            return {'success': False, 'error': 'API 서명 생성 실패'}
            
        params['signature'] = signature
        
        headers = {
            'X-MEXC-APIKEY': API_KEY
        }
        
        response = requests.post(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=30)
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생
        
        data = response.json()
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
            error_msg = data.get('msg', '알 수 없는 거래소 오류')
            return {'success': False, 'error': f'거래소 오류: {error_msg}'}
            
    except requests.exceptions.RequestException as e:
        error_details = ""
        if hasattr(e, 'response') and e.response is not None:
            try: error_details = e.response.json()
            except: error_details = e.response.text[:200]
        return {'success': False, 'error': f'네트워크 또는 API 통신 오류: {str(e)} ({error_details})'}
    except Exception as e:
        return {'success': False, 'error': f'예상치 못한 오류: {str(e)}'}

def simple_send_coin(target_coin, amount, address, network):
    """
    모든 코인 재고를 활용하여 목표 코인으로 Convert 후 송금 시도
    1. 목표 코인이 충분하면 바로 송금
    2. 목표 코인 부족 시:
       a. USDT 잔액이 충분하면 USDT를 목표 코인으로 Convert 후 송금 (시뮬레이션)
       b. USDT도 부족하면 다른 코인(BNB, TRX, LTC)을 USDT로 Convert 후, 그 USDT를 목표 코인으로 Convert 후 송금 (시뮬레이션)
    """
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키가 설정되지 않았습니다.'}

    try:
        balances = get_all_balances()
        prices = get_all_coin_prices() # 모든 코인의 USD 가격
        target_balance = balances.get(target_coin.upper(), 0)
        target_coin_price_usd = prices.get(target_coin.upper(), 0)

        # 목표 코인 가격 조회 실패 시
        if target_coin_price_usd <= 0:
            return {'success': False, 'error': f'목표 코인 {target_coin.upper()}의 가격을 조회할 수 없습니다.'}

        print(f"Debug: 목표 코인={target_coin.upper()}, 필요량={amount:.6f}, 현재 잔액={target_balance:.6f}")

        # 1. 목표 코인이 충분하면 바로 송금
        if target_balance >= amount:
            print(f"Debug: {target_coin.upper()} 잔액 충분, 바로 송금 진행")
            return send_coin_transaction(amount, address, network, target_coin)

        # 2. 목표 코인이 부족하면 다른 코인 활용 로직
        #   a. 필요한 USDT 양 계산 (목표 코인 양 * 목표 코인 USD 가격)
        needed_usdt_value = amount * target_coin_price_usd
        current_usdt_balance = balances.get('USDT', 0)
        total_usdt_after_conversions = current_usdt_balance
        
        convert_log = []
        
        # 2.b. 보유 코인들을 USDT로 전환 시도 (BNB, TRX, LTC 순)
        convert_priority = ['BNB', 'TRX', 'LTC'] 
        
        for coin_to_convert in convert_priority:
            if total_usdt_after_conversions >= needed_usdt_value:
                break # 이미 충분한 USDT를 확보했다면 추가 변환 불필요

            coin_balance = balances.get(coin_to_convert, 0)
            if coin_balance <= 0:
                continue

            # 이 코인을 USDT로 변환 (시뮬레이션)
            print(f"Debug: {coin_to_convert} {coin_balance:.6f}을 USDT로 Convert 시도 (시뮬레이션)")
            convert_result = mexc_swap_coins(coin_to_convert, 'USDT', coin_balance)
            
            if convert_result and convert_result.get('success', False):
                converted_usdt = convert_result.get('swapped_amount', 0)
                total_usdt_after_conversions += converted_usdt
                convert_log.append(f"  {coin_to_convert} {coin_balance:.6f} → USDT {converted_usdt:.6f} (Fee: {converted_usdt * convert_result.get('fee_rate',0):.6f} USDT)")
                print(f"Debug: {coin_to_convert} Convert 성공, 현재 확보된 USDT: {total_usdt_after_conversions:.6f}")
            else:
                error_msg = convert_result.get('error', 'Convert 실패') if convert_result else 'Convert 실패'
                convert_log.append(f"  {coin_to_convert} Convert 실패: {error_msg}")
                print(f"Debug: {coin_to_convert} Convert 실패: {error_msg}")
        
        print(f"Debug: 총 확보된 USDT (변환 후): {total_usdt_after_conversions:.6f}, 필요한 USDT 가치: {needed_usdt_value:.6f}")

        # 2.c. 최종 확보된 USDT로 목표 코인으로 Convert 시도
        if total_usdt_after_conversions >= needed_usdt_value:
            # 필요한 만큼의 USDT를 목표 코인으로 변환 (시뮬레이션)
            usdt_to_convert_for_target = needed_usdt_value # 필요한 USDT만큼만 변환
            
            print(f"Debug: 확보된 USDT {total_usdt_after_conversions:.6f}로 {target_coin.upper()} {amount:.6f} 생성 시도 (USDT {usdt_to_convert_for_target:.6f} 필요)")
            convert_to_target_result = mexc_swap_coins('USDT', target_coin.upper(), usdt_to_convert_for_target)

            if convert_to_target_result and convert_to_target_result.get('success', False):
                final_target_amount = convert_to_target_result.get('swapped_amount', 0)
                convert_log.append(f"  USDT {usdt_to_convert_for_target:.6f} → {target_coin.upper()} {final_target_amount:.6f} (Fee: {convert_to_target_result.get('fee_amount_in_target_coin',0):.6f} {target_coin.upper()})")
                print(f"Debug: 최종 {target_coin.upper()} 확보량: {final_target_amount:.6f}")

                if final_target_amount >= amount:
                    # 최종 목표 코인 확보 및 송금
                    return send_coin_transaction(amount, address, network, target_coin)
                else:
                    # Convert 후에도 목표량 미달 (수수료 등 고려)
                    debug_msg = "\n".join(convert_log)
                    return {'success': False, 'error': f'코인 변환 후에도 {target_coin.upper()} 잔액이 부족합니다.\n{debug_msg}\n(최종 확보량: {final_target_amount:.6f} {target_coin.upper()}, 필요량: {amount:.6f})'}
            else:
                error_msg = convert_to_target_result.get('error', 'Convert 실패') if convert_to_target_result else 'Convert 실패'
                debug_msg = "\n".join(convert_log)
                return {'success': False, 'error': f'USDT를 {target_coin.upper()}로 변환 실패: {error_msg}\n{debug_msg}'}
        else:
            # 모든 코인을 USDT로 변환해도 목표 USDT 가치에 미달
            debug_msg = "\n".join(convert_log)
            return {'success': False, 'error': f'모든 코인을 변환해도 필요한 USDT를 확보하지 못했습니다.\n{debug_msg}\n(확보 USDT: {total_usdt_after_conversions:.6f}, 필요 USDT: {needed_usdt_value:.6f})'}

    except Exception as e:
        return {'success': False, 'error': f'자동 Convert/송금 오류: {str(e)}'}

def get_balance(coin='USDT'):
    if not API_KEY or not SECRET_KEY:
        return "0"
    
    try:
        endpoint = "/api/v3/account"
        timestamp = int(time.time() * 1000)
        
        params = {
            'timestamp': timestamp
        }
        
        signature = sign_params(params, SECRET_KEY)
        if not signature:
            return "0"
            
        params['signature'] = signature
        
        headers = {
            'X-MEXC-APIKEY': API_KEY
        }
        
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            balances = data.get('balances', [])
            
            for balance in balances:
                if balance.get('asset') == coin.upper():
                    free_balance = float(balance.get('free', 0))
                    return str(max(0, free_balance))
            
            return "0"
        else:
            return "0"
            
    except (requests.RequestException, ValueError, KeyError):
        return "0"
    except Exception:
        return "0"

def get_all_balances():
    """모든 지원 코인의 잔액을 조회"""
    if not API_KEY or not SECRET_KEY:
        return {}
    
    try:
        endpoint = "/api/v3/account"
        timestamp = int(time.time() * 1000)
        
        params = {
            'timestamp': timestamp
        }
        
        signature = sign_params(params, SECRET_KEY)
        if not signature:
            return {}
            
        params['signature'] = signature
        
        headers = {
            'X-MEXC-APIKEY': API_KEY
        }
        
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            balances = data.get('balances', [])
            
            supported_coins = ['USDT', 'TRX', 'LTC', 'BNB']
            result = {coin: 0.0 for coin in supported_coins} # 기본값 0.0으로 초기화
            
            for balance in balances:
                asset = balance.get('asset', '')
                if asset in supported_coins:
                    free_balance = float(balance.get('free', 0))
                    result[asset] = max(0, free_balance)
            return result
        else:
            return {}
            
    except (requests.RequestException, ValueError, KeyError):
        return {}
    except Exception:
        return {}

def get_verified_user(user_id):
    try:
        conn = sqlite3.connect('DB/verify_user.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    except (sqlite3.Error, OSError):
        return None
    except Exception:
        return None

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
    except (sqlite3.Error, OSError):
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return False
    except Exception:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return False
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def add_transaction_history(user_id, amount, transaction_type):
    conn = None
    try:
        conn = sqlite3.connect('DB/history.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO transaction_history (user_id, amount, type) VALUES (?, ?, ?)', 
                      (user_id, amount, transaction_type))
        conn.commit()
    except (sqlite3.Error, OSError):
        pass
    except Exception:
        pass
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def get_txid_link(txid, coin='USDT'):
    try:
        if txid and len(str(txid)) > 0:
            # 코인별 블록 익스플로러 링크
            explorer_links = {
                'USDT': f"https://bscscan.com/tx/{txid}", # BEP20 USDT
                'BNB': f"https://bscscan.com/tx/{txid}",  # BEP20 BNB
                'TRX': f"https://tronscan.org/#/transaction/{txid}", # TRC20 TRX
                'LTC': f"https://blockchair.com/litecoin/transaction/{txid}" # Litecoin
            }
            return explorer_links.get(coin.upper(), f"https://bscscan.com/tx/{txid}") # 기본은 BSCScan
        return "https://bscscan.com/" # TXID 없을 때 기본 링크
    except Exception:
        return "https://bscscan.com/"

def get_minimum_amounts_krw():
    """최소 송금 금액을 KRW로 변환하여 반환"""
    min_amounts = {
        'USDT': 10,     # 10 USDT
        'TRX': 10,      # 10 TRX
        'LTC': 0.015,   # 0.015 LTC
        'BNB': 0.008    # 0.008 BNB
    }
    
    prices = get_all_coin_prices()
    krw_rate = get_exchange_rate()
    kimchi_premium = get_kimchi_premium()
    actual_krw_rate = krw_rate * (1 + kimchi_premium / 100) # 김프 반영된 실제 KRW 환율
    
    min_amounts_krw = {}
    for coin, min_amount_coin_unit in min_amounts.items():
        coin_price = prices.get(coin, 0)
        if coin_price > 0 and actual_krw_rate > 0:
            krw_value = min_amount_coin_unit * coin_price * actual_krw_rate
            min_amounts_krw[coin] = int(krw_value)
        else:
            min_amounts_krw[coin] = 0
    
    return min_amounts_krw

# ===== Tier/Fees Helpers =====
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
            pass # DB 연결 실패 시 total_amount 0으로 유지
        finally:
            if conn: conn.close()

        if total_amount >= 10_000_000:
            return ('VIP', 0.03, 0.01) # VIP: 서비스 수수료 3%, 구매 보너스 1%
        else:
            return ('BUYER', 0.05, 0.0) # BUYER: 서비스 수수료 5%, 구매 보너스 0%
    except Exception:
        return ('BUYER', 0.05, 0.0) # 오류 발생 시 기본 BUYER 등급

def get_minimum_amount_coin(coin_symbol):
    """특정 코인의 최소 송금 금액을 코인 단위로 반환"""
    min_amounts = {
        'USDT': 10,     # 10 USDT
        'TRX': 10,      # 10 TRX
        'LTC': 0.015,   # 0.015 LTC
        'BNB': 0.008    # 0.008 BNB
    }
    
    return min_amounts.get(coin_symbol.upper(), 10.0)

def krw_to_coin_amount(krw_amount, coin_symbol):
    """KRW 금액을 코인 단위로 변환"""
    krw_rate = get_exchange_rate()
    coin_price = get_coin_price(coin_symbol.upper())
    kimchi_premium = get_kimchi_premium()
    actual_krw_rate = krw_rate * (1 + kimchi_premium / 100) # 김프 반영된 실제 KRW 환율

    if actual_krw_rate <= 0 or coin_price <= 0:
        return 0.0 # 환율 또는 코인 가격 조회 실패 시 0 반환
        
    # KRW → USD (김프 반영) → Coin
    return krw_amount / (actual_krw_rate * coin_price)

class AmountModal(disnake.ui.Modal):
    def init(self, network, coin='usdt'): # __init__ 대신 init 사용 유지
        self.network = network
        self.coin = coin
        
        # 실시간 최소송금 금액 조회
        min_amounts_krw = get_minimum_amounts_krw()
        min_krw = min_amounts_krw.get(coin.upper(), 10000)
        
        # 코인별 단위 정보
        coin_info = {
            'usdt': {'unit': 'USDT'},
            'trx': {'unit': 'TRX'},
            'ltc': {'unit': 'LTC'},
            'bnb': {'unit': 'BNB'}
        }
        
        info = coin_info.get(coin.lower(), coin_info['usdt'])
        
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
        super().init(
            title=f"{info['unit']} 송금 정보",
            custom_id=f"amount_modal_{network}_{coin}",
            components=components,
        )

class ChargeModal(disnake.ui.Modal):
    def init(self): # __init__ 대신 init 사용 유지
        components = [
            disnake.ui.TextInput(
                label="충전 금액",
                placeholder="충전하실 금액을 적어주세요. ( 최소 500원 )",
                custom_id="charge_amount",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=15,
            )
        ]
        super().init(
            title="충전 금액 입력",
            custom_id="charge_modal",
            components=components,
        )

custom_emoji11 = PartialEmoji(name="47311ltc", id=1438899347453509824)
custom_emoji12 = PartialEmoji(name="6798bnb", id=1438899349110390834)
custom_emoji13 = PartialEmoji(name="tron", id=1438899350582591701)
custom_emoji14 = PartialEmoji(name="7541tetherusdt", id=1439510997730721863)

class CoinDropdown(disnake.ui.Select):
    def init(self): # __init__ 대신 init 사용 유지
        options = [
            disnake.SelectOption(label="USDT", description="테더코인 선택", value="usdt", emoji=custom_emoji14),
            disnake.SelectOption(label="TRX", description="트론 선택", value="trx", emoji=custom_emoji13),
            disnake.SelectOption(label="LTC", description="라이트코인 선택", value="ltc", emoji=custom_emoji11),
            disnake.SelectOption(label="BNB", description="바이낸스코인 선택", value="bnb", emoji=custom_emoji12)
        ]
        super().init(placeholder="송금할 코인을 선택해주세요", options=options)

    async def callback(self, interaction):
        try:
            # Avoid timeout by deferring first
            await interaction.response.defer(ephemeral=True)
            user_data = get_verified_user(interaction.author.id)
            if not user_data:
                embed = disnake.Embed(
                    title="**오류**",
                    description="**인증되지 않은 고객님입니다.**",
                    color=0xff6200
                )
                await interaction.edit_original_response(embed=embed)
                return
                
            # 최소송금 금액 안내
            selected_coin = self.values[0]
            
            # 실시간 최소 송금 금액 조회
            min_amounts_krw = get_minimum_amounts_krw()
            min_krw = min_amounts_krw.get(selected_coin.upper(), 10000)
            min_amount = f"{min_krw:,}"
                
            embed = disnake.Embed(
                title=f"**{selected_coin.upper()} 송금**",
                description=f"**최소 송금 금액 = {min_amount}원**",
                color=0xffffff
            )
            view = disnake.ui.View()
            view.add_item(NetworkDropdown(selected_coin))
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            embed = disnake.Embed(
                title="**오류**",
                description="**처리 중 오류가 발생했습니다.**",
                color=0xff6200
            )
            try:
                await interaction.edit_original_response(embed=embed)
            except:
                pass

class NetworkDropdown(disnake.ui.Select):
    def init(self, selected_coin): # __init__ 대신 init 사용 유지
        self.selected_coin = selected_coin
        
        # 코인별 지원 네트워크
        network_options = {
            'usdt': [
                disnake.SelectOption(label="BEP20", description="BSC Network", value="bep20"),
                disnake.SelectOption(label="TRC20", description="TRON Network", value="trc20")
            ],
            'trx': [
                disnake.SelectOption(label="TRC20", description="TRON Network", value="trc20")
            ],
            'ltc': [
                disnake.SelectOption(label="LTC", description="Litecoin Network", value="ltc")
            ],
            'bnb': [
            disnake.SelectOption(label="BEP20", description="BSC Network", value="bep20")
        ]
        }
        
        options = network_options.get(selected_coin.lower(), [
            disnake.SelectOption(label="BEP20", description="BSC Network", value="bep20")
        ])
        
        super().init(placeholder="네트워크를 선택해주세요", options=options)

    async def callback(self, interaction):
        try:
            await interaction.response.send_modal(AmountModal(self.values[0], self.selected_coin))
        except Exception as e:
            try:
                embed = disnake.Embed(
                    title="**오류**",
                    description="**처리 중 오류가 발생했습니다.**",
                    color=0x26272f
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception:
                try:
                    await interaction.edit_original_response(embed=embed)
                except Exception:
                    pass

pending_transactions = {}

async def handle_amount_modal(interaction):
    try:
        # 응답 지연 (3초 제한 해결)
        await interaction.response.defer(ephemeral=True)
        
        amount_str = interaction.text_values.get("amount", "").strip()
        address = interaction.text_values.get("address", "").strip()
        
        if not amount_str or not address:
            embed = disnake.Embed(
                title="**오류**",
                description="**모든 필드를 입력해주세요.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        try:
            krw_amount_input = float(amount_str) # 사용자가 입력한 KRW 금액
            if krw_amount_input <= 0:
                raise ValueError("양수여야 합니다")
        except (ValueError, TypeError):
            embed = disnake.Embed(
                title="**오류**",
                description="**올바른 숫자를 입력해주세요.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        # 커스텀 ID에서 코인과 네트워크 정보 추출
        custom_id_parts = interaction.custom_id.split('_')
        network = custom_id_parts[-2] if len(custom_id_parts) >= 3 else "bep20"
        coin = custom_id_parts[-1] if len(custom_id_parts) >= 4 else "usdt"
        
        # 통일된 최소 송금 금액 조회
        min_amounts_krw = get_minimum_amounts_krw()
        min_amount_krw = min_amounts_krw.get(coin.upper(), 10000)
        coin_unit = coin.upper()
        
        if krw_amount_input < min_amount_krw:
            embed = disnake.Embed(
                title="**오류**",
                description=f"**출금 최소 금액은 {min_amount_krw:,}원입니다.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        user_data = get_verified_user(interaction.author.id)
        if not user_data:
            embed = disnake.Embed(
                title="**오류**",
                description="**인증되지 않은 고객님 입니다.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        current_balance = user_data[6] if len(user_data) > 6 else 0
        if current_balance < krw_amount_input:
            embed = disnake.Embed(
                title="**잔액 부족**",
                description=f"**보유 금액 = {current_balance:,}원\n필요금액: {int(krw_amount_input):,}원**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        # --- 수수료 계산 로직 ---
        # 1. 환율 및 김치프리미엄 조회
        krw_rate = get_exchange_rate()
        coin_price_usd = get_coin_price(coin.upper())
        kimchi_premium = get_kimchi_premium()
        actual_krw_rate = krw_rate * (1 + kimchi_premium / 100) # 김프 반영된 실제 KRW 당 USD 환율

        if coin_price_usd <= 0 or actual_krw_rate <= 0:
            embed = disnake.Embed(title="**오류**", description="**코인 가격 또는 환율 정보를 조회할 수 없습니다.**", color=0xff6200)
            await interaction.edit_original_response(embed=embed)
            return

        # 2. 서비스 수수료 계산
        user_tier, service_fee_base_rate, _ = get_user_tier_and_fee(interaction.author.id)
        # 서비스 수수료: 티어별 기본 수수료율 + 김치프리미엄
        total_service_fee_rate = service_fee_base_rate + (kimchi_premium / 100)
        service_fee_krw = krw_amount_input * total_service_fee_rate # 사용자가 입력한 KRW 기준

        # 3. 거래소 송금 수수료 (코인 -> KRW)
        transaction_fee_coin = get_transaction_fee(coin.upper(), network.upper())
        exchange_fee_krw = transaction_fee_coin * coin_price_usd * actual_krw_rate # 코인 단위 수수료를 KRW로 변환

        # 4. 최종 송금에 필요한 총 KRW 금액
        # 사용자가 입력한 krw_amount_input (이것이 봇 시스템에서 차감되는 금액)
        # 이 금액에서 수수료를 제외하고 실제 코인으로 변환되어 송금
        total_fee_krw = service_fee_krw + exchange_fee_krw
        actual_send_krw_pre_convert = krw_amount_input - total_fee_krw

        if actual_send_krw_pre_convert <= 0:
            embed = disnake.Embed(title="**오류**", description="**수수료 제외 후 송금할 금액이 부족합니다.**", color=0xff6200)
            await interaction.edit_original_response(embed=embed)
            return

        # 실제 송금될 코인 양 (KRW에서 코인으로 변환)
        actual_send_amount_coin = krw_to_coin_amount(actual_send_krw_pre_convert, coin.upper())

        if actual_send_amount_coin < get_minimum_amount_coin(coin.upper()):
            embed = disnake.Embed(title="**오류**", description="**최소 송금 수량 미달 (수수료 제외 후)**", color=0xff6200)
            await interaction.edit_original_response(embed=embed)
            return

        pending_transactions[interaction.author.id] = {
            'krw_amount_input': krw_amount_input, # 사용자가 입력한 원금 (이 금액이 사용자에게서 차감됨)
            'send_amount_coin': actual_send_amount_coin, # 실제 송금할 코인 양 (수수료 제외 후)
            'network': network,
            'address': address,
            'coin': coin.upper(),
            'coin_price_usd': coin_price_usd,
            'krw_rate': krw_rate,
            'kimchi_premium': kimchi_premium,
            'actual_krw_rate': actual_krw_rate,
            'total_service_fee_rate': total_service_fee_rate, # 총 서비스 수수료율 (기본 + 김프)
            'service_fee_krw': service_fee_krw, # KRW 기준 서비스 수수료
            'exchange_fee_krw': exchange_fee_krw, # KRW 기준 거래소 송금 수수료
            'total_fee_krw': total_fee_krw, # KRW 기준 총 수수료
            'actual_send_krw_equivalent': actual_send_krw_pre_convert # KRW 기준 실제 송금 금액 (수수료 제외 후)
        }
        
        embed = disnake.Embed(
            color=0xffffff
        )
        
        # 송금 금액 정보 (김치프리미엄 적용)
        embed.add_field(
            name="**실제 송금 금액**",
            value=f"```{actual_send_amount_coin:.6f} {coin_unit}\n{int(actual_send_krw_pre_convert):,}원```",
            inline=True
        )
        embed.add_field(
            name="**종합 수수료**",
            value=f"```서비스 = {int(service_fee_krw):,}원\n거래소 = {int(exchange_fee_krw):,}원\n총합 = {int(total_fee_krw):,}원```",
            inline=True
        ) 
        embed.add_field(
            name="**네트워크**",
            value=f"```{network.upper()}```",
            inline=True
        )
        embed.add_field(
            name="**코인 주소**",
            value=f"```{address}```",
            inline=False
        )
        
        custom_emoji1 = PartialEmoji(name="send", id=1439222645035106436)

        send_btn = disnake.ui.Button(
            label="송금하기",
            style=disnake.ButtonStyle.gray,
            custom_id="송금하기",
            emoji=custom_emoji1
        )
        
        view = disnake.ui.View()
        view.add_item(send_btn)
        
        # 최초 defer 후에는 원본 응답 수정으로 전송
        await interaction.edit_original_response(embed=embed, view=view)
        
    except Exception as e: # 오류 상세 출력을 위한 변경
        print(f"Error in handle_amount_modal: {e}") 
        embed = disnake.Embed(
            title="**오류**",
            description="**처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.**",
            color=0xff6200
        )
        await interaction.edit_original_response(embed=embed)

async def handle_send_button(interaction):
    try:
        # 응답 지연 (3초 제한 해결)
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.author.id
        user_data = get_verified_user(user_id)
        if not user_data:
            embed = disnake.Embed(
                title="**오류**",
                description="**인증되지 않은 고객님 입니다.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        transaction_data = pending_transactions.get(user_id)
        if not transaction_data:
            embed = disnake.Embed(
                title="**오류**",
                description="**송금 정보를 찾을 수 없습니다. 다시 시도해주세요.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        krw_amount_to_subtract = transaction_data.get('krw_amount_input', 0) # 사용자에게서 차감할 원금
        send_amount_coin = transaction_data.get('send_amount_coin', 0) # 실제 보낼 코인 양
        network = transaction_data.get('network', 'BEP20').lower()
        address = transaction_data.get('address', '')
        coin = transaction_data.get('coin', 'USDT')

        if send_amount_coin <= 0 or krw_amount_to_subtract <= 0 or not address:
            embed = disnake.Embed(
                title="**오류**",
                description="**유효하지 않은 거래 정보입니다.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        processing_embed = disnake.Embed(
            title="**송금 처리중**",
            description="**조금만 기다려주세요.**",
            color=0xffffff
        )
        await interaction.edit_original_response(embed=processing_embed)
        
        if not subtract_balance(user_id, krw_amount_to_subtract):
            embed = disnake.Embed(
                title="**잔액 부족**",
                description="**잔액이 부족합니다. 시스템 오류일 경우 관리자에게 문의해주세요.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        add_transaction_history(user_id, krw_amount_to_subtract, "송금(차감)")
        # 서비스 수수료도 거래 내역에 별도로 기록 가능 (선택 사항)
        add_transaction_history(user_id, int(transaction_data.get('service_fee_krw', 0)), "서비스수수료")
        
        # 실제 MEXC 송금 (simple_send_coin은 자동 스왑 로직 포함)
        transaction_result = simple_send_coin(coin, send_amount_coin, address, network)
        
        if transaction_result and transaction_result.get('success', False):
            coin_name = transaction_result.get('coin', coin.upper())
            txid = transaction_result.get('txid', 'N/A')

            success_embed = disnake.Embed(
                title=f"**🎉 {coin_name} 전송 성공! 🎉**",
                color=0xffffff
            )
            success_embed.add_field(name="**전송 코인 수량**", value=f"```{send_amount_coin:.6f} {coin_name}```", inline=True)
            success_embed.add_field(name="**전송 금액 (KRW 환산)**", value=f"```{int(transaction_data['actual_send_krw_equivalent']):,}원```", inline=True)
            success_embed.add_field(name="**차감된 KRW**", value=f"```{int(krw_amount_to_subtract):,}원```", inline=True)
            success_embed.add_field(name="**서비스 수수료**", value=f"```{int(transaction_data['service_fee_krw']):,}원```", inline=True)
            success_embed.add_field(name="**거래소 수수료**", value=f"```{int(transaction_data['exchange_fee_krw']):,}원```", inline=True)
            success_embed.add_field(name="**총 수수료**", value=f"```{int(transaction_data['total_fee_krw']):,}원```", inline=True)
            success_embed.add_field(name="**네트워크**", value=f"```{network.upper()}```", inline=False)
            success_embed.add_field(name="**TXID**", value=f"[`{txid}`]({transaction_result.get('share_link', 'https://bscscan.com/')})", inline=False) # TXID 링크로 표시
            success_embed.add_field(name="**보낸주소**", value=f"```{address}```", inline=False)
            success_embed.add_field(name="**보낸시간**", value=f"```{transaction_result.get('time', 'N/A')}```", inline=False)
            
            await interaction.edit_original_response(embed=success_embed)
            
            # --- 로그 채널 전송 (실제 봇 실행 시 'bot' 객체 임포트 필요) ---
            try:
                # from bot import CHANNEL_ADMIN_LOG, CHANNEL_PURCHASE_LOG, bot as _bot
                # admin_ch = _bot.get_channel(CHANNEL_ADMIN_LOG)
                # purchase_ch = _bot.get_channel(CHANNEL_PURCHASE_LOG)
                
                # if admin_ch:
                #     t_embed = disnake.Embed(title="코인 전송 내역", color=0x26272f)
                #     t_embed.add_field(name="이용 유저", value=f"{interaction.author.mention} ({interaction.author.id})", inline=False)
                #     t_embed.add_field(name="총 차감금액", value=f"{int(krw_amount_to_subtract):,}원", inline=True)
                #     t_embed.add_field(name="실제 전송 KRW 환산", value=f"{int(transaction_data['actual_send_krw_equivalent']):,}원", inline=True)
                #     t_embed.add_field(name="서비스 수수료", value=f"{int(transaction_data['service_fee_krw']):,}원", inline=True)
                #     t_embed.add_field(name="거래소 수수료", value=f"{int(transaction_data['exchange_fee_krw']):,}원", inline=True)
                #     t_embed.add_field(name="TXID", value=txid, inline=False)
                #     t_embed.add_field(name="네트워크", value=network.upper(), inline=True)
                #     t_embed.add_field(name="보낸주소", value=address, inline=False)
                #     await admin_ch.send(embed=t_embed)

                # if purchase_ch:
                #     from bot import send_purchase_log # 예시
                #     await send_purchase_log(user_id, coin, int(krw_amount_to_subtract))
                print(f"로그 전송: {user_id}가 {int(krw_amount_to_subtract):,}원 상당의 {send_amount_coin:.6f} {coin}을 {address}로 송금했습니다. TXID: {txid}")
            except Exception as log_e:
                print(f"로그 전송 실패: {log_e}")
            
            if user_id in pending_transactions:
                del pending_transactions[user_id]
                
        else:
            error_message = transaction_result.get('error', '알 수 없는 오류')
            
            # 실패 시 사용자 잔액 환불
            conn = None
            try:
                conn = sqlite3.connect('DB/verify_user.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET now_amount = now_amount + ? WHERE user_id = ?', 
                              (krw_amount_to_subtract, user_id))
                conn.commit()
                add_transaction_history(user_id, krw_amount_to_subtract, "송금실패_환불")
            except (sqlite3.Error, OSError) as refund_e:
                print(f"잔액 환불 중 오류 발생 (DB): {refund_e}")
                if conn: conn.rollback()
            except Exception as refund_e:
                print(f"잔액 환불 중 오류 발생 (일반): {refund_e}")
                if conn: conn.rollback()
            finally:
                if conn: conn.close()
            
            refund_embed = disnake.Embed(
                title="**전송 실패**",
                description=f"전송 중 오류가 발생하여 {int(krw_amount_to_subtract):,}원이 환불되었습니다.",
                color=0xff6200
            )
            refund_embed.add_field(
                name="**오류 원인**",
                value=f"```{error_message}```",
                inline=False
            )
            refund_embed.add_field(
                name="**요청 요약**",
                value=f"```코인: {coin}\n네트워크: {network}\n보낼양: {send_amount_coin:.8f} {coin}\n주소: {address[:6]}...{address[-6:] if len(address)>12 else address}```",
                inline=False
            )
            
            await interaction.edit_original_response(embed=refund_embed)
            
            if user_id in pending_transactions:
                del pending_transactions[user_id]
            
            # --- 실패 로그 채널 기록 (실제 봇 실행 시 'bot' 객체 임포트 필요) ---
            try:
                # from bot import CHANNEL_ADMIN_LOG, bot as _bot
                # admin_ch = _bot.get_channel(CHANNEL_ADMIN_LOG)
                # if admin_ch:
                #     f_embed = disnake.Embed(title="코인 송금 실패", color=0x26272f)
                #     f_embed.add_field(name="고객", value=f"{interaction.author.mention} ({user_id})", inline=False)
                #     f_embed.add_field(name="환불 금액", value=f"₩{int(krw_amount_to_subtract):,}", inline=True)
                #     f_embed.add_field(name="코인/네트워크", value=f"{coin} / {network}", inline=True)
                #     f_embed.add_field(name="보낼양", value=f"{send_amount_coin:.8f} {coin}", inline=True)
                #     f_embed.add_field(name="주소", value=address, inline=False)
                #     f_embed.add_field(name="오류", value=f"```{error_message}```", inline=False)
                #     await admin_ch.send(embed=f_embed)
                print(f"송금 실패 로그: {user_id} - 오류: {error_message} (환불: {int(krw_amount_to_subtract):,}원)")
            except Exception as log_e:
                print(f"실패 로그 전송 실패: {log_e}")
        
    except Exception as e:
        print(f"Critical error in handle_send_button: {e}") # 최종 에러 핸들링
        try:
            embed = disnake.Embed(
                title="**처리 중 예상치 못한 오류 발생**",
                description="**직원에게 문의해주세요.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
        except:
            pass

# --- MEXC 입금 감지 및 로그 전송 (개념적 구현) ---
# 이 함수는 봇의 백그라운드 태스크나 별도의 서비스로 주기적으로 실행되어야 합니다.
# 실제 봇에 통합하려면 `on_ready` 이벤트에서 `bot.loop.create_task(check_mexc_deposits_loop())` 와 같이 실행해야 합니다.
# (check_mexc_deposits_loop는 이 함수를 감싸서 무한 루프를 돌리는 별도의 비동기 함수여야 함)
async def check_mexc_deposits():
    """MEXC 입금 내역을 확인하고, 새로운 입금이 있으면 Discord로 로그 전송"""
    if not API_KEY or not SECRET_KEY:
        print("MEXC API 키가 설정되지 않아 입금 감지 기능을 사용할 수 없습니다.")
        return

    try:
        endpoint = "/api/v3/capital/deposit/hisrec"
        timestamp = int(time.time() * 1000)
        
        # MEXC API 문서에 따라 적절한 쿼리 파라미터 사용
        # status: 1 (성공적인 입금), limit: 50 (최근 50개 내역), recvWindow: 60000 (윈도우 타임)
        params = {
            'timestamp': timestamp,
            'status': 1, 
            'limit': 50,
            'recvWindow': 60000 
        }
        signature = sign_params(params, SECRET_KEY)
        if not signature:
            print("MEXC 입금 감지: API 서명 생성 실패")
            return
        params['signature'] = signature # 서명 추가

        headers = { 'X-MEXC-APIKEY': API_KEY }
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생
        
        api_response = response.json()
        
        if api_response.get('code') != 200:
            print(f"MEXC 입금 내역 조회 실패: {api_response.get('msg', '알 수 없는 오류')}")
            return

        for deposit in api_response.get('data', []):
            # 실제 구현 시에는 DB에 저장된 마지막 입금 TXID 등을 비교하여 중복 로그 방지 필요
            # 여기서는 모든 내역을 새롭다고 가정하고 로그를 보냅니다.
            coin_symbol = deposit.get('coin')
            amount = float(deposit.get('amount', 0))
            network = deposit.get('network')
            txid = deposit.get('txid')
            
            if amount > 0: # 유효한 입금만 처리
                await send_deposit_log_to_discord(coin_symbol, amount, network, txid)
                
    except requests.exceptions.RequestException as e:
        print(f"MEXC 입금 감지 네트워크 오류: {e}")
    except Exception as e:
        print(f"MEXC 입금 감지 중 예상치 못한 오류: {e}")

async def send_deposit_log_to_discord(coin_symbol, amount, network, txid):
    """Discord에 입금 로그를 전송하는 함수 (개념적)"""
    try:
        # 이 부분을 실제 Discord 봇 객체와 연동해야 합니다.
        # 예시: bot_instance.get_channel(CHANNEL_DEPOSIT_LOG)
        # from bot import CHANNEL_DEPOSIT_LOG, bot as _bot 
        # deposit_log_channel = _bot.get_channel(CHANNEL_DEPOSIT_LOG)
        
        krw_rate = get_exchange_rate()
        coin_price_usd = get_coin_price(coin_symbol)
        krw_value = amount * coin_price_usd * krw_rate
        
        embed = disnake.Embed(
            title=f"📥 {coin_symbol.upper()} 입금 완료",
            description="새로운 코인 입금 내역이 감지되었습니다.",
            color=0x00ff00 # 초록색
        )
        embed.add_field(name="**코인**", value=coin_symbol.upper(), inline=True)
        embed.add_field(name="**수량**", value=f"{amount:.6f}", inline=True)
        embed.add_field(name="**네트워크**", value=network, inline=True)
        embed.add_field(name="**예상 원화 가치**", value=f"{int(krw_value):,}원", inline=False)
        embed.add_field(name="**TXID**", value=f"[`{txid}`]({get_txid_link(txid, coin_symbol)})", inline=False) # TXID 링크로 표시
        embed.set_footer(text=f"감지 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # if deposit_log_channel:
        #     await deposit_log_channel.send(embed=embed)
        # else:
        print(f"Discord 입금 로그 채널을 찾을 수 없거나, 로그 전송을 건너뛰었습니다. (입금: {coin_symbol} {amount:.6f}, {int(krw_value):,}원, TXID: {txid})")
        
    except Exception as e:
        print(f"Discord 입금 로그 전송 실패: {e}")

# Selenium 관련 함수는 기능 개선과 직접적인 관련이 없어 그대로 유지합니다.
def init_coin_selenium():
    return True

def quit_driver():
    pass
