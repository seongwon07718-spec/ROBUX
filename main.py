def sign_params(params, secret):
    """
    서명 생성: 파라미터 키 알파벳 순 정렬 후 URL-인코딩 없이 "&" 연결, HMAC SHA256 해시
    숫자형(amount 등)은 소수점 8자리 표현 문자열로 변환하고, 모든 값은 문자열이어야 함
    """
    try:
        # 숫자형 'amount' 처리 및 문자열 변환
        temp_params = {k: (f"{v:.8f}" if (k == 'amount' and isinstance(v, float)) else str(v)) for k, v in params.items()}
        sorted_params = sorted(temp_params.items())
        query_string = '&'.join(f"{k}={v}" for k, v in sorted_params)
        signature = hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        return signature
    except Exception as e:
        print(f"sign_params error: {e}")
        return None

def send_coin_transaction(amount, address, network, coin='USDT'):
    if not API_KEY or not SECRET_KEY:
        return {'success': False, 'error': 'API 키 설정 필요'}

    network_mapping = {'bep20': 'BSC', 'trc20': 'TRX', 'ltc': 'LTC', 'bnb': 'BSC'}
    network_code = network_mapping.get(network.lower())
    if not network_code:
        return {'success': False, 'error': f'지원하지 않는 네트워크: {network}'}

    timestamp = int(time.time() * 1000)
    params = {
        'coin': coin.upper(),
        'address': address.strip(),
        'amount': round(amount, 8),
        'netWork': network_code,
        'recvWindow': 60000,
        'timestamp': timestamp
    }

    signature = sign_params(params, SECRET_KEY)
    if not signature:
        return {'success': False, 'error': '서명 생성 실패'}

    params['signature'] = signature

    headers = {'X-MEXC-APIKEY': API_KEY, 'Content-Type': 'application/json'}

    try:
        # POST 요청 시, 쿼리스트링으로 요청하면 안 되며 json 본문으로 보내야 함
        # 다만 API 문서가 명확하면 그대로 쿼리스트링으로 보내도 되나 대부분 body로 전달 권장
        url = f"{BASE_URL}/api/v3/capital/withdraw"
        response = requests.post(url, headers=headers, json=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get('id'):
            txid = str(data['id'])
            return {'success': True, 'txid': txid, 'coin': coin.upper()}
        else:
            return {'success': False, 'error': f"API 오류: {data.get('msg', '알 수 없음')}"}
    except requests.RequestException as e:
        err_msg = ""
        try:
            err_msg = response.json()
        except Exception:
            err_msg = str(e)
        return {'success': False, 'error': f"통신 오류: {err_msg}"}
    except Exception as e:
        return {'success': False, 'error': f"예기치 못한 오류: {str(e)}"}
