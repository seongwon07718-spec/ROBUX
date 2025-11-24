import disnake
from disnake.ext import commands, tasks
import time
from datetime import datetime
# logger, coin, get_stock_amount, get_exchange_rate 등은 외부에서 정의되었다고 가정합니다.

# ----------------------------------------------------------------------
# 1. 전역 변수 선언 (봇 파일 최상단에 위치)
# ----------------------------------------------------------------------
embed_message = None
current_stock = 0
current_rate = 0
last_update_time = datetime.now()
embed_updating = False
api_update_counter = 0
# timer_message, stop_event 등 사용되는 전역 변수들도 여기에 선언되어야 합니다.


# ----------------------------------------------------------------------
# 2. 2분마다 실행되는 자동 업데이트 루프
# ----------------------------------------------------------------------
@tasks.loop(seconds=120)
async def update_embed_task():
    global embed_message, current_stock, current_rate, last_update_time, embed_updating, api_update_counter
    
    try:
        if embed_message is None:
            # 메시지가 없으면 루프를 중지합니다.
            update_embed_task.cancel() 
            return
        
        embed_updating = True
        
        # API 호출 및 재고/환율 업데이트 로직
        api_update_counter += 1
        if api_update_counter >= 1: 
            new_stock = get_stock_amount()
            new_rate = get_exchange_rate()
            
            if new_stock != current_stock or new_rate != current_rate:
                current_stock = new_stock
                current_rate = new_rate
            
            api_update_counter = 0
            
        last_update_time = datetime.now()
        
        # 코인 데이터 갱신
        all_balances = coin.get_all_balances()
        all_prices = coin.get_all_coin_prices()
        
        supported_coins = ['USDT', 'BNB', 'TRX', 'LTC']
        balance_text = ""
        total_krw_value = 0
        
        for coin_symbol in supported_coins:
            balance = all_balances.get(coin_symbol, 0)
            if balance > 0:
                price = all_prices.get(coin_symbol, 0)
                krw_value = balance * price * current_rate
                total_krw_value += krw_value
                balance_text += f"**```🛒 {krw_value:,.0f}원```**\n"
        
        # 김치프리미엄 조회
        kimchi_premium = coin.get_kimchi_premium()
        embed = disnake.Embed(color=0xffffff)
        try:
            embed.set_thumbnail(url=EMBED_ICON_URL)
        except Exception:
            pass
        
        # ★★★ 타이머 리셋 로직 (2분마다 '1초 전'부터 시작) ★★★
        timestamp_str = f"<t:{int(time.time()) - 1}:R>"

        embed.add_field(name="**실시간 재고**", value=balance_text if balance_text else "**```🛒 0원```**", inline=True)
        embed.add_field(name="**실시간 김프**", value=f"**```📈 {kimchi_premium:.2f}%```**", inline=True)
        embed.add_field(
            name=f"**<a:sexymega:1441678230175350817>{timestamp_str}에 재고, 김프가 갱신되었습니다**",
            value="**――――――――――――――――――――**",
            inline=False
        )
        embed.set_footer(text="Tip : 정보 조회 버튼 누르시면 거래내역 확인 가능")

        view = CoinView()
        await embed_message.edit(embed=embed, view=view)
        embed_updating = False
        
    except disnake.HTTPException as e:
        logger.error(f"업데이트 도중 에러: 메시지를 찾을 수 없음 또는 권한 부족: {e}")
        embed_message = None
        embed_updating = False
    except Exception as e:
        logger.error(f"업데이트 도중 일반 에러: {e}")
        embed_updating = False


# ----------------------------------------------------------------------
# 3. 슬래시 명령어 정의 (패널 전송 및 루프 시작)
# ----------------------------------------------------------------------
@bot.slash_command(name="대행패널", description="대행 패널 전송")
async def service_embed(inter):
    global embed_message, current_stock, current_rate, last_update_time

    try:
        # 3초 타임아웃 방지용 선미응답
        await inter.response.defer(ephemeral=True)

        # 허용된 사용자만 사용 가능
        if inter.author.id not in ALLOWED_USER_IDS:
            embed = disnake.Embed(
                title="**접근 거부**",
                description="**이 명령어는 허용된 사용자만 사용할 수 있습니다.**",
                color=0xff0000
            )
            await inter.edit_original_response(embed=embed)
            return

        # 관리자 권한 확인
        if not check_admin(inter.author.id):
            embed = disnake.Embed(
                title="**오류**",
                description="**권한이 없습니다.**",
                color=0xff6200
            )
            await inter.edit_original_response(embed=embed)
            return

        # --- [초기 데이터 로드] ---
        # 루프에서 사용할 데이터도 여기서 초기화
        all_balances = coin.get_all_balances()
        all_prices = coin.get_all_coin_prices()
        current_stock = get_stock_amount() # 초기 재고/환율 로드
        current_rate = get_exchange_rate() 
        last_update_time = datetime.now()


        supported_coins = ['USDT', 'BNB', 'TRX', 'LTC']
        balance_text = ""
        total_krw_value = 0
        for coin_symbol in supported_coins:
            balance = all_balances.get(coin_symbol, 0)
            if balance > 0:
                price = all_prices.get(coin_symbol, 0)
                krw_value = balance * price * current_rate
                total_krw_value += krw_value
                balance_text += f"**```🛒 {krw_value:,.0f}원```**\n"

        # 김치 프리미엄 조회
        kimchi_premium = coin.get_kimchi_premium()

        embed = disnake.Embed(color=0xffffff)
        try:
            embed.set_thumbnail(url=EMBED_ICON_URL)
        except Exception:
            pass

        # ★★★ 최초 타임스탬프 설정 (1초 전부터 카운트 시작) ★★★
        timestamp_str = f"<t:{int(time.time()) - 1}:R>"

        embed.add_field(name="**실시간 재고**", value=balance_text if balance_text else "**```🛒 0원```**", inline=True)
        embed.add_field(name="**실시간 김프**", value=f"**```📈 {kimchi_premium:.2f}%```**", inline=True)
        embed.add_field(
            name=f"**<a:sexymega:1441678230175350817>{timestamp_str}에 재고, 김프가 갱신되었습니다**",
            value="**――――――――――――――――――――**",
            inline=False
        )
        embed.set_footer(text="Tip : 정보 조회 버튼 누르시면 거래내역 확인 가능")

        view = CoinView()
        # 메시지를 전송하고 전역 변수에 저장
        embed_message = await inter.channel.send(embed=embed, view=view)

        # ★★★ 루프 시작/재시작 ★★★
        if update_embed_task.is_running():
            update_embed_task.restart()
        else:
            update_embed_task.start()

        # 관리자 응답
        admin_embed = disnake.Embed(color=0xffffff)
        admin_embed.add_field(name="대행 전송", value=f"**{inter.author.display_name}** 대행임베드를 사용함", inline=False)
        await inter.edit_original_response(embed=admin_embed)

    except Exception as e:
        logger.error(f"대행임베드 오류: {e}")
        error_embed = disnake.Embed(
            title="**오류**",
            description="**처리 중 오류가 발생했습니다.**",
            color=0xff6200
        )
        try:
            await inter.edit_original_response(embed=error_embed)
        except Exception:
            pass
