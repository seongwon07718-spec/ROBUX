import discord
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime, timedelta
import random
import json
import os
import logging
from discord import PartialEmoji, ui, app_commands
from PIL import Image
from io import BytesIO
import math

# 외부 모듈 (직접 구현 필요)
from pass_verify import make_passapi, send_passapi, verify_passapi
import coin
from api import set_service_fee_rate, get_service_fee_rate, get_user_tier_and_fee

# ===== 봇 설정 =====
TOKEN = ''  # 실제 봇 토큰 입력
DEFAULT_ADMIN_ID = 1402654236570812467
ALLOWED_USER_IDS = [1402654236570812467]  # 중복 제거

EMBED_ICON_URL = "https://encrypted-tbn0.gstatic.com/image6jLPhxp5TLkKPq1sfTvMADTF4A&s"

DEPOSIT_BANK_NAME = "토스뱅크"
DEPOSIT_ACCOUNT_NO = "1001"
DEPOSIT_ACCOUNT_HOLDER = "정"

CHANNEL_PURCHASE_LOG = 1436586235886829588
CHANNEL_TRANSFER_LOG = 1436602282719580281
CHANNEL_VERIFY_LOG = 1438855210121433141
CHANNEL_CHARGE_LOG = 1436602243905228831
CHANNEL_ADMIN_LOG = 1436602585862766612
CHANNEL_DEPOSIT_LOG = 1436584475407548416

PURCHASE_LOG_TITLE = "🎉 대행 이용"
PURCHASE_LOG_DESCRIPTION = "익명 고객님 {amount:,}원 대행 감사합니다.\n오늘도 좋은하루 되시길 바랍니다."
PURCHASE_LOG_FOOTER = "브레인롯 코인대행"

VERIFY_LOG_TITLE = "✅ PASS 인증 완료"
VERIFY_LOG_DESCRIPTION = (
    "PASS 본인인증 성공\n- 사용자: {user_mention} ({user_id})\n"
    "- 이름: {name}\n- 휴대폰: {phone}\n- 생년월일: {birth}\n- 통신사: {telecom}"
)

CHARGE_REQUEST_TITLE = "💰 충전 요청"
CHARGE_REQUEST_DESCRIPTION = (
    "충전 요청이 접수되었습니다.\n- 사용자: {user_mention} ({user_id})\n- 요청 금액: ₩{amount:,}\n- 현재 잔액: ₩{balance:,}"
)

CHARGE_APPROVE_TITLE = "✅ 충전 승인"
CHARGE_APPROVE_DESCRIPTION = (
    "충전이 승인되었습니다.\n- 사용자: {user_mention} ({user_id})\n- 승인 금액: ₩{amount:,}\n- 승인자: {approver}"
)

CHARGE_REJECT_TITLE = "❌ 충전 거절"
CHARGE_REJECT_DESCRIPTION = (
    "충전이 거절되었습니다.\n- 사용자: {user_mention} ({user_id})\n- 거절 금액: ₩{amount:,}\n- 거절자: {rejector}"
)

TRANSFER_LOG_TITLE = "💸 송금 완료"
TRANSFER_LOG_DESCRIPTION = (
    "송금 완료\n- 사용자: {user_mention} ({user_id})\n- 코인 종류: {coin_name}\n- 금액: ₩{amount:,}\n"
    "- TXID: `{txid}`\n- 처리 시간: {timestamp}"
)

LOG_FILE = 'bot.log'
LOG_LEVEL = logging.INFO

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 권한 체크
def is_allowed_user(user_id: int) -> bool:
    return user_id in ALLOWED_USER_IDS

def check_admin(user_id: int) -> bool:
    try:
        if user_id == DEFAULT_ADMIN_ID:
            return True
        conn = sqlite3.connect('DB/admin.db')
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM admins WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"직원 확인 오류: {e}")
        return False

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

user_sessions = {}
embed_message = None
pending_charge_requests = {}
current_stock = 0
current_rate = 1350
last_update_time = datetime.now()

# 대행임베드 명령어에서 보여줄 임베드 생성 함수
def create_service_embed(stock_krw: float, kimchi_premium: float, remain_seconds: int) -> discord.Embed:
    embed = discord.Embed(title="실시간 재고", color=0x303136)
    embed.add_field(name="📦", value=f"{stock_krw:,.0f}원", inline=False)
    embed.add_field(name="김프 (%)", value=f"📈 {kimchi_premium:.2f}%", inline=False)

    minute = remain_seconds // 60
    second = remain_seconds % 60

    if minute > 0:
        time_str = f"{minute}분 {second}초"
    else:
        time_str = f"{second}초"

    embed.add_field(name="\u200b", value=f"**{time_str} 후 재고가 갱신됩니다.**\n{'─' * 40}", inline=False)
    embed.add_field(name="Tip", value="내역 조회는 정보조회를 통해 가능합니다.", inline=False)
    return embed

@bot.tree.command(name="대행임베드", description="대행 서비스 UI 출력")
async def service_embed(interaction: discord.Interaction):
    global embed_message, current_stock, current_rate, last_update_time

    try:
        if not is_allowed_user(interaction.user.id) or not check_admin(interaction.user.id):
            embed = discord.Embed(title="접근 거부", description="이 명령어는 허용된 사용자만 사용할 수 있습니다.", color=0x26272f)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        current_stock = coin.get_balance()
        current_rate = coin.get_exchange_rate()
        last_update_time = datetime.now()

        remain = 60  # 갱신 남은 시간: 초기값 60초

        embed = create_service_embed(current_stock, coin.get_kimchi_premium(), remain)

        await interaction.response.send_message(embed=embed)
        embed_message = await interaction.original_response()

    except Exception as e:
        logger.error(f"대행임베드 명령어 오류: {e}")
        embed = discord.Embed(title="오류", description="임베드 생성 중 오류가 발생했습니다.", color=0xFF0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tasks.loop(seconds=5)
async def update_embed_loop():
    global embed_message, current_stock, current_rate, last_update_time

    if embed_message is None:
        return

    try:
        elapsed = (datetime.now() - last_update_time).seconds
        remain = max(0, 60 - elapsed)

        # 60초마다 재고 및 환율 갱신
        if remain == 0:
            current_stock = coin.get_balance()
            current_rate = coin.get_exchange_rate()
            last_update_time = datetime.now()
            remain = 60

        embed = create_service_embed(current_stock, coin.get_kimchi_premium(), remain)
        await embed_message.edit(embed=embed)
    except Exception as e:
        logger.error(f"임베드 자동 갱신 실패: {e}")
        embed_message = None

@bot.event
async def on_ready():
    logger.info(f'{bot.user} 준비 완료')
    update_embed_loop.start()

# 나머지 명령어, 기능들은 기존 코드 유지하며 위 구조 참고해 통합 적용합니다.

if __name__ == "__main__":
    bot.run(TOKEN)
