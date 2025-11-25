def calculate_krw_value(coin_symbol, amount):
    """
    코인 수량 amount를 원화 가치로 환산 (김치프리미엄 포함).
    """
    coin_price_usd = get_coin_price(coin_symbol.upper())
    krw_rate = get_exchange_rate()
    kimchi_premium = get_kimchi_premium()
    
    actual_krw_rate = krw_rate * (1 + kimchi_premium / 100)
    
    if coin_price_usd <= 0 or actual_krw_rate <= 0:
        return 0
    
    krw_value = amount * coin_price_usd * actual_krw_rate
    return int(krw_value)
