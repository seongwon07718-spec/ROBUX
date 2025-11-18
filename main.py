import disnake
from disnake.ext import commands, tasks
import sqlite3
from datetime import datetime, timedelta
import random
import json
import os
import logging
from disnake import PartialEmoji, ui
from PIL import Image
from io import BytesIO
import math
from pass_verify import make_passapi, send_passapi, verify_passapi

import coin
from api import set_service_fee_rate, get_service_fee_rate, get_user_tier_and_fee

# ===== 봇 설정 =====
TOKEN = ''
DEFAULT_ADMIN_ID = 1402654236570812467
# 슬래시 명령어 사용 가능한 사용자 ID (요청: 두 사용자만 허용)
ALLOWED_USER_IDS = [1402654236570812467, 1402654236570812467]

# 임베드 공통 썸네일(외부 이미지 이모지 대용)
EMBED_ICON_URL = "https://encrypted-tbn0.gstatic.com/image6jLPhxp5TLkKPq1sfTvMADTF4A&s"

# ===== 충전 계좌 설정 =====
DEPOSIT_BANK_NAME = "토스뱅크"
DEPOSIT_ACCOUNT_NO = "1001"
DEPOSIT_ACCOUNT_HOLDER = "정"

# ===== 채널 설정 =====
CHANNEL_PURCHASE_LOG = 1436586235886829588
CHANNEL_TRANSFER_LOG = 1436602282719580281
CHANNEL_VERIFY_LOG = 1438855210121433141
CHANNEL_CHARGE_LOG = 1436602243905228831
CHANNEL_ADMIN_LOG = 1436602585862766612
CHANNEL_DEPOSIT_LOG = 1436584475407548416

# ===== 메시지 템플릿 설정 =====
PURCHASE_LOG_TITLE = "🎉 대행 이용"
PURCHASE_LOG_DESCRIPTION = "익명 고객님 {amount:,}원 대행 감사합니다.\n오늘도 좋은하루 되시길 바랍니다."
PURCHASE_LOG_FOOTER = "브레인롯 코인대행"

VERIFY_LOG_TITLE = "✅ PASS 인증 완료"
VERIFY_LOG_DESCRIPTION = "PASS 본인인증 성공\n- 사용자: {user_mention} ({user_id})\n- 이름: {name}\n- 휴대폰: {phone}\n- 생년월일: {birth}\n- 통신사: {telecom}"

CHARGE_REQUEST_TITLE = "💰 충전 요청"
CHARGE_REQUEST_DESCRIPTION = "충전 요청이 접수되었습니다.\n- 사용자: {user_mention} ({user_id})\n- 요청 금액: ₩{amount:,}\n- 현재 잔액: ₩{balance:,}"

CHARGE_APPROVE_TITLE = "✅ 충전 승인"
CHARGE_APPROVE_DESCRIPTION = "충전이 승인되었습니다.\n- 사용자: {user_mention} ({user_id})\n- 승인 금액: ₩{amount:,}\n- 승인자: {approver}"

CHARGE_REJECT_TITLE = "❌ 충전 거절"
CHARGE_REJECT_DESCRIPTION = "충전이 거절되었습니다.\n- 사용자: {user_mention} ({user_id})\n- 거절 금액: ₩{amount:,}\n- 거절자: {rejector}"

TRANSFER_LOG_TITLE = "💸 송금 완료"
TRANSFER_LOG_DESCRIPTION = "송금 완료\n- 사용자: {user_mention} ({user_id})\n- 코인 종류: {coin_name}\n- 금액: ₩{amount:,}\n- TXID: `{txid}`\n- 처리 시간: {timestamp}"

# ===== 로그 설정 =====
LOG_FILE = 'bot.log'
LOG_LEVEL = logging.INFO

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== 명령어 권한 체크 함수 =====
def is_allowed_user(user_id):
    return user_id in ALLOWED_USER_IDS

intents = disnake.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

user_sessions = {}
embed_updating = False
pending_charge_requests = {}

# ===== 수정: UI 컨테이너 기반 대행임베드 뷰 =====
class ServiceContainerView(ui.LayoutView):
    def __init__(self, stock_display: str, kimchi_premium_display: str):
        super().__init__(timeout=None)

        c = ui.Container()
        c.add_item(ui.TextDisplay("**BTCC | 코인대행**"))
        c.add_item(ui.TextDisplay("아래 버튼을 눌러 이용해주세요"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.add_item(c)

        stock_kimchi_container = ui.Container()
        stock_btn = ui.Button(label=f"실시간 재고: {stock_display}", style=disnake.ButtonStyle.grey, disabled=True)
        kimchi_btn = ui.Button(label=f"실시간 김프: {kimchi_premium_display}", style=disnake.ButtonStyle.grey, disabled=True)
        stock_kimchi_container.add_item(stock_btn)
        stock_kimchi_container.add_item(kimchi_btn)
        self.add_item(stock_kimchi_container)

        self.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        button_container = ui.Container()

        # 기존 이모지 그대로 사용
        emoji_send = PartialEmoji(name="send", id=1439222645035106436)
        emoji_info = PartialEmoji(name="info", id=1439222648512053319)
        emoji_charge = PartialEmoji(name="charge", id=1439222646641262706)

        send_button = ui.Button(label="송금", style=disnake.ButtonStyle.grey, emoji=emoji_send, custom_id="use_service_button")
        info_button = ui.Button(label="정보 보기", style=disnake.ButtonStyle.grey, emoji=emoji_info, custom_id="my_info_button")
        charge_button = ui.Button(label="충전", style=disnake.ButtonStyle.grey, emoji=emoji_charge, custom_id="charge_button")

        button_container.add_item(send_button)
        button_container.add_item(info_button)
        button_container.add_item(charge_button)
        self.add_item(button_container)

        tail_container = ui.Container()
        tail_container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        tail_container.add_item(ui.TextDisplay("Tip : 송금 내역은 정보 보기 버튼을 통해 볼 수 있습니다."))
        self.add_item(tail_container)

# ===== 수정: 대행임베드 명령어 =====
@bot.slash_command(name="대행임베드", description="컨테이너 박스 대행임베드 출력")
async def service_embed(inter):
    try:
        await inter.response.defer(ephemeral=True)
        if inter.author.id not in ALLOWED_USER_IDS or not check_admin(inter.author.id):
            embed = disnake.Embed(
                title="**권한 없음**",
                description="이 명령어는 허용된 사용자만 사용할 수 있습니다.",
                color=0x26272f
            )
            await inter.edit_original_response(embed=embed)
            return

        global embed_message, current_rate
        all_balances = coin.get_all_balances()
        all_prices = coin.get_all_coin_prices()
        supported_coins = ['USDT', 'BNB', 'TRX', 'LTC']
        total_krw_value = 0
        for coin_symbol in supported_coins:
            balance = all_balances.get(coin_symbol, 0)
            if balance > 0:
                price = all_prices.get(coin_symbol, 0)
                total_krw_value += balance * price * current_rate

        stock_display_value = f"{total_krw_value / current_rate:,.2f} USDT" if total_krw_value > 0 else "재고 없음"
        kimchi_premium_value = f"{coin.get_kimchi_premium():.2f}%"

        view = ServiceContainerView(stock_display_value, kimchi_premium_value)
        embed_message = await inter.channel.send("대행 서비스", view=view)

        admin_embed = disnake.Embed(color=0x26272f)
        admin_embed.add_field(name="전송 성공", value=f"{inter.author.display_name} 님이 대행임베드를 사용함", inline=False)
        await inter.edit_original_response(embed=admin_embed)

    except Exception as e:
        logger.error(f"대행임베드 오류: {e}")
        error_embed = disnake.Embed(
            title="**오류**",
            description="처리 중 오류가 발생했습니다.",
            color=0x26272f
        )
        try:
            await inter.edit_original_response(embed=error_embed)
        except:
            pass

# 나머지 코드는 요청대로 수정 없이 그대로 유지해 주세요.
