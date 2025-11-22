# explorer_api.py
import requests, logging, os
logger = logging.getLogger(__name__)

# 권장: BscScan API 키 발급 후 설정
BSCSCAN_API_KEY = ""  # 여기에 키 넣으세요 (필수 아님, 있으니 정확도/한도 좋아짐)

def fetch_bsc_tx(txid):
    try:
        if not BSCSCAN_API_KEY:
            # API 키 없으면 실패(권장: 키 사용)
            return None
        url = f"https://api.bscscan.com/api?module=account&action=tokentx&txhash={txid}&apikey={BSCSCAN_API_KEY}"
        r = requests.get(url, timeout=15).json()
        if r.get('status') == '1' and r.get('result'):
            # 여러 이벤트 중 첫 수신 이벤트 사용(운영 환경에선 더 정교히 필터 필요)
            evt = r['result'][0]
            to_addr = evt.get('to')
            from_addr = evt.get('from')
            token_symbol = evt.get('tokenSymbol')
            decimals = int(evt.get('tokenDecimal') or 0)
            value = int(evt.get('value') or 0)
            amount = value / (10 ** decimals) if decimals else float(value)
            return {'to_address': to_addr, 'from_address': from_addr, 'amount': amount, 'token_symbol': token_symbol, 'decimals': decimals, 'status': 'success'}
        return None
    except Exception as e:
        logger.exception(e)
        return None

def fetch_trx_tx(txid):
    try:
        url = f"https://apilist.tronscan.org/api/transaction-info?hash={txid}"
        r = requests.get(url, timeout=15).json()
        # Parsing may vary; try token transfers field
        tts = r.get('tokenTransfers') or r.get('token_transfer')
        if tts and len(tts) > 0:
            t = tts[0]
            to = t.get('to_address') or t.get('to')
            frm = t.get('from_address') or t.get('from')
            amount = float(t.get('amount') or 0)
            # decimals may be in token_info
            decimals = int(t.get('tokenInfo', {}).get('decimals', 0) or 0)
            amount = amount / (10**decimals) if decimals else amount
            symbol = t.get('tokenInfo', {}).get('symbol') or t.get('tokenName')
            return {'to_address': to, 'from_address': frm, 'amount': amount, 'token_symbol': symbol, 'decimals': decimals, 'status': 'success'}
        return None
    except Exception as e:
        logger.exception(e)
        return None

def fetch_blockchair_tx(chain, txid):
    try:
        url = f"https://api.blockchair.com/{chain}/dashboards/transaction/{txid}"
        r = requests.get(url, timeout=15).json()
        data = r.get('data', {}).get(txid, {})
        return {'raw': data, 'status':'success'}
    except Exception as e:
        logger.exception(e)
        return None

def fetch_solana_tx(txid):
    try:
        url = f"https://public-api.solscan.io/transaction/{txid}"
        r = requests.get(url, timeout=15)
        if r.status_code != 200: return None
        return {'raw': r.json(), 'status':'success'}
    except Exception as e:
        logger.exception(e)
        return None

def fetch_tx_raw(coin, txid):
    coin = coin.upper()
    if coin in ('BNB','USDT'):
        return fetch_bsc_tx(txid)
    if coin == 'TRX':
        return fetch_trx_tx(txid)
    if coin in ('LTC','DOGE'):
        chain = 'litecoin' if coin=='LTC' else 'dogecoin'
        return fetch_blockchair_tx(chain, txid)
    if coin in ('SOL','SOLANA'):
        return fetch_solana_tx(txid)
    return None
