# api.py (간단 구현)
import requests, logging
logger = logging.getLogger(__name__)

def get_exchange_rate():
    try:
        r = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=KRW", timeout=10).json()
        return float(r.get('rates', {}).get('KRW', 1350))
    except Exception:
        return 1350.0

def get_coin_price(coin_symbol):
    # coin_symbol: USDT, BNB, TRX, LTC, DOGE, SOL
    try:
        if coin_symbol.upper() == 'USDT':
            return 1.0
        # try CoinGecko (no API key)
        cg = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin_symbol.lower()}&vs_currencies=usd", timeout=10)
        data = cg.json()
        val = data.get(coin_symbol.lower(), {}).get('usd')
        if val: return float(val)
    except Exception as e:
        logger.exception(e)
    # fallback values
    fallback = {'BNB': 300.0, 'TRX': 0.06, 'LTC': 80.0, 'DOGE': 0.06, 'SOL': 20.0}
    return float(fallback.get(coin_symbol.upper(), 1.0))
