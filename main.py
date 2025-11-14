import disnake
import requests
import time
import hashlib
import hmac
import sqlite3
from datetime import datetime
import urllib.parse
# 웹훅 사용 제거

# MEXC API 설정
API_KEY = "mx0vg"
SECRET_KEY = "92a35962c743a4"
BASE_URL = "https://api.mexc.com"

# 서비스 수수료율(기본 0.05 = 5%)
SERVICE_FEE_RATE = 0.05

def set_service_fee_rate(rate: float):
    global SERVICE_FEE_RATE
    try:
        if rate < 0 or rate > 0.5:
            return False
        SERVICE_FEE_RATE = rate
        return True
    except Exception:
        return False

def get_service_fee_rate() -> float:
    try:
        return SERVICE_FEE_RATE
    except Exception:
        return 0.05

def sign_params(params, secret):
    try:
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
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
        
        krw_rate = get_exchange_rate()
        binance_price_krw = binance_price_usd * krw_rate
        kimchi_premium = ((upbit_price - binance_price_krw) / binance_price_krw) * 100
        return round(kimchi_premium, 2)
    except Exception:
        return 0

def get_coin_price(coin_symbol):
    try:
        upbit_price = get_upbit_coin_price(coin_symbol)
        if upbit_price > 0:
            return upbit_price
        endpoint = "/api/v3/ticker/price"
        params = {'symbol': f"{coin_symbol}USDT"}
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
    try:
        upbit_mapping = {
            'USDT': 'USDT-KRW',
            'BNB': 'BNB-KRW', 
            'TRX': 'TRX-KRW',
            'LTC': 'LTC-KRW'
        }
        upbit_symbol = upbit_mapping.get(coin_symbol)
        if not upbit_symbol:
            return 0
        url = f"https://api.upbit.com/v1/ticker?markets={upbit_symbol}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                krw_price = float(data[0].get('trade_price', 0))
                usd_krw_rate = get_exchange_rate()
                if usd_krw_rate > 0:
                    usd_price = krw_price / usd_krw_rate
                    return usd_price
        return 0
    except (requests.RequestException, ValueError, KeyError):
        return 0
    except Exception:
        return 0

def get_all_coin_prices():
    try:
        prices = {}
        supported_coins = ['USDT', 'TRX', 'LTC', 'BNB']
        for coin in supported_coins:
            if coin == 'USDT':
                prices[coin] = 1.0
            else:
                upbit_price = get_upbit_coin_price(coin)
                if upbit_price > 0:
                    prices[coin] = upbit_price
                else:
                    mexc_price = get_mexc_coin_price(coin)
                    prices[coin] = mexc_price
        return prices
    except Exception:
        return {}

def get_mexc_coin_price(coin_symbol):
    try:
        endpoint = "/api/v3/ticker/price"
        params = {'symbol': f"{coin_symbol}USDT"}
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

def get_convert_pairs():
    if not API_KEY or not SECRET_KEY:
        return None
    try:
        endpoint = "/api/v3/convert/pairs"
        timestamp = int(time.time() * 1000)
        params = {
            'recvWindow': 60000,
            'timestamp': timestamp
        }
        signature = sign_params(params, SECRET_KEY)
        if not signature:
            return None
        params['signature'] = signature
        headers = {
            'X-MEXC-APIKEY': API_KEY
        }
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 200:
                return data.get('data', [])
        return None
    except Exception:
        return None

def get_symbol_info(symbol):
    if not API_KEY or not SECRET_KEY:
        return None
    try:
        endpoint = "/api/v3/exchangeInfo"
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            symbols = data.get('symbols', [])
            for sym in symbols:
                if sym.get('symbol') == symbol and sym.get('status') == 'ENABLED':
                    return sym
            return None
        else:
            return None
    except Exception:
        return None

def mexc_swap_coins(from_coin, to_coin, amount):
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키가 설정되지 않았습니다'}
    try:
        from_price = get_coin_price(from_coin.upper())
        to_price = get_coin_price(to_coin.upper())
        if from_price <= 0 or to_price <= 0:
            return {'success': False, 'error': '코인 가격 조회 실패'}
        usdt_amount = amount * from_price
        to_amount = usdt_amount / to_price
        swap_fee = 0.001
        final_amount = to_amount * (1 - swap_fee)
        print(f"Debug: {from_coin} {amount} → {to_coin} {final_amount:.6f} (시뮬레이션)")
        return {
            'success': True,
            'orderId': f"SWAP_{int(time.time())}",
            'status': 'success',
            'from_coin': from_coin.upper(),
            'to_coin': to_coin.upper(),
            'amount': amount,
            'swapped_amount': final_amount,
            'fee': swap_fee
        }
    except Exception as e:
        return {'success': False, 'error': f'스왑 오류: {str(e)}'}

# 첫 번째 simple_send_coin 함수 삭제 (중복 제거)

def simple_send_coin(target_coin, amount, address, network):
    """선택한 코인으로 직접 송금 (자동 스왑 없음)"""
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키가 설정되지 않았습니다'}
    try:
        balances = get_all_balances()
        target_balance = balances.get(target_coin.upper(), 0)
        print(f"Debug: 목표 코인={target_coin.upper()}, 필요량={amount}, 현재잔액={target_balance}")
        if target_balance < amount:
            return {'success': False, 'error': f'{target_coin.upper()} 잔액 부족: {target_balance:.6f} {target_coin.upper()} (필요: {amount:.6f})'}
        print(f"Debug: {target_coin.upper()} 잔액 충분, 바로 송금")
        return send_coin_transaction(amount, address, network, target_coin)
    except Exception as e:
        return {'success': False, 'error': f'송금 오류: {str(e)}'}

def get_balance(coin='USDT'):
    if not API_KEY or not SECRET_KEY:
        return "0"
    try:
        endpoint = "/api/v3/account"
        timestamp = int(time.time() * 1000)
        params = {'timestamp': timestamp}
        signature = sign_params(params, SECRET_KEY)
        if not signature:
            return "0"
        params['signature'] = signature
        headers = {'X-MEXC-APIKEY': API_KEY}
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
    if not API_KEY or not SECRET_KEY:
        return {}
    try:
        endpoint = "/api/v3/account"
        timestamp = int(time.time() * 1000)
        params = {'timestamp': timestamp}
        signature = sign_params(params, SECRET_KEY)
        if not signature:
            return {}
        params['signature'] = signature
        headers = {'X-MEXC-APIKEY': API_KEY}
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            balances = data.get('balances', [])
            supported_coins = ['USDT', 'TRX', 'LTC', 'BNB']
            result = {}
            for balance in balances:
                asset = balance.get('asset', '')
                if asset in supported_coins:
                    free_balance = float(balance.get('free', 0))
                    result[asset] = max(0, free_balance)
            for coin in supported_coins:
                if coin not in result:
                    result[coin] = 0
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
            explorer_links = {
                'USDT': f"https://bscscan.com/tx/{txid}",
                'BNB': f"https://bscscan.com/tx/{txid}",
                'TRX': f"https://tronscan.org/#/transaction/{txid}",
                'LTC': f"https://blockchair.com/litecoin/transaction/{txid}"
            }
            return explorer_links.get(coin.upper(), f"https://bscscan.com/tx/{txid}")
        return "https://bscscan.com/"
    except Exception:
        return "https://bscscan.com/"

def get_transaction_fee(coin, network):
    fees = {
        'USDT': {'BSC': 0.8, 'TRX': 1.0},
        'TRX': {'TRX': 1.0},
        'LTC': {'LTC': 0.001},
        'BNB': {'BSC': 0.0005}
    }
    coin_fees = fees.get(coin.upper(), {})
    return coin_fees.get(network.upper(), 1.0)

def get_minimum_amounts_krw():
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
    for coin, min_amount in min_amounts.items():
        coin_price = prices.get(coin, 0)
        if coin_price > 0:
            krw_value = min_amount * coin_price * actual_krw_rate
            min_amounts_krw[coin] = int(krw_value)
        else:
            min_amounts_krw[coin] = 0
    return min_amounts_krw

