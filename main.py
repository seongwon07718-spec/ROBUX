import disnake
from disnake.ext import commands, tasks
import requests
import time
import hashlib
import hmac
import sqlite3
from datetime import datetime, timedelta
import urllib.parse
from disnake import PartialEmoji, ui
import os # os 모듈 추가 (DB 폴더 생성을 위해)

# 웹훅 사용 제거

# --------------------------------------------------------------------------------------
# 📌 튜어오오오옹님! 이 아래의 정보들을 실제 값으로 반드시 교체해주세요!
# MEXC API 설정
API_KEY = "mx0v" # 실제 MEXC API Key로 변경해주세요!
SECRET_KEY = "13f32a0ef0e" # 실제 MEXC Secret Key로 변경해주세요!
BASE_URL = "https://api.mexc.com"

# Discord 봇 토큰 (이 값을 튜어오오오옹님의 실제 Discord 봇 토큰으로 교체하세요!)
BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN_HERE" 

# 입금 알림 및 기타 관리 로그를 보낼 Discord 채널 ID (여기에 실제 채널 ID를 입력해주세요!)
CHANNEL_DEPOSIT_LOG_ID = 1438902596954202378 # 실제 Discord 채널 ID로 변경해주세요!

# 스팟 거래시 지정가 주문 대기 시간 (초)
LIMIT_ORDER_TIMEOUT_SECONDS = 15 
# --------------------------------------------------------------------------------------


# 서비스 수수료율 (기존 코드 유지)
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
        # Hashing algorithm must be sha256. All the parameters except `signature` are
        # concatenated using an ampersand, in ascending alphabetical order of their keys
        # for `GET` method request, then it will become a Query String that looks like this:
        # key=value&key=value, like `side=BUY&symbol=BTCUSDT&timestamp=1626084045585&type=LIMIT`
        # for `POST` method request, body is directly used for signing.
        # This function seems generic, let's assume it's for query string signing.
        sorted_params = sorted(params.items())
        query_string = urllib.parse.urlencode(sorted_params)
        signature = hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        return signature
    except Exception as e:
        print(f"Error signing parameters: {e}")
        return ""

# MEXC API 요청 서명 생성 (POST 요청용 - 바디 데이터로 서명)
def sign_body_params(payload, secret):
    try:
        signature = hmac.new(secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
        return signature
    except Exception as e:
        print(f"Error signing body parameters: {e}")
        return ""

def get_exchange_rate():
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
        response.raise_for_status()
        data = response.json()
        rate = data.get("rates", {}).get("KRW")
        return rate if rate and rate > 0 else 1350
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Error getting exchange rate: {e}")
        return 1350
    except Exception as e:
        print(f"Unexpected error in get_exchange_rate: {e}")
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
        
    except Exception as e:
        print(f"Error getting kimchi premium: {e}")
        return 0

def get_upbit_coin_price(coin_symbol):
    """업비트에서 코인 가격을 USD로 조회"""
    try:
        upbit_mapping = {
            'USDT': 'USDT-KRW', 'BNB': 'BNB-KRW', 'TRX': 'TRX-KRW', 'LTC': 'LTC-KRW', 'BTC': 'KRW-BTC'
        }
        
        upbit_symbol = upbit_mapping.get(coin_symbol.upper())
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
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Error getting Upbit coin price for {coin_symbol}: {e}")
        return 0
    except Exception as e:
        print(f"Unexpected error in get_upbit_coin_price: {e}")
        return 0

def get_mexc_coin_price(coin_symbol):
    """MEXC에서 코인 가격 조회 (백업용)"""
    try:
        endpoint = "/api/v3/ticker/price"
        params = {'symbol': f"{coin_symbol.upper()}USDT"}
        
        response = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return float(data.get('price', 0))
        else:
            return 0
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Error getting MEXC coin price for {coin_symbol}: {e}")
        return 0
    except Exception as e:
        print(f"Unexpected error in get_mexc_coin_price: {e}")
        return 0

def get_coin_price(coin_symbol):
    """
    특정 코인의 현재 가격을 USD로 조회 (업비트 우선, MEXC 백업).
    USDT는 1.0으로 고정 처리.
    """
    if coin_symbol.upper() == 'USDT':
        return 1.0

    upbit_price = get_upbit_coin_price(coin_symbol)
    if upbit_price > 0:
        return upbit_price
    
    return get_mexc_coin_price(coin_symbol)

def get_all_coin_prices():
    """모든 지원 코인의 현재 가격을 조회 (업비트 우선, MEXC 백업)"""
    try:
        prices = {}
        supported_coins = ['USDT', 'TRX', 'LTC', 'BNB']
        
        for coin in supported_coins:
            prices[coin] = get_coin_price(coin)
        
        return prices
    except Exception as e:
        print(f"Error getting all coin prices: {e}")
        return {}

def get_convert_pairs(): # 기존 기능 유지
    """MEXC Convert 가능한 코인 쌍 조회"""
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
    except Exception as e:
        print(f"Error in get_convert_pairs: {e}")
        return None

def get_symbol_info(symbol): # 기존 기능 유지
    """거래소에서 지원하는 심볼 정보 확인"""
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
    except Exception as e:
        print(f"Error in get_symbol_info: {e}")
        return None

def get_precision_info(symbol):
    """
    거래 쌍의 가격 및 수량 정밀도 정보를 가져옵니다.
    """
    info = get_symbol_info(symbol)
    if info:
        return {
            'quantityPrecision': info.get('quantityPrecision', 8),
            'pricePrecision': info.get('pricePrecision', 8),
            'baseCoin': info.get('baseAsset'),
            'quoteCoin': info.get('quoteAsset')
        }
    return None

def mexc_place_spot_order(symbol, side, order_type, quantity=None, price=None, quote_order_qty=None):
    """
    MEXC 현물(Spot) 주문을 생성합니다.
    type: LIMIT, MARKET
    side: BUY, SELL
    quantity: 구매/판매할 코인 수량
    price: 지정가 (LIMIT 주문 시 필수)
    quote_order_qty: 구매할 인용자산(예: USDT)의 수량 (MARKET BUY 주문 시 사용 가능)
    """
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키가 설정되지 않았습니다'}

    endpoint = "/api/v3/order"
    timestamp = int(time.time() * 1000)
    
    payload_params = {
        'symbol': symbol,
        'side': side,
        'type': order_type,
        'recvWindow': 60000,
        'timestamp': timestamp
    }

    if quantity is not None:
        payload_params['quantity'] = f"{quantity:.8f}" # Ensure correct precision
    if price is not None:
        payload_params['price'] = f"{price:.8f}" # Ensure correct precision
    if quote_order_qty is not None:
        payload_params['quoteOrderQty'] = f"{quote_order_qty:.8f}" # Ensure correct precision

    # 필터를 위해 불필요한 필드는 제거하거나, API 문서에 따라 추가적인 처리 필요
    # 예: orderId, newClientOrderId 등 (보통 시스템이 자동 생성)

    # 딕셔너리를 Query String 형태로 변환 후 서명
    query_string_for_signing = urllib.parse.urlencode(sorted(payload_params.items()))
    signature = sign_body_params(query_string_for_signing, SECRET_KEY)
    
    if not signature:
        return {'success': False, 'error': 'API 서명 생성 실패'}
        
    payload_params['signature'] = signature

    headers = {
        'X-MEXC-APIKEY': API_KEY,
        'Content-Type': 'application/json' # POST 요청시 Content-Type 필요
    }

    try:
        # MEXC API는 POST 요청 시 payload_params를 쿼리 파라미터로 보내도록 되어있습니다.
        # requests.post(url, headers=headers, params=payload_params, timeout=30)
        # 쿼리스트링으로 보내는 경우 (sign_params와 유사)
        # 이전에 sign_params에서 query_string_for_signing을 썼으므로, requests.post에 params로 전달.
        response = requests.post(f"{BASE_URL}{endpoint}", headers=headers, params=payload_params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data and data.get('orderId'):
            return {'success': True, 'order': data}
        else:
            return {'success': False, 'error': f"주문 실패: {data.get('msg', '알 수 없는 오류')}", 'data': data}

    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f'주문 요청 중 네트워크 오류: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': f'예상치 못한 오류 발생 (mexc_place_spot_order): {str(e)}'}


def mexc_get_order_status(symbol, order_id):
    """
    MEXC 현물 주문의 상태를 조회합니다.
    """
    if not API_KEY or not SECRET_KEY:
        return None

    endpoint = "/api/v3/order"
    timestamp = int(time.time() * 1000)
    
    params = {
        'symbol': symbol,
        'orderId': order_id,
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

    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting order status {order_id} for {symbol}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in mexc_get_order_status: {e}")
        return None

def mexc_cancel_order(symbol, order_id):
    """
    MEXC 현물 주문을 취소합니다.
    """
    if not API_KEY or not SECRET_KEY:
        return None

    endpoint = "/api/v3/order"
    timestamp = int(time.time() * 1000)
    
    params = {
        'symbol': symbol,
        'orderId': order_id,
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

    try:
        response = requests.delete(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error canceling order {order_id} for {symbol}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in mexc_cancel_order: {e}")
        return None

# --- 자동 스왑 기능 (수수료 최적화 로직 포함) ---
async def perform_fee_optimized_swap(from_coin, from_amount, to_coin):
    """
    지정가 주문을 우선하여 from_coin을 USDT로 판매하고, USDT로 to_coin을 구매하여
    수수료를 최적화하는 스왑 로직 (비동기 함수)
    """
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키가 설정되지 않았습니다.'}

    prices = get_all_coin_prices() # 모든 코인 가격 (USD)
    if not prices:
        return {'success': False, 'error': '코인 가격 정보를 가져올 수 없습니다.'}
    
    if from_coin.upper() not in prices or to_coin.upper() not in prices:
        return {'success': False, 'error': '지원하지 않는 코인입니다.'}

    # 스왑할 금액 (from_coin 기준)
    sell_quantity = from_amount
    
    usdt_amount_obtained = 0.0
    
    # 1단계: from_coin을 USDT로 판매 (Sell from_coin/USDT)
    if from_coin.upper() != 'USDT':
        sell_symbol = f"{from_coin.upper()}USDT"
        
        # 시장가 조회
        ticker = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={'symbol': sell_symbol}, timeout=5).json()
        current_sell_price = float(ticker['price']) if 'price' in ticker else prices.get(from_coin.upper(), 0)

        # 수량 정밀도 확인
        symbol_info = get_precision_info(sell_symbol)
        if not symbol_info:
            return {'success': False, 'error': f'{sell_symbol} 거래 쌍 정보를 가져올 수 없습니다.'}
        
        quantity_precision = symbol_info['quantityPrecision']
        
        # 판매할 수량, 정밀도에 맞춰 조정
        sell_quantity_rounded = float(f"{sell_quantity:.{quantity_precision}f}")
        
        print(f"Debug: {from_coin} {sell_quantity_rounded}을 USDT로 판매 시작 (현재가: {current_sell_price})")

        # 1-1. 지정가 매도 주문 시도 (현재 시장 가격보다 약간 낮은 가격)
        # 즉시 체결되지 않고 메이커가 되기 위해 호가창에 걸릴 가격.
        limit_sell_price = current_sell_price * 0.999 # 현재가보다 약간 낮게 (상황에 따라 조정 필요)
        limit_sell_price = float(f"{limit_sell_price:.{symbol_info['pricePrecision']}f}")

        sell_order_result = mexc_place_spot_order(sell_symbol, 'SELL', 'LIMIT', quantity=sell_quantity_rounded, price=limit_sell_price)
        
        order_id = None
        if sell_order_result['success']:
            order_id = sell_order_result['order']['orderId']
            print(f"Debug: {sell_symbol} 지정가 매도 주문 ({order_id}) 제출. 대기 중...")
            
            start_time = time.time()
            while time.time() - start_time < LIMIT_ORDER_TIMEOUT_SECONDS:
                status = mexc_get_order_status(sell_symbol, order_id)
                if status and status.get('status') == 'FILLED':
                    usdt_amount_obtained = float(status.get('cummulativeQuoteQty', status.get('executedQty')) or 0) # executedQty: 수량, cummulativeQuoteQty: USDT
                    print(f"Debug: {sell_symbol} 지정가 매도 주문({order_id}) 체결 완료. 획득 USDT: {usdt_amount_obtained}")
                    break
                time.sleep(1) # 1초마다 상태 확인

            if usdt_amount_obtained == 0: # 지정가 미체결 또는 부분 체결 시
                print(f"Debug: {sell_symbol} 지정가 매도 주문({order_id}) {LIMIT_ORDER_TIMEOUT_SECONDS}초 내 미체결. 취소 후 시장가 시도.")
                mexc_cancel_order(sell_symbol, order_id) # 주문 취소
                
                # 남은 수량 시장가로 매도
                remaining_quantity_result = mexc_get_order_status(sell_symbol, order_id)
                if remaining_quantity_result:
                    filled_qty = float(remaining_quantity_result.get('executedQty', 0))
                    remaining_qty_to_sell = sell_quantity_rounded - filled_qty
                    usdt_amount_obtained += float(remaining_quantity_result.get('cummulativeQuoteQty', 0))

                    if remaining_qty_to_sell > 0:
                        print(f"Debug: {sell_symbol} 남은 {remaining_qty_to_sell:.{quantity_precision}f} 시장가 매도.")
                        market_sell_result = mexc_place_spot_order(sell_symbol, 'SELL', 'MARKET', quantity=remaining_qty_to_sell)
                        if market_sell_result['success']:
                            market_status = mexc_get_order_status(sell_symbol, market_sell_result['order']['orderId'])
                            if market_status and market_status.get('status') == 'FILLED':
                                usdt_amount_obtained += float(market_status.get('cummulativeQuoteQty', market_status.get('executedQty')) or 0)
                                print(f"Debug: {sell_symbol} 시장가 매도 체결 완료. 총 획득 USDT: {usdt_amount_obtained}")
                        else:
                            print(f"Error: {sell_symbol} 시장가 매도 실패: {market_sell_result['error']}")
                            return {'success': False, 'error': f'코인 판매 중 시장가 매도 실패: {market_sell_result["error"]}'}
                else:
                    return {'success': False, 'error': f'판매 주문 상태 확인 실패 후 시장가 전환 불가.'}
        else:
            print(f"Error: {sell_symbol} 지정가 매도 주문 실패: {sell_order_result['error']}")
            # 지정가 실패 시 바로 시장가 시도
            print(f"Debug: {sell_symbol} 시장가 매도 주문 시도 (지정가 실패).")
            market_sell_result = mexc_place_spot_order(sell_symbol, 'SELL', 'MARKET', quantity=sell_quantity_rounded)
            if market_sell_result['success']:
                market_status = mexc_get_order_status(sell_symbol, market_sell_result['order']['orderId'])
                if market_status and market_status.get('status') == 'FILLED':
                    usdt_amount_obtained = float(market_status.get('cummulativeQuoteQty', market_status.get('executedQty')) or 0)
                    print(f"Debug: {sell_symbol} 시장가 매도 체결 완료. 총 획득 USDT: {usdt_amount_obtained}")
                else:
                    return {'success': False, 'error': f'코인 판매 중 시장가 매도 미체결/실패'}
            else:
                return {'success': False, 'error': f'코인 판매 중 시장가 매도 실패: {market_sell_result["error"]}'}

    else: # from_coin이 USDT인 경우 (판매 건너뛰기)
        usdt_amount_obtained = sell_quantity # USDT는 이미 보유 중

    if usdt_amount_obtained <= 0:
        return {'success': False, 'error': 'USDT를 충분히 확보하지 못했습니다.'}

    # 2단계: USDT로 to_coin 구매 (Buy to_coin/USDT)
    buy_symbol = f"{to_coin.upper()}USDT"

    # 시장가 조회
    ticker = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={'symbol': buy_symbol}, timeout=5).json()
    current_buy_price = float(ticker['price']) if 'price' in ticker else prices.get(to_coin.upper(), 0)

    # 수량/가격 정밀도 확인
    symbol_info = get_precision_info(buy_symbol)
    if not symbol_info:
        return {'success': False, 'error': f'{buy_symbol} 거래 쌍 정보를 가져올 수 없습니다.'}
    
    quote_precision = symbol_info['pricePrecision'] # quote_order_qty 정밀도

    # 구매할 USDT 수량, 정밀도에 맞춰 조정
    buy_quote_qty_rounded = float(f"{usdt_amount_obtained:.{quote_precision}f}")
    
    # 최소 주문 금액 확인 (MEAX API: quoteOrderQty >= 5 USDT)
    if buy_quote_qty_rounded < 5:
        print(f"Warn: 구매할 USDT({buy_quote_qty_rounded})가 최소 거래 금액 5 USDT 미만입니다. 주문이 실패할 수 있습니다.")
        return {'success': False, 'error': '구매할 USDT 금액이 최소 거래 금액(5 USDT) 미만입니다.'}

    print(f"Debug: {buy_quote_qty_rounded} USDT로 {to_coin} 구매 시작 (현재가: {current_buy_price})")

    # 2-1. 지정가 매수 주문 시도 (현재 시장 가격보다 약간 높은 가격)
    # 즉시 체결되지 않고 메이커가 되기 위해 호가창에 걸릴 가격.
    limit_buy_price = current_buy_price * 1.001 # 현재가보다 약간 높게 (상황에 따라 조정 필요)
    limit_buy_price = float(f"{limit_buy_price:.{symbol_info['pricePrecision']}f}")

    buy_order_result = mexc_place_spot_order(buy_symbol, 'BUY', 'LIMIT', price=limit_buy_price, quote_order_qty=buy_quote_qty_rounded)
    
    purchased_quantity = 0.0
    if buy_order_result['success']:
        order_id = buy_order_result['order']['orderId']
        print(f"Debug: {buy_symbol} 지정가 매수 주문 ({order_id}) 제출. 대기 중...")
        
        start_time = time.time()
        while time.time() - start_time < LIMIT_ORDER_TIMEOUT_SECONDS:
            status = mexc_get_order_status(buy_symbol, order_id)
            if status and status.get('status') == 'FILLED':
                purchased_quantity = float(status.get('executedQty', 0))
                print(f"Debug: {buy_symbol} 지정가 매수 주문({order_id}) 체결 완료. 획득 {to_coin}: {purchased_quantity}")
                break
            time.sleep(1)

        if purchased_quantity == 0: # 지정가 미체결 또는 부분 체결 시
            print(f"Debug: {buy_symbol} 지정가 매수 주문({order_id}) {LIMIT_ORDER_TIMEOUT_SECONDS}초 내 미체결. 취소 후 시장가 시도.")
            mexc_cancel_order(buy_symbol, order_id) # 주문 취소

            # 남은 USDT로 시장가 매수
            remaining_usdt_result = mexc_get_order_status(buy_symbol, order_id)
            if remaining_usdt_result:
                filled_quote_qty = float(remaining_usdt_result.get('cummulativeQuoteQty', 0))
                remaining_usdt_to_buy = buy_quote_qty_rounded - filled_quote_qty
                purchased_quantity += float(remaining_usdt_result.get('executedQty', 0))

                if remaining_usdt_to_buy > 0:
                    print(f"Debug: {buy_symbol} 남은 {remaining_usdt_to_buy:.{quote_precision}f} USDT 시장가 매수.")
                    market_buy_result = mexc_place_spot_order(buy_symbol, 'BUY', 'MARKET', quote_order_qty=remaining_usdt_to_buy)
                    if market_buy_result['success']:
                        market_status = mexc_get_order_status(buy_symbol, market_buy_result['order']['orderId'])
                        if market_status and market_status.get('status') == 'FILLED':
                            purchased_quantity += float(market_status.get('executedQty', 0))
                            print(f"Debug: {buy_symbol} 시장가 매수 체결 완료. 총 획득 {to_coin}: {purchased_quantity}")
                    else:
                        print(f"Error: {buy_symbol} 시장가 매수 실패: {market_buy_result['error']}")
                        return {'success': False, 'error': f'코인 구매 중 시장가 매수 실패: {market_buy_result["error"]}'}
            else:
                return {'success': False, 'error': f'구매 주문 상태 확인 실패 후 시장가 전환 불가.'}
    else:
        print(f"Error: {buy_symbol} 지정가 매수 주문 실패: {buy_order_result['error']}")
        # 지정가 실패 시 바로 시장가 시도
        print(f"Debug: {buy_symbol} 시장가 매수 주문 시도 (지정가 실패).")
        market_buy_result = mexc_place_spot_order(buy_symbol, 'BUY', 'MARKET', quote_order_qty=buy_quote_qty_rounded)
        if market_buy_result['success']:
            market_status = mexc_get_order_status(buy_symbol, market_buy_result['order']['orderId'])
            if market_status and market_status.get('status') == 'FILLED':
                purchased_quantity = float(market_status.get('executedQty', 0))
                print(f"Debug: {buy_symbol} 시장가 매수 체결 완료. 총 획득 {to_coin}: {purchased_quantity}")
            else:
                return {'success': False, 'error': f'코인 구매 중 시장가 매수 미체결/실패'}
        else:
            return {'success': False, 'error': f'코인 구매 중 시장가 매수 실패: {market_buy_result["error"]}'}

    if purchased_quantity > 0:
        return {'success': True, 'swapped_amount': purchased_quantity, 'from_coin': from_coin.upper(), 'to_coin': to_coin.upper()}
    else:
        return {'success': False, 'error': f'{to_coin} 구매에 실패했거나 수량이 0입니다.'}


# 이 두 개의 simple_send_coin 함수 중 하나를 사용해야 합니다.
# 튜어오오오옹님의 요청에 따라 '모든 코인 재고를 활용하여 목표 코인으로 Convert 후 송금' 로직을 사용합니다.
# 자동 스왑을 위해 Spot 거래 API를 호출하는 로직으로 내부를 수정했습니다.
async def simple_send_coin(target_coin, amount, address, network):
    """
    모든 코인 재고를 활용하여 목표 코인으로 변환 후 송금합니다.
    변환 과정은 Spot 거래 API(지정가 우선, 미체결 시 시장가 전환)를 사용하여 수수료를 최적화합니다.
    """
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키가 설정되지 않았습니다'}
    
    try:
        # 현재 모든 코인 잔액 확인
        balances = get_all_balances()
        prices = get_all_coin_prices()
        
        target_coin_upper = target_coin.upper()
        target_balance = balances.get(target_coin_upper, 0)
        
        print(f"Debug: 목표 코인={target_coin_upper}, 필요량={amount}, 현재잔액={target_balance}")
        
        # 목표 코인이 충분하면 바로 송금
        if target_balance >= amount:
            print(f"Debug: {target_coin_upper} 잔액 충분, 바로 송금")
            return send_coin_transaction(amount, address, network, target_coin)
        
        # 목표 코인이 부족하면 다른 코인들을 USDT로 Convert 후 목표 코인으로 Convert
        # Spot 거래 API를 사용하여 수수료를 최적화 (지정가 -> 시장가 전환)
        
        needed_usdt_value = amount * prices.get(target_coin_upper, 0) # 필요한 target_coin의 USDT 가치
        
        # 보유 중인 USDT를 먼저 사용
        current_usdt_balance = balances.get('USDT', 0)
        total_usdt_for_buy = current_usdt_balance
        
        # convert_priority 순서대로 코인을 USDT로 변환 시도
        convert_priority = [c for c in ['BNB', 'TRX', 'LTC'] if c.upper() != target_coin_upper] # USDT는 이미 사용, 목표코인 제외

        for from_c in convert_priority:
            from_c_balance = balances.get(from_c.upper(), 0)
            if from_c_balance > 0.0001: # 0이 아닌 아주 작은 잔액도 고려 (MEXC 최소 거래량 확인 필요)
                print(f"Debug: {from_c.upper()} {from_c_balance}를 USDT로 스왑 시도.")
                
                # 수수료 최적화 스왑 로직 호출
                swap_result = await perform_fee_optimized_swap(from_c.upper(), from_c_balance, 'USDT')
                
                if swap_result['success']:
                    total_usdt_for_buy += swap_result['swapped_amount']
                    print(f"Debug: {from_c.upper()} -> USDT 스왑 성공 (획득 USDT: {swap_result['swapped_amount']}). 총 USDT: {total_usdt_for_buy}")
                else:
                    print(f"Warning: {from_c.upper()} -> USDT 스왑 실패: {swap_result['error']}")
        
        # 확보된 총 USDT로 목표 코인 구매 시도
        if total_usdt_for_buy < needed_usdt_value:
            # 확보된 USDT가 목표 코인 구매에 필요한 USDT 가치보다 적은 경우
            print(f"Error: 필요한 {target_coin_upper}({amount}) 구매에 충분한 USDT({total_usdt_for_buy})를 확보하지 못했습니다. (필요 USDT: {needed_usdt_value})")
            return {'success': False, 'error': f'코인 구매에 필요한 USDT 부족. 확보된 USDT: {total_usdt_for_buy:.4f}, 필요한 USDT: {needed_usdt_value:.4f}'}

        # 확보된 USDT 전액으로 target_coin 구매
        print(f"Debug: 확보된 {total_usdt_for_buy} USDT로 {target_coin_upper} 구매 시도.")
        
        buy_target_result = await perform_fee_optimized_swap('USDT', total_usdt_for_buy, target_coin_upper)
        
        if buy_target_result['success']:
            purchased_target_coin_amount = buy_target_result['swapped_amount']
            print(f"Debug: {target_coin_upper} 구매 성공 (획득 수량: {purchased_target_coin_amount}).")

            # 구매한 코인으로 송금
            if purchased_target_coin_amount >= amount:
                print(f"Debug: {target_coin_upper} 구매 완료, 송금 진행.")
                return send_coin_transaction(amount, address, network, target_coin)
            else:
                return {'success': False, 'error': f'목표 코인({target_coin_upper}) 구매량이 부족합니다. 필요: {amount}, 구매: {purchased_target_coin_amount}'}
        else:
            print(f"Error: USDT -> {target_coin_upper} 스왑 실패: {buy_target_result['error']}")
            return {'success': False, 'error': f'목표 코인({target_coin_upper}) 구매 실패: {buy_target_result["error"]}'}
        
    except Exception as e:
        print(f"Unexpected error in simple_send_coin: {e}")
        return {'success': False, 'error': f'코인 자동 스왑 및 송금 중 예상치 못한 오류: {str(e)}'}


def get_balance(coin='USDT'): # 기존 기능 유지
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
            
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Error getting balance for {coin}: {e}")
        return "0"
    except Exception as e:
        print(f"Unexpected error in get_balance: {e}")
        return "0"

def get_all_balances(): # 기존 기능 유지
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
            result = {}
            
            for balance in balances:
                asset = balance.get('asset', '')
                if asset in supported_coins:
                    free_balance = float(balance.get('free', 0))
                    result[asset] = max(0, free_balance)
            
            # 지원하지 않는 코인은 0으로 설정
            for coin in supported_coins:
                if coin not in result:
                    result[coin] = 0
                    
            return result
        else:
            print(f"Error getting all balances: {response.status_code} - {response.text}")
            return {}
            
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Error getting all balances: {e}")
        return {}
    except Exception as e:
        print(f"Unexpected error in get_all_balances: {e}")
        return {}

def get_verified_user(user_id): # 기존 기능 유지
    try:
        os.makedirs('DB', exist_ok=True) # DB 폴더 생성
        conn = sqlite3.connect('DB/verify_user.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    except (sqlite3.Error, OSError) as e:
        print(f"Error getting verified user {user_id}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in get_verified_user: {e}")
        return None

def subtract_balance(user_id, amount): # 기존 기능 유지
    conn = None
    try:
        os.makedirs('DB', exist_ok=True) # DB 폴더 생성
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
        print(f"Error subtracting balance for user {user_id}: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"Unexpected error in subtract_balance: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def add_transaction_history(user_id, amount, transaction_type): # 기존 기능 유지
    conn = None
    try:
        os.makedirs('DB', exist_ok=True) # DB 폴더 생성
        conn = sqlite3.connect('DB/history.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO transaction_history (user_id, amount, type) VALUES (?, ?, ?)', 
                      (user_id, amount, transaction_type))
        conn.commit()
    except (sqlite3.Error, OSError) as e:
        print(f"Error adding transaction history for user {user_id}: {e}")
    except Exception as e:
        print(f"Unexpected error in add_transaction_history: {e}")
    finally:
        if conn:
            conn.close()

def get_txid_link(txid, coin='USDT'): # 기존 기능 유지
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
    except Exception as e:
        print(f"Error in get_txid_link: {e}")
        return "https://bscscan.com/"

def get_transaction_fee(coin, network): # 기존 기능 유지
    """송금 수수료 조회"""
    fees = {
        'USDT': {'BSC': 0.8, 'TRX': 1.0},
        'TRX': {'TRX': 1.0},
        'LTC': {'LTC': 0.001},
        'BNB': {'BSC': 0.0005}
    }
    
    coin_fees = fees.get(coin.upper(), {})
    return coin_fees.get(network.upper(), 1.0)

def get_minimum_amounts_krw(): # 기존 기능 유지
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

# ===== Tier/Fees Helpers ===== (기존 기능 유지)
def get_user_tier_and_fee(user_id: int):
    """Return (tier, service_fee_rate, purchase_bonus_rate). tier: 'VIP' or 'BUYER'"""
    try:
        total_amount = 0
        try:
            os.makedirs('DB', exist_ok=True) # DB 폴더 생성
            conn = sqlite3.connect('DB/verify_user.db')
            cursor = conn.cursor()
            cursor.execute('SELECT Total_amount FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                total_amount = int(row[0] or 0)
            conn.close()
        except Exception as e:
            print(f"Error in get_user_tier_and_fee (DB query): {e}")
            pass
        if total_amount >= 10_000_000:
            return ('VIP', 0.03, 0.01)
        else:
            return ('BUYER', 0.05, 0.0)
    except Exception as e:
        print(f"Unexpected error in get_user_tier_and_fee: {e}")
        return ('BUYER', 0.05, 0.0)

def get_minimum_amount_coin(coin_symbol): # 기존 기능 유지
    """특정 코인의 최소 송금 금액을 코인 단위로 반환"""
    min_amounts = {
        'USDT': 10,     # 10 USDT
        'TRX': 10,      # 10 TRX
        'LTC': 0.015,   # 0.015 LTC
        'BNB': 0.008    # 0.008 BNB
    }
    
    return min_amounts.get(coin_symbol.upper(), 10)

def krw_to_coin_amount(krw_amount, coin_symbol): # 기존 기능 유지
    """KRW 금액을 코인 단위로 변환"""
    krw_rate = get_exchange_rate()
    coin_price = get_coin_price(coin_symbol.upper())
    kimchi_premium = get_kimchi_premium()
    actual_krw_rate = krw_rate * (1 + kimchi_premium / 100)
    
    if actual_krw_rate == 0 or coin_price == 0:
        print(f"Error: KRW rate ({actual_krw_rate}) or Coin price ({coin_price}) is zero for {coin_symbol}.")
        return 0
    return krw_amount / actual_krw_rate / coin_price

# 이 send_coin_transaction 함수는 실제 MEXC 출금 API를 호출합니다. (기존 기능 유지)
def send_coin_transaction(amount, address, network, coin='USDT', skip_min_check=False, skip_address_check=False):
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키가 설정되지 않았습니다'}
    
    if not skip_min_check:
        min_amount = get_minimum_amount_coin(coin.upper())
        min_amounts_krw = get_minimum_amounts_krw()
        min_krw = min_amounts_krw.get(coin.upper(), 10000)
        
        if amount < min_amount:
            return {'success': False, 'error': f'최소 송금 금액 미달: ₩{min_krw:,} (약 {min_amount:.6f} {coin.upper()}) 필요'}
    
    network_mapping = {
        'bep20': 'BSC',      'trc20': 'TRX', 'ltc': 'LTC', 'bnb': 'BSC'
    }
    
    network_code = network_mapping.get(network.lower())
    if not network_code:
        return {'success': False, 'error': f'지원하지 않는 네트워크: {network}'}
    
    print(f"Debug: Coin={coin}, Network={network}, NetworkCode={network_code}, Address={address}, Amount={amount}")
    
    try:
        endpoint = "/api/v3/capital/withdraw"
        timestamp = int(time.time() * 1000)
        
        params = {
            'coin': coin.upper(),
            'address': str(address).strip(),
            'amount': str(amount),
            'netWork': network_code,
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
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                if data.get('id'):
                    txid = str(data.get('id', ''))
                    share_link = get_txid_link(txid, coin.upper())
                    
                    # NOTE: 기존 코드에서 봇 전체 잔액에서 출금 수수료를 차감하는 로직은 주석 처리합니다.
                    # 튜어오오오옹님의 봇 시스템에 맞게 직접 구현해야 합니다.
                    # transaction_fee = get_transaction_fee(coin.upper(), network_code)
                    # try:
                    #     krw_rate = get_exchange_rate()
                    #     coin_price = get_coin_price(coin.upper())
                    #     fee_krw = transaction_fee * coin_price * krw_rate
                    #     # bot.subtract_balance_system_account(int(fee_krw)) # 예시
                    # except Exception as e:
                    #     print(f"송금 수수료 차감 실패: {e}")
                    
                    result = {
                        'success': True,
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'txid': txid,
                        'network': network_code,
                        # 'fee': f"{transaction_fee} {coin.upper()}", # 위 로직이 활성화되면 사용
                        'to_address': str(address).strip(),
                        'share_link': share_link,
                        'coin': coin.upper()
                    }
                    
                    return result
                else:
                    error_msg = data.get('msg', '알 수 없는 오류')
                    print(f"MEXC 출금 실패: {error_msg}")
                    return {'success': False, 'error': f'거래소 오류: {error_msg}'}
            except (ValueError, KeyError) as e:
                print(f"MEXC 출금 응답 파싱 오류: {e} - {response.text}")
                return {'success': False, 'error': '응답 데이터 파싱 오류'}
        else:
            status = response.status_code
            error_msg = None
            try:
                error_data = response.json()
                error_msg = error_data.get('msg') or error_data.get('message')
            except Exception:
                pass
            composed = f"HTTP {status} | {error_msg or '거래소 응답 오류'}"
            print(f"MEXC 출금 실패: {composed} - Request: {params}")
            return {'success': False, 'error': composed}
        
    except requests.exceptions.RequestException as e:
        print(f"MEXC 출금 네트워크 오류: {e}")
        return {'success': False, 'error': f'네트워크 오류: {str(e)}'}
    except Exception as e:
        print(f"MEXC 출금 예상치 못한 오류: {e}")
        return {'success': False, 'error': f'예상치 못한 오류: {str(e)}'}

class AmountModal(disnake.ui.Modal): # 기존 기능 유지
    def __init__(self, network, coin='usdt'):
        self.network = network
        self.coin = coin
        
        min_amounts_krw = get_minimum_amounts_krw()
        min_krw = min_amounts_krw.get(coin.upper(), 10000)
        
        coin_info = {
            'usdt': {'unit': 'USDT'}, 'trx': {'unit': 'TRX'},
            'ltc': {'unit': 'LTC'}, 'bnb': {'unit': 'BNB'}
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
        super().__init__(
            title=f"{info['unit']} 송금 정보",
            custom_id=f"amount_modal_{network}_{coin}",
            components=components,
        )

class ChargeModal(disnake.ui.Modal): # 기존 기능 유지
    def __init__(self):
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
        super().__init__(
            title="충전 금액 입력",
            custom_id="charge_modal",
            components=components,
        )

custom_emoji11 = PartialEmoji(name="47311ltc", id=1438899347453509824) # 기존 이모지 ID
custom_emoji12 = PartialEmoji(name="6798bnb", id=1438899349110390834)
custom_emoji13 = PartialEmoji(name="tron", id=1438899350582591701)
custom_emoji14 = PartialEmoji(name="7541tetherusdt", id=1439510997730721863)

class CoinDropdown(disnake.ui.Select): # 기존 기능 유지
    def __init__(self):
        options = [
            disnake.SelectOption(label="USDT", description="테더코인 선택", value="usdt", emoji=custom_emoji14),
            disnake.SelectOption(label="TRX", description="트론 선택", value="trx", emoji=custom_emoji13),
            disnake.SelectOption(label="LTC", description="라이트코인 선택", value="ltc", emoji=custom_emoji11),
            disnake.SelectOption(label="BNB", description="바이낸스코인 선택", value="bnb", emoji=custom_emoji12)
        ]
        super().__init__(placeholder="송금할 코인을 선택해주세요", options=options)

    async def callback(self, interaction):
        try:
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
                
            selected_coin = self.values[0]
            
            min_amounts_krw = get_minimum_amounts_krw()
            min_krw = min_amounts_krw.get(selected_coin.upper(), 10000)
            
            embed = disnake.Embed(
                title=f"**{selected_coin.upper()} 송금**",
                description=f"**최소 송금 금액 = {min_krw:,}원**",
                color=0xffffff
            )
            view = disnake.ui.View()
            view.add_item(NetworkDropdown(selected_coin))
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception as e:
            print(f"CoinDropdown callback 오류: {e}")
            embed = disnake.Embed(
                title="**오류**",
                description="**처리 중 오류가 발생했습니다.**",
                color=0xff6200
            )
            try:
                await interaction.edit_original_response(embed=embed)
            except Exception:
                pass

class NetworkDropdown(disnake.ui.Select): # 기존 기능 유지
    def __init__(self, selected_coin):
        self.selected_coin = selected_coin
        
        network_options = {
            'usdt': [
                disnake.SelectOption(label="BEP20", description="BSC Network", value="bep20"),
                disnake.SelectOption(label="TRC20", description="TRON Network", value="trc20")
            ],
            'trx': [disnake.SelectOption(label="TRC20", description="TRON Network", value="trc20")],
            'ltc': [disnake.SelectOption(label="LTC", description="Litecoin Network", value="ltc")],
            'bnb': [disnake.SelectOption(label="BEP20", description="BSC Network", value="bep20")]
        }
        
        options = network_options.get(selected_coin.lower(), [
            disnake.SelectOption(label="BEP20", description="BSC Network", value="bep20") # 기본값
        ])
        
        super().__init__(placeholder="네트워크를 선택해주세요", options=options)

    async def callback(self, interaction):
        try:
            await interaction.response.send_modal(AmountModal(self.values[0], self.selected_coin))
        except Exception as e:
            print(f"NetworkDropdown callback 오류: {e}")
            embed = disnake.Embed(
                title="**오류**",
                description="**처리 중 오류가 발생했습니다.**",
                color=0x26272f
            )
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception:
                pass

pending_transactions = {}

async def handle_amount_modal(interaction): # 기존 기능 유지
    try:
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
            krw_amount_input = float(amount_str) # 사용자가 입력한 원화 금액
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
        
        custom_id_parts = interaction.custom_id.split('_')
        network = custom_id_parts[-2] if len(custom_id_parts) >= 3 else "bep20"
        coin = custom_id_parts[-1] if len(custom_id_parts) >= 4 else "usdt"
        
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
        
        krw_rate = get_exchange_rate()
        coin_price = get_coin_price(coin.upper())
        if coin_price <= 0:
            embed = disnake.Embed(
                title="**오류**",
                description="**코인 가격을 조회할 수 없습니다.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
        kimchi_premium = get_kimchi_premium()
        actual_krw_rate = krw_rate * (1 + kimchi_premium / 100)

        # 수수료 계산 (2.5% + 김치프리미엄% + 거래소 송금 수수료)
        service_fee_rate_calc = 0.025 + (kimchi_premium / 100)  # 2.5% + 김치프리미엄%
        
        # 거래소 송금 수수료 (원화)
        transaction_fee_coin = get_transaction_fee(coin.upper(), network.upper())
        exchange_fee_krw = transaction_fee_coin * coin_price * actual_krw_rate # 코인 송금수수료를 원화로 변환

        # 실제 사용자가 지불해야 할 금액 (서비스 수수료 + 거래소 송금 수수료)
        service_fee_krw = krw_amount_input * service_fee_rate_calc
        total_fee_krw = service_fee_krw + exchange_fee_krw

        # 실제 송금할 코인 양 (사용자 입력 원화 금액에서 총 수수료를 제외한 금액을 코인으로 환산)
        actual_send_krw = krw_amount_input - total_fee_krw
        actual_send_amount = actual_send_krw / (coin_price * actual_krw_rate)
        
        # 사용자 잔액에서 차감할 총 금액은 사용자가 입력한 원화 금액
        krw_amount_to_subtract = int(krw_amount_input)
        
        current_balance = user_data[6] if len(user_data) > 6 else 0
        
        if current_balance < krw_amount_to_subtract:
            embed = disnake.Embed(
                title="**잔액 부족**",
                description=f"**보유 금액 = {current_balance:,}원\n필요금액: {krw_amount_to_subtract:,}원**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        network_name = network.upper()
        
        pending_transactions[interaction.author.id] = {
            'send_amount': actual_send_amount,  # 실제 송금할 코인 양
            'total_amount': krw_amount_input,   # 사용자 입력 원화 금액
            'krw_amount': krw_amount_to_subtract, # 사용자 잔액에서 차감할 원화 금액
            'network': network_name,
            'address': address,
            'krw_rate': krw_rate,
            'actual_krw_rate': actual_krw_rate,
            'kimchi_premium': kimchi_premium,
            'coin': coin.upper(),
            'coin_price': coin_price,
            'service_fee_krw': service_fee_krw, 
            'exchange_fee_krw': exchange_fee_krw, 
            'total_fee_krw': total_fee_krw,     
            'actual_send_krw': actual_send_krw, 
            'fee_rate': service_fee_rate_calc               
        }
        
        embed = disnake.Embed(color=0xffffff)
        
        embed.add_field(
            name="**실제 송금 금액**",
            value=f"```{actual_send_amount:.6f} {coin_unit}\n{int(actual_send_krw):,}원```",
            inline=True
        )
        embed.add_field(
            name="**종합 수수료**",
            value=f"```서비스 = {int(service_fee_krw):,}원\n거래소 = {int(exchange_fee_krw):,}원\n총합 = {int(total_fee_krw):,}원```",
            inline=True
        ) 
        embed.add_field(name="**네트워크**", value=f"```{network_name}```", inline=True)
        embed.add_field(name="**코인 주소**", value=f"```{address}```", inline=False)
        
        custom_emoji1 = PartialEmoji(name="send", id=1439222645035106436)

        send_btn = disnake.ui.Button(
            label="송금하기",
            style=disnake.ButtonStyle.gray,
            custom_id="송금하기",
            emoji=custom_emoji1
        )
        
        view = disnake.ui.View()
        view.add_item(send_btn)
        
        await interaction.edit_original_response(embed=embed, view=view)
        
    except Exception as e:
        print(f"handle_amount_modal에서 오류 발생: {e}")
        embed = disnake.Embed(
            title="**오류**",
            description="**처리 중 오류가 발생했습니다.**",
            color=0xff6200
        )
        await interaction.edit_original_response(embed=embed)

async def handle_send_button(interaction): # 기존 기능 유지
    try:
        await interaction.response.defer(ephemeral=True)
        
        user_data = get_verified_user(interaction.author.id)
        if not user_data:
            embed = disnake.Embed(
                title="**오류**",
                description="**인증되지 않은 고객님 입니다.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        transaction_data = pending_transactions.get(interaction.author.id)
        if not transaction_data:
            embed = disnake.Embed(
                title="**오류**",
                description="**송금 정보를 찾을 수 없습니다. 다시 시도해주세요.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        send_amount = transaction_data.get('send_amount', 0)
        total_krw_amount_to_subtract = transaction_data.get('krw_amount', 0) # 사용자 잔액에서 차감할 최종 원화 금액
        network = transaction_data.get('network', 'BEP20').lower()
        address = transaction_data.get('address', '')
        coin = transaction_data.get('coin', 'USDT')
        
        if send_amount <= 0 or total_krw_amount_to_subtract <= 0 or not address:
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
        
        if not subtract_balance(interaction.author.id, total_krw_amount_to_subtract):
            embed = disnake.Embed(
                title="**잔액 부족**",
                description="**잔액이 부족합니다.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
        
        # 수수료 차감은 total_krw_amount_to_subtract에 포함되므로, 따로 fee_krw를 차감하지 않습니다.
        add_transaction_history(interaction.author.id, total_krw_amount_to_subtract, "송금")
        
        # simple_send_coin이 async 함수가 되었으므로 await를 붙여 호출합니다.
        transaction_result = await simple_send_coin(coin, send_amount, address, network) 
        
        if transaction_result and transaction_result.get('success', True):
            coin_name = transaction_result.get('coin', 'USDT')
            actual_send_krw = transaction_data.get('actual_send_krw', 0)
            service_fee_krw = transaction_data.get('service_fee_krw', 0)
            exchange_fee_krw = transaction_data.get('exchange_fee_krw', 0)
            total_fee_krw = transaction_data.get('total_fee_krw', 0)
            
            success_embed = disnake.Embed(
                title=f"**{coin_name} 전송 성공**",
                color=0xffffff
            )
            success_embed.add_field(name="**전송 금액**", value=f"```{int(actual_send_krw):,}원```", inline=True)
            
            success_embed.add_field(name="종합 수수료", value=f"```서비스 = {int(service_fee_krw):,}원\n거래소 = {int(exchange_fee_krw):,}원\n총합 = ₩{int(total_fee_krw):,}원```", inline=True)
            success_embed.add_field(name="네트워크", value=f"```{transaction_result.get('network', 'N/A')}```", inline=False)
            success_embed.add_field(name="TXID", value=f"```{transaction_result.get('txid', 'N/A')}```", inline=False)
            success_embed.add_field(name="보낸주소", value=f"```{transaction_result.get('to_address', 'N/A')}```", inline=False)
            success_embed.add_field(name="보낸시간", value=f"```{transaction_result.get('time', 'N/A')}```", inline=False)
            
            await interaction.edit_original_response(embed=success_embed)

            # NOTE: 기존 코드에서 import bot 관련 부분이 명확하지 않아 주석 처리합니다.
            # 튜어오오오옹님의 봇 시스템에 맞게 직접 구현해야 합니다.
            # try:
            #     from bot import CHANNEL_ADMIN_LOG, CHANNEL_PURCHASE_LOG, bot as _bot
            #     admin_ch = _bot.get_channel(CHANNEL_ADMIN_LOG)
            #     if admin_ch:
            #         t_embed = disnake.Embed(title="코인 전송 내역", color=0x26272f)
            #         t_embed.add_field(name="이용 유저", value=f"{interaction.author.mention} ({interaction.author.id})", inline=False)
            #         t_embed.add_field(name="총 차감금액", value=f"{total_krw_amount_to_subtract:,}원", inline=True)
            #         t_embed.add_field(name="실제 전송 KRW", value=f"{int(actual_send_krw):,}원", inline=True)
            #         t_embed.add_field(name="서비스 수수료", value=f"{int(service_fee_krw):,}원", inline=True)
            #         t_embed.add_field(name="거래소 수수료", value=f"{int(exchange_fee_krw):,}원", inline=True)
            #         t_embed.add_field(name="TXID", value=transaction_result.get('txid', 'N/A'), inline=False)
            #         t_embed.add_field(name="네트워크", value=f"{transaction_result.get('network', 'N/A')}", inline=True)
            #         t_embed.add_field(name="체인 수수료", value=f"{transaction_result.get('fee', 'N/A')}", inline=True)
            #         t_embed.add_field(name="보낸주소", value=f"{transaction_result.get('to_address', 'N/A')}", inline=False)
            #         await admin_ch.send(embed=t_embed)
            #
            #     purchase_ch = _bot.get_channel(CHANNEL_PURCHASE_LOG)
            #     if purchase_ch:
            #         from bot import send_purchase_log
            #         await send_purchase_log(interaction.author.id, transaction_result.get('coin', 'USDT'), int(total_krw_amount_to_subtract))
            # except Exception as e:
            #     print(f"로그 채널 전송 중 오류 발생: {e}")
            
            if interaction.author.id in pending_transactions:
                del pending_transactions[interaction.author.id]
                
        else:
            error_message = "알 수 없는 오류"
            if isinstance(transaction_result, dict) and 'error' in transaction_result:
                error_message = transaction_result['error']
            
            coin = transaction_data.get('coin', 'USDT')
            network = transaction_data.get('network', 'N/A')
            address = transaction_data.get('address', '')
            send_amount_dbg = transaction_data.get('send_amount', 0)
            actual_send_krw = transaction_data.get('actual_send_krw', 0)
            service_fee_krw = transaction_data.get('service_fee_krw', 0)
            exchange_fee_krw = transaction_data.get('exchange_fee_krw', 0)
            
            # 실패 시 환불 처리
            conn = None
            try:
                os.makedirs('DB', exist_ok=True) # DB 폴더 생성
                conn = sqlite3.connect('DB/verify_user.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET now_amount = now_amount + ? WHERE user_id = ?', 
                              (total_krw_amount_to_subtract, interaction.author.id))
                conn.commit()
                print(f"User {interaction.author.id}에게 {total_krw_amount_to_subtract}원 환불 완료.")
            except (sqlite3.Error, OSError) as e:
                print(f"환불 처리 중 DB 오류: {e}")
            except Exception as e:
                print(f"환불 처리 중 예상치 못한 오류: {e}")
            finally:
                if conn:
                    conn.close()
            
            add_transaction_history(interaction.author.id, total_krw_amount_to_subtract, "환불")
            
            refund_embed = disnake.Embed(
                title="**전송 실패**",
                description=f"전송 중 오류가 발생하여 {total_krw_amount_to_subtract:,}원이 환불되었습니다.",
                color=0xff6200
            )
            refund_embed.add_field(
                name="**오류 원인**",
                value=f"```{error_message}```",
                inline=False
            )
            refund_embed.add_field(
                name="**요청 요약**",
                value=f"```코인: {coin}\n네트워크: {network}\n보낼양: {send_amount_dbg:.8f} {coin}\n주소: {address[:6]}...{address[-6:] if len(address)>12 else address}```",
                inline=False
            )
            
            await interaction.edit_original_response(embed=refund_embed)
            
            if interaction.author.id in pending_transactions:
                del pending_transactions[interaction.author.id]
            
            # NOTE: 이 부분도 봇 시스템에 맞게 조정이 필요합니다.
            try:
            #     from bot import CHANNEL_ADMIN_LOG, bot as _bot
            #     admin_ch = _bot.get_channel(CHANNEL_ADMIN_LOG)
            #     if admin_ch:
            #         f_embed = disnake.Embed(title="코인 송금 실패", color=0x26272f)
            #         f_embed.add_field(name="고객", value=f"{interaction.author.mention} ({interaction.author.id})", inline=False)
            #         f_embed.add_field(name="환불 금액", value=f"₩{total_krw_amount_to_subtract:,}", inline=True)
            #         f_embed.add_field(name="코인/네트워크", value=f"{coin} / {network}", inline=True)
            #         f_embed.add_field(name="보낼양", value=f"{send_amount_dbg:.8f} {coin}", inline=True)
            #         f_embed.add_field(name="실제 송금 KRW", value=f"₩{int(actual_send_krw):,}", inline=True)
            #         f_embed.add_field(name="수수료(서비스/거래소)", value=f"₩{int(service_fee_krw):,} / ₩{int(exchange_fee_krw):,}", inline=True)
            #         if address:
            #             f_embed.add_field(name="주소", value=address, inline=False)
            #         f_embed.add_field(name="오류", value=f"```{error_message}```", inline=False)
            #         await admin_ch.send(embed=f_embed)
            # except Exception as e:
            #     print(f"실패 로그 전송 중 오류 발생: {e}")
            
    except Exception as e:
        print(f"handle_send_button에서 오류 발생: {e}")
        try:
            embed = disnake.Embed(
                title="**처리 중 오류 발생**",
                description="직원에게 문의해주세요.",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
        except Exception:
            pass

def init_coin_selenium(): # 기존 기능 유지
    return True

def quit_driver(): # 기존 기능 유지
    pass


# ====================================================================================
# 📌 MEXC 입금 알림 기능 추가 (기존 코드를 그대로 유지하고 추가된 부분)
# ====================================================================================

# MEXC 입금 내역 조회 함수 (입금 감지 전용)
def get_mexc_deposit_history_for_checker():
    """
    MEXC API를 통해 최근 입금 내역을 조회합니다. (입금 감지 전용)
    """
    if not API_KEY or not SECRET_KEY:
        print("경고: MEXC API_KEY 또는 SECRET_KEY가 설정되지 않았습니다. 입금 내역을 조회할 수 없습니다.")
        return []

    endpoint = "/api/v3/capital/deposit/hisrec"
    timestamp = int(time.time() * 1000)
    
    start_time = int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
    
    params = {
        'timestamp': timestamp,
        'recvWindow': 60000, 
        'status': 1, # 1: 성공적인 입금
        'startTime': start_time,
        'limit': 100 
    }
    
    signature = sign_params(params, SECRET_KEY)
    params['signature'] = signature
    
    headers = {
        'X-MEXC-APIKEY': API_KEY
    }
    
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        response.raise_for_status() 
        data = response.json()
        
        if isinstance(data, dict) and 'code' in data and str(data['code']) != '200': 
            print(f"MEXC API 오류 발생 (입금 내역): {data.get('msg', '알 수 없는 오류')} (코드: {data['code']})")
            return []
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
            return data['data']
        else:
            print(f"MEXC 입금 내역 응답 형식 오류: {data}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"MEXC 입금 내역 조회 중 네트워크 오류 발생: {e}")
        return []
    except ValueError as e:
        print(f"MEXC 입금 내역 응답 파싱 오류: {e}")
        return []
    except Exception as e:
        print(f"예상치 못한 오류 발생 (get_mexc_deposit_history_for_checker): {e}")
        return []

# --- 중복 알림 방지를 위한 SQLite 데이터베이스 관리 (입금 감지 전용) ---
def init_mexc_deposit_db(): # 기존 DB 함수와 충돌 방지를 위해 함수명 변경
    """
    입금 내역 TXID를 저장할 SQLite 데이터베이스를 초기화합니다.
    """
    conn = None
    try:
        os.makedirs('DB', exist_ok=True) 
        conn = sqlite3.connect('DB/mexc_deposits.db') 
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_mexc_deposits (
                txid TEXT PRIMARY KEY,
                coin TEXT,
                amount REAL,
                insert_time INTEGER,
                process_time TEXT DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%S', 'NOW'))
            );
        ''')
        conn.commit()
        print("MEXC 입금 내역 감지 DB 초기화 완료.")
    except (sqlite3.Error, OSError) as e:
        print(f"MEXC 입금 감지 DB 초기화 오류: {e}")
    finally:
        if conn:
            conn.close()

def is_txid_processed_for_mexc_deposit(txid): # 기존 DB 함수와 충돌 방지를 위해 함수명 변경
    """
    해당 TXID가 이미 처리된 입금 내역인지 확인합니다. (입금 감지 전용)
    """
    conn = None
    try:
        os.makedirs('DB', exist_ok=True)
        conn = sqlite3.connect('DB/mexc_deposits.db')
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM processed_mexc_deposits WHERE txid = ?', (txid,))
        return cursor.fetchone() is not None
    except (sqlite3.Error, OSError) as e:
        print(f"MEXC 입금 감지 TXID 확인 오류: {e}")
        return False
    finally:
        if conn:
            conn.close()

def add_processed_txid_for_mexc_deposit(txid, coin, amount, insert_time): # 기존 DB 함수와 충돌 방지를 위해 함수명 변경
    """
    처리된 입금 내역의 TXID를 데이터베이스에 추가합니다. (입금 감지 전용)
    """
    conn = None
    try:
        os.makedirs('DB', exist_ok=True)
        conn = sqlite3.connect('DB/mexc_deposits.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO processed_mexc_deposits (txid, coin, amount, insert_time) VALUES (?, ?, ?, ?)',
            (txid, coin, amount, insert_time)
        )
        conn.commit()
    except (sqlite3.Error, OSError) as e:
        print(f"MEXC 입금 감지 TXID 추가 오류: {e}")
    finally:
        if conn:
            conn.close()

# Discord 봇 인스턴스 초기화 (기존 봇 객체를 사용)
bot = commands.Bot(command_prefix="!", intents=disnake.Intents.all()) 

@bot.listen("on_ready")
async def mexc_deposit_checker_on_ready(): # 기존 on_ready 함수명과 충돌 방지를 위해 변경
    """
    봇이 Discord에 성공적으로 연결되었을 때 실행됩니다.
    MEXC 입금 감지 관련 DB 초기화 및 루프를 시작합니다.
    """
    print(f"MEXC 입금 감지 모듈 시작: {bot.user} 님으로 로그인했습니다 (ID: {bot.user.id})")
    init_mexc_deposit_db() # 봇 시작 시 입금 내역 DB 초기화
    mexc_deposit_loop.start() # 주기적인 입금 확인 루프 시작

@tasks.loop(seconds=30) # 30초마다 MEXC 입금 내역을 확인합니다.
async def mexc_deposit_loop():
    """
    MEXC 입금 내역을 주기적으로 확인하고 Discord에 알림을 보냅니다.
    """
    deposit_records = get_mexc_deposit_history_for_checker() 
    
    if not deposit_records:
        return

    deposit_log_channel = bot.get_channel(CHANNEL_DEPOSIT_LOG_ID)
    if not deposit_log_channel:
        print(f"오류: 입금 로그 채널 ID {CHANNEL_DEPOSIT_LOG_ID}를 찾을 수 없습니다. 봇 설정 또는 권한을 확인해주세요.")
        return

    for record in deposit_records:
        txid = record.get('txId')
        coin = record.get('coin')
        amount_str = record.get('amount')
        insert_time = record.get('insertTime') # UTC 밀리초 (Unix Time)

        if not txid or not coin or not amount_str:
            print(f"경고: 필수 정보가 누락된 입금 기록이 발견되었습니다: {record}")
            continue

        try:
            amount = float(amount_str)
        except ValueError:
            print(f"경고: 입금 금액 파싱 오류 ({amount_str}), 기록: {record}")
            continue

        # 이미 처리된 TXID인지 확인합니다. (중복 알림 방지 목적)
        if is_txid_processed_for_mexc_deposit(txid): 
            continue
            
        # 입금된 코인의 원화 가치를 계산합니다. (기존 calculate_krw_value 함수 재사용)
        krw_value = calculate_krw_value(coin, amount)

        # Discord Embed 메시지 생성 (원화 가치만 표시)
        embed = disnake.Embed(
            title="💰 MEXC 입고 완료!",
            description="새로운 코인 입고가 확인되었습니다.",
            color=disnake.Color.green(), 
            timestamp=datetime.fromtimestamp(insert_time / 1000) 
        )
        embed.add_field(name="입고 금액", value=f"```🥳 {krw_value:,}원 🥳```", inline=False)
        
        try:
            await deposit_log_channel.send(embed=embed)
            add_processed_txid_for_mexc_deposit(txid, coin, amount, insert_time) 
            print(f"MEXC 입고 알림 성공: {krw_value:,}원 ({coin.upper()} {amount:.6f}, TXID: {txid})")
        except Exception as e:
            print(f"Discord 입고 알림 전송 실패 (TXID: {txid}): {e}")

# 봇 실행 (가장 하단에 배치하며, 실제 토큰으로 교체해야 합니다.)
if __name__ == '__main__':
    if BOT_TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("오류: BOT_TOKEN을 실제 Discord 봇 토큰으로 교체해야 합니다. 봇을 시작할 수 없습니다.")
    elif not API_KEY or not SECRET_KEY:
        print("오류: MEXC API_KEY 또는 SECRET_KEY가 설정되지 않았습니다. 봇을 시작할 수 없습니다.")
    else:
        bot.run(BOT_TOKEN)
