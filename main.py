# 입금 내역 중복 알림 방지를 위한 마지막 타임스탬프 메모리 저장
last_deposit_checked_timestamp = 0

async def check_mexc_deposits(bot):
    global last_deposit_checked_timestamp
    if not API_KEY or not SECRET_KEY:
        print("API 키 미설정 - 입고 감지 불가")
        return

    try:
        endpoint = "/api/v3/capital/deposit/hisrec"
        timestamp = int(time.time() * 1000)
        params = {
            'timestamp': timestamp,
            'status': 1,
            'recvWindow': 60000,
            'limit': 50
        }
        signature = sign_params(params, SECRET_KEY)
        if not signature:
            print("서명 생성 실패")
            return

        params['signature'] = signature
        headers = {'X-MEXC-APIKEY': API_KEY}
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        # MEXC v3 API 문서에 따라 입금 내역 위치 확인 필요
        deposits = data.get('data', []) if 'data' in data else data

        new_deposits = []
        for d in deposits:
            deposit_time = d.get('created_time') or d.get('time') or d.get('createdAt')
            if deposit_time is None:
                continue
            
            # 입금 시간은 보통 밀리초 단위 정수여야 함
            if isinstance(deposit_time, str) and deposit_time.isdigit():
                deposit_time = int(deposit_time)
            elif isinstance(deposit_time, str):
                # ISO 포맷일 경우 변환 필요 (예외처리)
                try:
                    dt_obj = datetime.fromisoformat(deposit_time)
                    deposit_time = int(dt_obj.timestamp() * 1000)
                except Exception:
                    deposit_time = 0
            
            if deposit_time > last_deposit_checked_timestamp:
                new_deposits.append(d)

        if not new_deposits:
            return

        # 최신 입금 시간 갱신
        last_deposit_checked_timestamp = max(int(d.get('created_time', 0)) for d in new_deposits)

        # 디스코드 알림 전송
        for deposit in new_deposits:
            coin = deposit.get('coin')
            amount = float(deposit.get('amount', 0))
            network = deposit.get('network')
            txid = deposit.get('txId') or deposit.get('txid') or 'N/A'
            await send_deposit_log_to_discord(bot, coin, amount, network, txid)

    except Exception as e:
        print(f"입금 감지 오류: {e}")

async def send_deposit_log_to_discord(bot, coin, amount, network, txid):
    try:
        channel = bot.get_channel(CHANNEL_DEPOSIT_LOG)
        if channel is None:
            print("입고 로그 채널을 찾을 수 없습니다.")
            return

        krw_rate = get_exchange_rate() or 1350.0
        coin_price_usd = get_coin_price(coin)
        krw_value = int(amount * coin_price_usd * krw_rate) if coin_price_usd > 0 else 0

        embed = disnake.Embed(
            title=f"🛒 입고 완료 ({coin})",
            description=f"**{amount:.8f} {coin}** 입고 확인되었습니다.",
            color=0x4caf50
        )
        embed.add_field(name="입고 금액 (KRW 환산)", value=f"**{krw_value:,}원**", inline=False)
        embed.add_field(name="네트워크", value=network, inline=True)
        embed.add_field(name="TXID", value=f"[{txid}](https://www.blockchain.com/{coin.lower()}/tx/{txid})", inline=True)
        embed.set_footer(text=f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        await channel.send(embed=embed)
    except Exception as e:
        print(f"디스코드 입고 알림 전송 실패: {e}")
