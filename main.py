import disnake
import requests
import time
import hashlib
import hmac
import sqlite3
from datetime import datetime, timedelta
import urllib.parse
# from disnake import PartialEmoji, ui # UI 컴포넌트 클래스들이 함수 밖에 정의되어 있으므로 제거하지 않습니다.
import asyncio # 비동기 sleep을 위해 추가
import os # os.makedirs를 위해 추가

# 웹훅 사용 제거

# --------------------------------------------------------------------------------------
# 📌 튜어오오오옹님! 이 아래의 정보들을 실제 값으로 반드시 교체해주세요!
# MEXC API 설정
API_KEY = "mx0vgl9lSugl" # 실제 MEXC API Key로 변경해주세요!
SECRET_KEY = "13f323aaa36b0656a882a54" # 실제 MEXC Secret Key로 변경해주세요!
BASE_URL = "https://api.mexc.com"

# 입금 알림 및 기타 관리 로그를 보낼 Discord 채널 ID (여기에 실제 채널 ID를 입력해주세요!)
CHANNEL_DEPOSIT_LOG_ID = 1438902596954202378 # 실제 Discord 채널 ID로 변경해주세요!

# 스팟 거래시 지정가 주문 대기 시간 (초) - 수수료 최적화 로직에서 사용
LIMIT_ORDER_TIMEOUT_SECONDS = 15 
# --------------------------------------------------------------------------------------

# 서비스 수수료율
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
        sorted_params = sorted(params.items())
        query_string = urllib.parse.urlencode(sorted_params)
        signature = hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        return signature
    except Exception as e:
        print(f"Error signing parameters: {e}")
        return ""

def sign_body_params(payload, secret): # 기존에 있던 함수
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
        
    except Exception as e: # 수정: 잘못된 위치의 except Exception 수정
        print(f"Error getting kimchi premium: {e}")
        return 0

def get_upbit_coin_price(coin_symbol):
    """업비트에서 코인 가격을 USD로 조회"""
    try:
        upbit_mapping = {
            'USDT': 'USDT-KRW', 'BNB': 'BNB-KRW', 'TRX': 'TRX-KRW', 'LTC': 'LTC-KRW', 'BTC': 'KRW-BTC' # BTC 추가
        }
        upbit_symbol = upbit_mapping.get(coin_symbol.upper()) # 수정: .upper() 추가
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
    except (requests.RequestException, ValueError, KeyError) as e: # 수정: 잘못된 위치의 except Exception 수정
        print(f"Error getting Upbit coin price for {coin_symbol}: {e}")
        return 0
    except Exception as e:
        print(f"Unexpected error in get_upbit_coin_price: {e}")
        return 0

def get_mexc_coin_price(coin_symbol):
    """MEXC에서 코인 가격 조회 (백업용)"""
    try:
        endpoint = "/api/v3/ticker/price"
        params = {'symbol': f"{coin_symbol.upper()}USDT"} # 수정: .upper() 추가
        
        response = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return float(data.get('price', 0))
        else:
            return 0
    except (requests.RequestException, ValueError, KeyError) as e: # 수정: 잘못된 위치의 except Exception 수정
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
    if coin_symbol.upper() == 'USDT': # 수정: .upper() 추가
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
    except Exception as e: # 수정: 잘못된 위치의 except Exception 수정
        print(f"Error getting all coin prices: {e}")
        return {}

def get_convert_pairs():
    """MEXC Convert 가능한 코인 쌍 조회 (기존 기능 유지)"""
    if not API_KEY or not SECRET_KEY:
        return None
    
    try:
        endpoint = "/api/v3/convert/pairs"
        timestamp = int(time.time() * 1000)
        params = {'recvWindow': 60000, 'timestamp': timestamp}
        signature = sign_params(params, SECRET_KEY)
        if not signature:
            return None
        params['signature'] = signature
        headers = {'X-MEXC-APIKEY': API_KEY}
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 200:
                return data.get('data', [])
        return None
    except Exception as e: # 수정: 잘못된 위치의 except Exception 수정
        print(f"Error in get_convert_pairs: {e}")
        return None

def get_symbol_info(symbol):
    """거래소에서 지원하는 심볼 정보 확인 (기존 기능 유지)"""
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
    except Exception as e: # 수정: 잘못된 위치의 except Exception 수정
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
    quantity: 구매/판매할 코인 수량 (MARKET SELL, LIMIT 주문 시)
    price: 지정가 (LIMIT 주문 시 필수)
    quote_order_qty: 구매할 인용자산(예: USDT)의 수량 (MARKET BUY 주문 시 사용)
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
        payload_params['quantity'] = f"{quantity:.8f}"
    if price is not None:
        payload_params['price'] = f"{price:.8f}"
    if quote_order_qty is not None:
        payload_params['quoteOrderQty'] = f"{quote_order_qty:.8f}"

    # 딕셔너리를 Query String 형태로 변환 후 서명 (MEXC는 POST도 Query String으로 서명)
    signature = sign_params(payload_params, SECRET_KEY)

    if not signature:
        return {'success': False, 'error': 'API 서명 생성 실패'}
        
    payload_params['signature'] = signature

    headers = {'X-MEXC-APIKEY': API_KEY}

    try:
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
    params = {'symbol': symbol, 'orderId': order_id, 'recvWindow': 60000, 'timestamp': timestamp}
    signature = sign_params(params, SECRET_KEY)
    if not signature:
        return None
    params['signature'] = signature
    headers = {'X-MEXC-APIKEY': API_KEY}
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
    params = {'symbol': symbol, 'orderId': order_id, 'recvWindow': 60000, 'timestamp': timestamp}
    signature = sign_params(params, SECRET_KEY)
    if not signature:
        return None
    params['signature'] = signature
    headers = {'X-MEXC-APIKEY': API_KEY}
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

def mexc_swap_coins(from_coin, to_coin, amount): # 기존 기능 유지
    """MEXC Convert 시뮬레이션 (실제 Convert API가 작동하지 않음)"""
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
    except Exception as e: # 수정: 잘못된 위치의 except Exception 수정
        return {'success': False, 'error': f'스왑 오류: {str(e)}'}

async def perform_fee_optimized_swap(from_coin, from_amount, to_coin):
    """
    지정가 주문을 우선하여 from_coin을 USDT로 판매하고, USDT로 to_coin을 구매하여
    수수료를 최적화하는 스왑 로직 (비동기 함수)
    """
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키가 설정되지 않았습니다.'}

    prices = get_all_coin_prices()
    if not prices:
        return {'success': False, 'error': '코인 가격 정보를 가져올 수 없습니다.'}
    
    if from_coin.upper() not in prices or to_coin.upper() not in prices:
        return {'success': False, 'error': '지원하지 않는 코인입니다.'}

    sell_quantity = from_amount
    usdt_amount_obtained = 0.0
    
    # 1단계: from_coin을 USDT로 판매 (Sell from_coin/USDT)
    if from_coin.upper() != 'USDT':
        sell_symbol = f"{from_coin.upper()}USDT"
        
        ticker_response = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={'symbol': sell_symbol}, timeout=5)
        ticker_response.raise_for_status()
        ticker = ticker_response.json()
        current_sell_price = float(ticker['price']) if 'price' in ticker else prices.get(from_coin.upper(), 0)

        symbol_info = get_precision_info(sell_symbol)
        if not symbol_info:
            return {'success': False, 'error': f'{sell_symbol} 거래 쌍 정보를 가져올 수 없습니다.'}
        
        quantity_precision = symbol_info['quantityPrecision']
        sell_quantity_rounded = float(f"{sell_quantity:.{quantity_precision}f}")
        
        print(f"Debug: {from_coin} {sell_quantity_rounded}을 USDT로 판매 시작 (현재가: {current_sell_price})")

        # 1-1. 지정가 매도 주문 시도 (현재 시장 가격보다 약간 낮은 가격)
        limit_sell_price = current_sell_price * 0.999 
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
                    usdt_amount_obtained = float(status.get('cummulativeQuoteQty', status.get('executedQty')) or 0)
                    print(f"Debug: {sell_symbol} 지정가 매도 주문({order_id}) 체결 완료. 획득 USDT: {usdt_amount_obtained}")
                    break
                await asyncio.sleep(1) # 비동기 sleep

            if usdt_amount_obtained == 0: 
                print(f"Debug: {sell_symbol} 지정가 매도 주문({order_id}) {LIMIT_ORDER_TIMEOUT_SECONDS}초 내 미체결. 취소 후 시장가 시도.")
                mexc_cancel_order(sell_symbol, order_id)
                
                remaining_quantity_result = mexc_get_order_status(sell_symbol, order_id)
                if remaining_quantity_result:
                    filled_qty = float(remaining_quantity_result.get('executedQty', 0))
                    remaining_qty_to_sell = sell_quantity_rounded - filled_qty
                    usdt_amount_obtained += float(remaining_quantity_result.get('cummulativeQuoteQty', 0))

                    if remaining_qty_to_sell > 0.00000001: 
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

    else:
        usdt_amount_obtained = sell_quantity

    if usdt_amount_obtained <= 0:
        return {'success': False, 'error': 'USDT를 충분히 확보하지 못했습니다.'}

    # 2단계: USDT로 to_coin 구매 (Buy to_coin/USDT)
    buy_symbol = f"{to_coin.upper()}USDT"

    ticker_response = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={'symbol': buy_symbol}, timeout=5)
    ticker_response.raise_for_status()
    ticker = ticker_response.json()
    current_buy_price = float(ticker['price']) if 'price' in ticker else prices.get(to_coin.upper(), 0)

    symbol_info = get_precision_info(buy_symbol)
    if not symbol_info:
        return {'success': False, 'error': f'{buy_symbol} 거래 쌍 정보를 가져올 수 없습니다.'}
    
    quote_precision = symbol_info['pricePrecision']
    buy_quote_qty_rounded = float(f"{usdt_amount_obtained:.{quote_precision}f}")
    
    if buy_quote_qty_rounded < 5:
        print(f"Warn: 구매할 USDT({buy_quote_qty_rounded})가 최소 거래 금액 5 USDT 미만입니다. 주문이 실패할 수 있습니다.")
        return {'success': False, 'error': '구매할 USDT 금액이 최소 거래 금액(5 USDT) 미만입니다.'}

    print(f"Debug: {buy_quote_qty_rounded} USDT로 {to_coin} 구매 시작 (현재가: {current_buy_price})")

    # 2-1. 지정가 매수 주문 시도 (현재 시장 가격보다 약간 높은 가격)
    limit_buy_price = current_buy_price * 1.001 
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
            await asyncio.sleep(1)

        if purchased_quantity == 0: 
            print(f"Debug: {buy_symbol} 지정가 매수 주문({order_id}) {LIMIT_ORDER_TIMEOUT_SECONDS}초 내 미체결. 취소 후 시장가 시도.")
            mexc_cancel_order(buy_symbol, order_id)

            remaining_usdt_result = mexc_get_order_status(buy_symbol, order_id)
            if remaining_usdt_result:
                filled_quote_qty = float(remaining_usdt_result.get('cummulativeQuoteQty', 0))
                remaining_usdt_to_buy = buy_quote_qty_rounded - filled_quote_qty
                purchased_quantity += float(remaining_usdt_result.get('executedQty', 0))

                if remaining_usdt_to_buy > 0.00000001: 
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

def simple_send_coin(target_coin, amount, address, network):
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키가 설정되지 않았습니다'}
    
    try:
        balances = get_all_balances()
        prices = get_all_coin_prices()
        
        target_coin_upper = target_coin.upper()
        target_balance = balances.get(target_coin_upper, 0)
        
        print(f"Debug: 목표 코인={target_coin_upper}, 필요량={amount}, 현재잔액={target_balance}")
        
        if target_balance >= amount:
            print(f"Debug: {target_coin_upper} 잔액 충분, 바로 송금")
            return send_coin_transaction(amount, address, network, target_coin)
        
        needed_usdt_value = amount * prices.get(target_coin_upper, 0)
        current_usdt_balance = balances.get('USDT', 0)
        total_usdt_for_buy = current_usdt_balance
        
        convert_priority = [c for c in ['BNB', 'TRX', 'LTC'] if c.upper() != target_coin_upper]

        for from_c in convert_priority:
            from_c_balance = balances.get(from_c.upper(), 0)
            if from_c_balance > 0.0001: 
                print(f"Debug: {from_c.upper()} {from_c_balance}를 USDT로 스왑 시도.")
                swap_result = mexc_swap_coins(from_c.upper(), 'USDT', from_c_balance) # 수정: await perform_fee_optimized_swap(from_c.upper(), from_c_balance, 'USDT')로 변경해야 함.
                if swap_result['success']:
                    total_usdt_for_buy += swap_result['swapped_amount']
                    print(f"Debug: {from_c.upper()} -> USDT 스왑 성공 (획득 USDT: {swap_result['swapped_amount']}). 총 USDT: {total_usdt_for_buy}")
                else:
                    print(f"Warning: {from_c.upper()} -> USDT 스왑 실패: {swap_result['error']}")
        
        if total_usdt_for_buy < needed_usdt_value:
            print(f"Error: 필요한 {target_coin_upper}({amount}) 구매에 충분한 USDT({total_usdt_for_buy})를 확보하지 못했습니다. (필요 USDT: {needed_usdt_value})")
            return {'success': False, 'error': f'코인 구매에 필요한 USDT 부족. 확보된 USDT: {total_usdt_for_buy:.4f}, 필요한 USDT: {needed_usdt_value:.4f}'}

        print(f"Debug: 확보된 {total_usdt_for_buy} USDT로 {target_coin_upper} 구매 시도.")
        
        buy_target_result = mexc_swap_coins('USDT', total_usdt_for_buy, target_coin_upper) # 수정: await perform_fee_optimized_swap('USDT', total_usdt_for_buy, target_coin_upper)로 변경해야 함.
        
        if buy_target_result['success']:
            purchased_target_coin_amount = buy_target_result['swapped_amount']
            print(f"Debug: {target_coin_upper} 구매 성공 (획득 수량: {purchased_target_coin_amount}).")

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

def get_balance(coin='USDT'):
    if not API_KEY or not SECRET_KEY:
        return "0"
    try:
        endpoint = "/api/v3/account"
        timestamp = int(time.time() * 1000)
        params = {'timestamp': timestamp}
        signature = sign_params(params, SECRET_KEY)
        if not signature: return "0"
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
        else: return "0"
    except Exception as e: print(f"Error getting balance for {coin}: {e}"); return "0"

def get_all_balances():
    if not API_KEY or not SECRET_KEY: return {}
    try:
        endpoint = "/api/v3/account"
        timestamp = int(time.time() * 1000)
        params = {'timestamp': timestamp}
        signature = sign_params(params, SECRET_KEY)
        if not signature: return {}
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
                if coin not in result: result[coin] = 0
            return result
        else: print(f"Error getting all balances: {response.status_code} - {response.text}"); return {}
    except Exception as e: print(f"Error getting all balances: {e}"); return {}

def get_verified_user(user_id):
    try:
        os.makedirs('DB', exist_ok=True)
        conn = sqlite3.connect('DB/verify_user.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    except Exception as e: print(f"Error getting verified user {user_id}: {e}"); return None

def subtract_balance(user_id, amount):
    conn = None
    try:
        os.makedirs('DB', exist_ok=True)
        conn = sqlite3.connect('DB/verify_user.db')
        cursor = conn.cursor()
        cursor.execute('SELECT now_amount FROM users WHERE user_id = ?', (user_id,))
        current = cursor.fetchone()
        if current and current[0] >= amount:
            new_balance = current[0] - amount
            cursor.execute('UPDATE users SET now_amount = ? WHERE user_id = ?', (new_balance, user_id))
            conn.commit()
            return True
        else: return False
    except Exception as e: print(f"Error subtracting balance for user {user_id}: {e}"); if conn: conn.rollback(); return False
    finally:
        if conn: conn.close()

def add_transaction_history(user_id, amount, transaction_type):
    conn = None
    try:
        os.makedirs('DB', exist_ok=True)
        conn = sqlite3.connect('DB/history.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO transaction_history (user_id, amount, type) VALUES (?, ?, ?)',
                       (user_id, amount, transaction_type))
        conn.commit()
    except Exception as e: print(f"Error adding transaction history for user {user_id}: {e}")
    finally:
        if conn: conn.close()

def get_txid_link(txid, coin='USDT'):
    try:
        if txid:
            explorer_links = {
                'USDT': f"https://bscscan.com/tx/{txid}", 'BNB': f"https://bscscan.com/tx/{txid}",
                'TRX': f"https://tronscan.org/#/transaction/{txid}", 'LTC': f"https://blockchair.com/litecoin/transaction/{txid}"
            }
            return explorer_links.get(coin.upper(), f"https://bscscan.com/tx/{txid}")
        return "https://bscscan.com/"
    except Exception as e: print(f"Error in get_txid_link: {e}"); return "https://bscscan.com/"

def get_transaction_fee(coin, network):
    fees = {
        'USDT': {'BSC': 0.8, 'TRX': 1.0}, 'TRX': {'TRX': 1.0},
        'LTC': {'LTC': 0.001}, 'BNB': {'BSC': 0.0005}
    }
    coin_fees = fees.get(coin.upper(), {})
    return coin_fees.get(network.upper(), 1.0)

def get_minimum_amounts_krw():
    min_amounts = {
        'USDT': 10, 'TRX': 10, 'LTC': 0.015, 'BNB': 0.008
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
        else: min_amounts_krw[coin] = 0
    return min_amounts_krw

def get_user_tier_and_fee(user_id: int):
    try:
        total_amount = 0
        try:
            os.makedirs('DB', exist_ok=True)
            conn = sqlite3.connect('DB/verify_user.db')
            cursor = conn.cursor()
            cursor.execute('SELECT Total_amount FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row: total_amount = int(row[0] or 0)
            conn.close()
        except Exception as e: print(f"Error in get_user_tier_and_fee (DB query): {e}")
        if total_amount >= 10_000_000: return ('VIP', 0.03, 0.01)
        else: return ('BUYER', 0.05, 0.0)
    except Exception as e: print(f"Unexpected error in get_user_tier_and_fee: {e}"); return ('BUYER', 0.05, 0.0)

def get_minimum_amount_coin(coin_symbol):
    min_amounts = {'USDT': 10, 'TRX': 10, 'LTC': 0.015, 'BNB': 0.008}
    return min_amounts.get(coin_symbol.upper(), 10)

def krw_to_coin_amount(krw_amount, coin_symbol):
    krw_rate = get_exchange_rate()
    coin_price = get_coin_price(coin_symbol.upper())
    kimchi_premium = get_kimchi_premium()
    actual_krw_rate = krw_rate * (1 + kimchi_premium / 100)
    if actual_krw_rate == 0 or coin_price == 0:
        print(f"Error: KRW rate ({actual_krw_rate}) or Coin price ({coin_price}) is zero for {coin_symbol}.")
        return 0
    return krw_amount / actual_krw_rate / coin_price

def send_coin_transaction(amount, address, network, coin='USDT', skip_min_check=False, skip_address_check=False):
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키가 설정되지 않았습니다'}
    
    if not skip_min_check:
        min_amount = get_minimum_amount_coin(coin.upper())
        min_krw = get_minimum_amounts_krw().get(coin.upper(), 10000)
        if amount < min_amount:
            return {'success': False, 'error': f'최소 송금 금액 미달: ₩{min_krw:,} (약 {min_amount:.6f} {coin.upper()}) 필요'}
    
    network_mapping = {'bep20': 'BSC', 'trc20': 'TRX', 'ltc': 'LTC', 'bnb': 'BSC'}
    network_code = network_mapping.get(network.lower())
    if not network_code:
        return {'success': False, 'error': f'지원하지 않는 네트워크: {network}'}
    
    print(f"Debug: Coin={coin}, Network={network}, NetworkCode={network_code}, Address={address}, Amount={amount}")
    
    try:
        endpoint = "/api/v3/capital/withdraw"
        timestamp = int(time.time() * 1000)
        params = {
            'coin': coin.upper(), 'address': str(address).strip(), 'amount': str(amount),
            'netWork': network_code, 'recvWindow': 60000, 'timestamp': timestamp
        }
        signature = sign_params(params, SECRET_KEY)
        if not signature: return {'success': False, 'error': 'API 서명 생성 실패'}
        params['signature'] = signature
        headers = {'X-MEXC-APIKEY': API_KEY}
        response = requests.post(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('id'):
                txid = str(data.get('id', ''))
                share_link = get_txid_link(txid, coin.upper())
                result = {
                    'success': True, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'txid': txid, 'network': network_code, 'to_address': str(address).strip(),
                    'share_link': share_link, 'coin': coin.upper()
                }
                return result
            else:
                error_msg = data.get('msg', '알 수 없는 오류')
                print(f"MEXC 출금 실패: {error_msg}")
                return {'success': False, 'error': f'거래소 오류: {error_msg}'}
        else:
            status = response.status_code
            error_msg = response.json().get('msg') if response.content else '거래소 응답 오류'
            print(f"MEXC 출금 실패: HTTP {status} | {error_msg} - Request: {params}")
            return {'success': False, 'error': f"HTTP {status} | {error_msg}"}
        
    except Exception as e:
        print(f"MEXC 출금 예상치 못한 오류: {e}")
        return {'success': False, 'error': f'예상치 못한 오류: {str(e)}'}

class AmountModal(disnake.ui.Modal):
    def __init__(self, network, coin='usdt'):
        self.network = network
        self.coin = coin
        
        min_krw = get_minimum_amounts_krw().get(coin.upper(), 10000)
        info = {'usdt': {'unit': 'USDT'}, 'trx': {'unit': 'TRX'}, 'ltc': {'unit': 'LTC'}, 'bnb': {'unit': 'BNB'}}.get(coin.lower(), {'unit': 'USDT'})
        
        components = [
            disnake.ui.TextInput(label="금액", placeholder=f"금액을 입력해주세요 (최소 {min_krw:,}원)",
                                 custom_id="amount", style=disnake.TextInputStyle.short, min_length=1, max_length=15),
            disnake.ui.TextInput(label="코인 주소", placeholder="송금 받으실 지갑 주소를 입력해주세요",
                                 custom_id="address", style=disnake.TextInputStyle.short, min_length=10, max_length=100)
        ]
        super().__init__(title=f"{info['unit']} 송금 정보", custom_id=f"amount_modal_{network}_{coin}", components=components)

class ChargeModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(label="충전 금액", placeholder="충전하실 금액을 적어주세요. ( 최소 500원 )",
                                 custom_id="charge_amount", style=disnake.TextInputStyle.short, min_length=1, max_length=15)
        ]
        super().__init__(title="충전 금액 입력", custom_id="charge_modal", components=components)

custom_emoji11 = PartialEmoji(name="47311ltc", id=1438899347453509824)
custom_emoji12 = PartialEmoji(name="6798bnb", id=1438899349110390834)
custom_emoji13 = PartialEmoji(name="tron", id=1438899350582591701)
custom_emoji14 = PartialEmoji(name="7541tetherusdt", id=1439510997730721863)

class CoinDropdown(disnake.ui.Select):
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
                embed = disnake.Embed(title="**오류**", description="**인증되지 않은 고객님입니다.**", color=0xff6200)
                await interaction.edit_original_response(embed=embed)
                return
            
            selected_coin = self.values[0]
            min_krw = get_minimum_amounts_krw().get(selected_coin.upper(), 10000)
            embed = disnake.Embed(title=f"**{selected_coin.upper()} 송금**", description=f"**최소 송금 금액 = {min_krw:,}원**", color=0xffffff)
            view = disnake.ui.View()
            view.add_item(NetworkDropdown(selected_coin))
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception as e:
            print(f"CoinDropdown callback 오류: {e}")
            embed = disnake.Embed(title="**오류**", description="**처리 중 오류가 발생했습니다.**", color=0xff6200)
            try: await interaction.edit_original_response(embed=embed)
            except: pass

class NetworkDropdown(disnake.ui.Select):
    def __init__(self, selected_coin):
        self.selected_coin = selected_coin
        
        network_options = {
            'usdt': [disnake.SelectOption(label="BEP20", description="BSC Network", value="bep20"),
                     disnake.SelectOption(label="TRC20", description="TRON Network", value="trc20")],
            'trx': [disnake.SelectOption(label="TRC20", description="TRON Network", value="trc20")],
            'ltc': [disnake.SelectOption(label="LTC", description="Litecoin Network", value="ltc")],
            'bnb': [disnake.SelectOption(label="BEP20", description="BSC Network", value="bep20")]
        }
        options = network_options.get(selected_coin.lower(), [disnake.SelectOption(label="BEP20", description="BSC Network", value="bep20")])
        super().__init__(placeholder="네트워크를 선택해주세요", options=options)

    async def callback(self, interaction):
        try: await interaction.response.send_modal(AmountModal(self.values[0], self.selected_coin))
        except Exception as e:
            print(f"NetworkDropdown callback 오류: {e}")
            embed = disnake.Embed(title="**오류**", description="**처리 중 오류가 발생했습니다.**", color=0x26272f)
            try: await interaction.response.send_message(embed=embed, ephemeral=True)
            except: pass

pending_transactions = {}

async def handle_amount_modal(interaction):
    try:
        await interaction.response.defer(ephemeral=True)
        amount_str = interaction.text_values.get("amount", "").strip()
        address = interaction.text_values.get("address", "").strip()
        
        if not amount_str or not address:
            embed = disnake.Embed(title="**오류**", description="**모든 필드를 입력해주세요.**", color=0xff6200)
            await interaction.edit_original_response(embed=embed)
            return
        
        try:
            krw_amount_input = float(amount_str)
            if krw_amount_input <= 0: raise ValueError("양수여야 합니다")
        except:
            embed = disnake.Embed(title="**오류**", description="**올바른 숫자를 입력해주세요.**", color=0xff6200)
            await interaction.edit_original_response(embed=embed)
            return
        
        custom_id_parts = interaction.custom_id.split('_')
        network = custom_id_parts[-2] if len(custom_id_parts) >= 3 else "bep20"
        coin = custom_id_parts[-1] if len(custom_id_parts) >= 4 else "usdt"
        
        min_krw = get_minimum_amounts_krw().get(coin.upper(), 10000)
        coin_unit = coin.upper()
        
        if krw_amount_input < min_krw:
            embed = disnake.Embed(title="**오류**", description=f"**출금 최소 금액은 {min_krw:,}원입니다.**", color=0xff6200)
            await interaction.edit_original_response(embed=embed)
            return
        
        user_data = get_verified_user(interaction.author.id)
        if not user_data:
            embed = disnake.Embed(title="**오류**", description="**인증되지 않은 고객님 입니다.**", color=0xff6200)
            await interaction.edit_original_response(embed=embed)
            return
        
        krw_rate = get_exchange_rate()
        coin_price = get_coin_price(coin.upper())
        if coin_price <= 0:
            embed = disnake.Embed(title="**오류**", description="**코인 가격을 조회할 수 없습니다.**", color=0xff6200)
            await interaction.edit_original_response(embed=embed)
            return
        kimchi_premium = get_kimchi_premium()
        actual_krw_rate = krw_rate * (1 + kimchi_premium / 100)

        service_fee_rate_calc = 0.025 + (kimchi_premium / 100)
        transaction_fee_coin = get_transaction_fee(coin.upper(), network.upper())
        exchange_fee_krw = transaction_fee_coin * coin_price * actual_krw_rate

        service_fee_krw = krw_amount_input * service_fee_rate_calc
        total_fee_krw = service_fee_krw + exchange_fee_krw
        actual_send_krw = krw_amount_input - total_fee_krw
        
        if coin_price * actual_krw_rate == 0: # 0으로 나누는 오류 방지 추가
             raise ValueError("코인 가격 또는 실질 환율이 0입니다. 계산 불가.")

        actual_send_amount = actual_send_krw / (coin_price * actual_krw_rate)
        krw_amount_to_subtract = int(krw_amount_input)
        
        current_balance = user_data[6] if len(user_data) > 6 else 0
        
        if current_balance < krw_amount_to_subtract:
            embed = disnake.Embed(title="**잔액 부족**", description=f"**보유 금액 = {current_balance:,}원\n필요금액: {krw_amount_to_subtract:,}원**", color=0xff6200)
            await interaction.edit_original_response(embed=embed)
            return
        
        network_name = network.upper()
        
        pending_transactions[interaction.author.id] = {
            'send_amount': actual_send_amount, 'total_amount': krw_amount_input,
            'krw_amount': krw_amount_to_subtract, 'network': network_name, 'address': address,
            'krw_rate': krw_rate, 'actual_krw_rate': actual_krw_rate, 'kimchi_premium': kimchi_premium,
            'coin': coin.upper(), 'coin_price': coin_price, 'service_fee_krw': service_fee_krw,
            'exchange_fee_krw': exchange_fee_krw, 'total_fee_krw': total_fee_krw,
            'actual_send_krw': actual_send_krw, 'fee_rate': service_fee_rate_calc               
        }
        
        embed = disnake.Embed(color=0xffffff)
        embed.add_field(name="**실제 송금 금액**", value=f"```{actual_send_amount:.6f} {coin_unit}\n{int(actual_send_krw):,}원```", inline=True)
        embed.add_field(name="**종합 수수료**", value=f"```서비스 = {int(service_fee_krw):,}원\n거래소 = {int(exchange_fee_krw):,}원\n총합 = {int(total_fee_krw):,}원```", inline=True) 
        embed.add_field(name="**네트워크**", value=f"```{network_name}```", inline=True)
        embed.add_field(name="**코인 주소**", value=f"```{address}```", inline=False)
        
        send_btn = disnake.ui.Button(label="송금하기", style=disnake.ButtonStyle.gray,
                                     custom_id="송금하기", emoji=PartialEmoji(name="send", id=1439222645035106436))
        view = disnake.ui.View()
        view.add_item(send_btn)
        await interaction.edit_original_response(embed=embed, view=view)
        
    except Exception as e:
        print(f"handle_amount_modal에서 오류 발생: {e}")
        embed = disnake.Embed(title="**오류**", description="**처리 중 오류가 발생했습니다.**", color=0xff6200)
        await interaction.edit_original_response(embed=embed)

async def handle_send_button(interaction):
    try:
        await interaction.response.defer(ephemeral=True)
        user_data = get_verified_user(interaction.author.id)
        if not user_data:
            embed = disnake.Embed(title="**오류**", description="**인증되지 않은 고객님 입니다.**", color=0xff6200)
            await interaction.edit_original_response(embed=embed)
            return
        
        transaction_data = pending_transactions.get(interaction.author.id)
        if not transaction_data:
            embed = disnake.Embed(title="**오류**", description="**송금 정보를 찾을 수 없습니다. 다시 시도해주세요.**", color=0xff6200)
            await interaction.edit_original_response(embed=embed)
            return
        
        send_amount = transaction_data.get('send_amount', 0)
        total_krw_amount_to_subtract = transaction_data.get('krw_amount', 0)
        network = transaction_data.get('network', 'BEP20').lower()
        address = transaction_data.get('address', '')
        coin = transaction_data.get('coin', 'USDT')
        
        if send_amount <= 0 or total_krw_amount_to_subtract <= 0 or not address:
            embed = disnake.Embed(title="**오류**", description="**유효하지 않은 거래 정보입니다.**", color=0xff6200)
            await interaction.edit_original_response(embed=embed)
            return
        
        processing_embed = disnake.Embed(title="**송금 처리중**", description="**조금만 기다려주세요.**", color=0xffffff)
        await interaction.edit_original_response(embed=processing_embed)
        
        if not subtract_balance(interaction.author.id, total_krw_amount_to_subtract):
            embed = disnake.Embed(title="**잔액 부족**", description="**잔액이 부족합니다.**", color=0xff6200)
            await interaction.edit_original_response(embed=embed)
            return
        
        add_transaction_history(interaction.author.id, total_krw_amount_to_subtract, "송금")
        
        transaction_result = await simple_send_coin(coin, send_amount, address, network) # async 함수이므로 await
        
        if transaction_result and transaction_result.get('success', True):
            coin_name = transaction_result.get('coin', 'USDT')
            actual_send_krw = transaction_data.get('actual_send_krw', 0)
            service_fee_krw = transaction_data.get('service_fee_krw', 0)
            exchange_fee_krw = transaction_data.get('exchange_fee_krw', 0)
            total_fee_krw = transaction_data.get('total_fee_krw', 0)
            
            success_embed = disnake.Embed(title=f"**{coin_name} 전송 성공**", color=0xffffff)
            success_embed.add_field(name="**전송 금액**", value=f"```{int(actual_send_krw):,}원```", inline=True)
            success_embed.add_field(name="종합 수수료", value=f"```서비스 = {int(service_fee_krw):,}원\n거래소 = {int(exchange_fee_krw):,}원\n총합 = ₩{int(total_fee_krw):,}원```", inline=True)
            success_embed.add_field(name="네트워크", value=f"```{transaction_result.get('network', 'N/A')}```", inline=False)
            success_embed.add_field(name="TXID", value=f"```{transaction_result.get('txid', 'N/A')}```", inline=False)
            success_embed.add_field(name="보낸주소", value=f"```{transaction_result.get('to_address', 'N/A')}```", inline=False)
            success_embed.add_field(name="보낸시간", value=f"```{transaction_result.get('time', 'N/A')}```", inline=False)
            
            await interaction.edit_original_response(embed=success_embed)

            # NOTE: 관리자/구매 로그 전송은 봇 통합 방식에 따라 조정이 필요합니다.
            # try:
            #     from bot import CHANNEL_ADMIN_LOG, CHANNEL_PURCHASE_LOG, bot as _bot
            #     admin_ch = _bot.get_channel(CHANNEL_ADMIN_LOG)
            #     if admin_ch: # ... 관리자 로그 전송 로직 ...
            #     purchase_ch = _bot.get_channel(CHANNEL_PURCHASE_LOG)
            #     if purchase_ch: # ... 구매 로그 전송 로직 ...
            # except Exception as e: print(f"로그 채널 전송 중 오류 발생: {e}")
            
            if interaction.author.id in pending_transactions:
                del pending_transactions[interaction.author.id]
                
        else:
            error_message = transaction_result.get('error', '알 수 없는 오류')
            
            # 실패 시 환불 처리
            conn = None
            try:
                os.makedirs('DB', exist_ok=True)
                conn = sqlite3.connect('DB/verify_user.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET now_amount = now_amount + ? WHERE user_id = ?', 
                              (total_krw_amount_to_subtract, interaction.author.id))
                conn.commit()
                print(f"User {interaction.author.id}에게 {total_krw_amount_to_subtract}원 환불 완료.")
            except Exception as e: print(f"환불 처리 중 오류: {e}")
            finally:
                if conn: conn.close()
            
            add_transaction_history(interaction.author.id, total_krw_amount_to_subtract, "환불")
            
            refund_embed = disnake.Embed(title="**전송 실패**", description=f"전송 중 오류가 발생하여 {total_krw_amount_to_subtract:,}원이 환불되었습니다.", color=0xff6200)
            refund_embed.add_field(name="**오류 원인**", value=f"```{error_message}```", inline=False)
            refund_embed.add_field(name="**요청 요약**",
                                    value=f"```코인: {coin}\n네트워크: {network}\n보낼양: {send_amount:.8f} {coin}\n주소: {address[:6]}...{address[-6:] if len(address)>12 else address}```",
                                    inline=False)
            await interaction.edit_original_response(embed=refund_embed)
            
            if interaction.author.id in pending_transactions: del pending_transactions[interaction.author.id]
            
            # NOTE: 실패 로그 전송 (봇 통합 방식에 따라 조정 필요)
            # try:
            #     from bot import CHANNEL_ADMIN_LOG, bot as _bot
            #     admin_ch = _bot.get_channel(CHANNEL_ADMIN_LOG)
            #     if admin_ch: # ... 실패 로그 전송 로직 ...
            # except Exception as e: print(f"실패 로그 전송 중 오류 발생: {e}")
            
    except Exception as e:
        print(f"handle_send_button에서 오류 발생: {e}")
        embed = disnake.Embed(title="**처리 중 오류 발생**", description="직원에게 문의해주세요.", color=0xff6200)
        try: await interaction.edit_original_response(embed=embed)
        except: pass

def init_coin_selenium(): return True
def quit_driver(): pass

# --- MEXC 입금 알림 기능 ---

def get_mexc_deposit_history_for_checker():
    if not API_KEY or not SECRET_KEY:
        print("경고: MEXC API_KEY 또는 SECRET_KEY가 설정되지 않았습니다. 입금 내역을 조회할 수 없습니다.")
        return []
    endpoint = "/api/v3/capital/deposit/hisrec"
    timestamp = int(time.time() * 1000)
    start_time = int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
    params = {'timestamp': timestamp, 'recvWindow': 60000, 'status': 1, 'startTime': start_time, 'limit': 100}
    signature = sign_params(params, SECRET_KEY)
    params['signature'] = signature
    headers = {'X-MEXC-APIKEY': API_KEY}
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and 'code' in data and str(data['code']) != '200':
            print(f"MEXC API 오류 (입금 내역): {data.get('msg', '알 수 없는 오류')} 코드: {data['code']}")
            return []
        if isinstance(data, list): return data
        elif isinstance(data, dict) and 'data' in data and isinstance(data['data'], list): return data['data']
        else: print(f"MEXC 입금 내역 응답 형식 예외: {data}"); return []
    except Exception as e: print(f"MEXC 입금 내역 조회 오류: {e}"); return []

def init_mexc_deposit_db():
    os.makedirs('DB', exist_ok=True)
    conn = sqlite3.connect('DB/mexc_deposits.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_mexc_deposits (
            txid TEXT PRIMARY KEY, coin TEXT, amount REAL, insert_time INTEGER,
            process_time TEXT DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%S', 'NOW'))
        );
    ''')
    conn.commit()
    conn.close()

def is_txid_processed_for_mexc_deposit(txid):
    os.makedirs('DB', exist_ok=True)
    conn = sqlite3.connect('DB/mexc_deposits.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM processed_mexc_deposits WHERE txid = ?', (txid,))
    result = cursor.fetchone() is not None
    conn.close()
    return result

def add_processed_txid_for_mexc_deposit(txid, coin, amount, insert_time):
    os.makedirs('DB', exist_ok=True)
    conn = sqlite3.connect('DB/mexc_deposits.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO processed_mexc_deposits (txid, coin, amount, insert_time) VALUES (?, ?, ?, ?)',
        (txid, coin, amount, insert_time)
    )
    conn.commit()
    conn.close()

# 봇 객체는 여기서 바로 생성하지 않습니다. main_bot.py에서 넘겨받을 것입니다.
_bot_instance = None 

def setup_api_features(bot_instance: commands.Bot):
    global _bot_instance
    _bot_instance = bot_instance
    init_mexc_deposit_db()
    mexc_deposit_loop.start()

@tasks.loop(seconds=30)
async def mexc_deposit_loop():
    if not _bot_instance:
        print("경고: _bot_instance가 설정되지 않아 mexc_deposit_loop가 작동하지 않습니다.")
        return

    deposit_records = get_mexc_deposit_history_for_checker() 
    if not deposit_records: return

    deposit_log_channel = _bot_instance.get_channel(CHANNEL_DEPOSIT_LOG_ID)
    if not deposit_log_channel:
        print(f"오류: 입금 로그 채널({CHANNEL_DEPOSIT_LOG_ID})을 찾을 수 없습니다. 설정 또는 권한 확인.")
        return

    for record in deposit_records:
        txid = record.get('txId')
        coin = record.get('coin')
        amount_str = record.get('amount')
        insert_time = record.get('insertTime')

        if not txid or not coin or not amount_str: continue
        try: amount = float(amount_str)
        except: continue
        if is_txid_processed_for_mexc_deposit(txid): continue

        krw_value = calculate_krw_value(coin, amount)

        embed = disnake.Embed(
            title="💰 MEXC 입고 완료!", description="새로운 코인 입고가 확인되었습니다.",
            color=disnake.Color.green(), timestamp=datetime.fromtimestamp(insert_time / 1000)
        )
        embed.add_field(name="입고 금액", value=f"```🥳 {krw_value:,}원 🥳```", inline=False)
        try:
            await deposit_log_channel.send(embed=embed)
            add_processed_txid_for_mexc_deposit(txid, coin, amount, insert_time)
            print(f"입고 알림 성공: {coin} {amount} (KRW {krw_value}) TXID: {txid}")
        except Exception as e: print(f"입고 알림 전송 실패 TXID {txid}: {e}")

이 코드에 입고 로그, 자동 스왑+수수료 최적화 로직 짜서 완성본 보내줘 기능 다 포함해서 기능빼먹지말고 그리고 맨위에 오류나는 코드 부분 다 고쳐줘 진짜 이번이 마지막임 ㅠㅠㅠㅠㅠㅠㅠㅠ
