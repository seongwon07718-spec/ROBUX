import disnake
from disnake.ext import commands
import sqlite3
import logging # 로깅을 위해 import

# --- 설정값 (실제 값으로 변경해주세요) ---
# ALLOWED_USER_IDS: 이 명령어를 사용할 수 있는 관리자 유저 ID 목록 (int)
ALLOWED_USER_IDS = [1202376635128340, 1402654236570812467] # 튜어오오오옹님의 ID 및 Discord Admin ID 예시

# CHANNEL_CHARGE_LOG: 충전/차감 로그 메시지를 보낼 채널 ID (int)
CHANNEL_CHARGE_LOG = 1234567890123456789 # 실제 로그 채널 ID로 변경해주세요.
# ----------------------------------------

# 로깅 설정 (로깅이 되어있지 않다면 아래 코드를 bot.py 맨 위에 추가해주세요)
# if not logging.getLogger(__name__).handlers:
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 데이터베이스 유틸리티 함수 (bot.py 또는 api.py에 존재해야 함) ---
# 기존에 사용하시던 coin 모듈 또는 직접 구현된 DB 함수들을 활용해주세요.
# 여기서는 SQLite를 가정한 예시를 포함합니다. 실제 DB에 맞게 수정해주세요.

DB_PATH = 'DB/verify_user.db' # 고객 정보 DB 경로
HISTORY_DB_PATH = 'DB/history.db' # 거래 내역 DB 경로

def check_admin(user_id: int) -> bool:
    # 이 명령어를 사용할 수 있는 관리자 권한을 체크합니다.
    # ALLOWED_USER_IDS에 해당하면 True를 반환합니다.
    return user_id in ALLOWED_USER_IDS

def get_user_balance_info(user_id: int):
    """지정된 유저의 잔액 정보를 가져옵니다."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # users 테이블 구조에 맞게 필드를 조정해주세요. (user_id, now_amount, total_amount, user_name)
        cursor.execute('SELECT user_id, now_amount, Total_amount, user_name FROM users WHERE user_id = ?', (user_id,))
        user_info = cursor.fetchone()
        return user_info
    except sqlite3.Error as e:
        logger.error(f"DB Error (get_user_balance_info) for user_id {user_id}: {e}")
        return None
    finally:
        if conn: conn.close()

def update_user_balance(user_id: int, amount: int, action_type: str) -> bool:
    """유저의 잔액을 업데이트하고, 총액도 함께 업데이트합니다. (True: 성공, False: 실패)"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT now_amount, Total_amount FROM users WHERE user_id = ?', (user_id,))
        current_data = cursor.fetchone()

        if not current_data:
            logger.warning(f"update_user_balance: User {user_id} not found in DB.")
            return False

        current_balance, total_amount = current_data[0] or 0, current_data[1] or 0

        new_balance = current_balance
        new_total_amount = total_amount

        if action_type == "추가":
            new_balance += amount
            new_total_amount += amount
            log_type = "잔액추가"
        elif action_type == "차감":
            if current_balance < amount:
                logger.warning(f"update_user_balance: User {user_id} insufficient balance for subtraction (current: {current_balance}, requested: {amount}).")
                return False # 잔액 부족
            new_balance -= amount
            # 차감은 Total_amount에 영향을 주지 않음 (구매 총액과 다름)
            log_type = "잔액차감"
        else:
            logger.error(f"update_user_balance: Invalid action_type '{action_type}' for user {user_id}.")
            return False

        cursor.execute('UPDATE users SET now_amount = ?, Total_amount = ? WHERE user_id = ?', (new_balance, new_total_amount, user_id))
        conn.commit()

        # 거래 내역 기록
        add_transaction_history(user_id, amount, log_type)
        return True

    except sqlite3.Error as e:
        logger.error(f"DB Error (update_user_balance) for user_id {user_id}: {e}")
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()

def add_transaction_history(user_id: int, amount: int, transaction_type: str):
    """거래 내역을 기록합니다."""
    conn = None
    try:
        conn = sqlite3.connect(HISTORY_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO transaction_history (user_id, amount, type, timestamp) VALUES (?, ?, ?, ?)',
            (user_id, amount, transaction_type, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"DB Error (add_transaction_history) for user_id {user_id}: {e}")
    finally:
        if conn: conn.close()

# --- 슬래시 명령어 정의 ---
# bot 객체는 이미 정의되어 있다고 가정합니다 (예: bot = commands.Bot(...) )
# `bot` 변수를 사용하는 명령어 데코레이터입니다.

@bot.slash_command(
    name="수동잔액관리", # 명령어를 "/수동잔액관리"로 변경하여 더 명확하게 했습니다.
    description="인증고객님의 잔액을 수동으로 추가하거나 차감합니다."
)
async def manual_balance_manage(
    inter: disnake.ApplicationCommandInteraction,
    유저: disnake.Member,
    금액: commands.Range[int, 1, ...], # 금액은 1 이상만 허용
    액션: str = commands.Param(
        choices={"추가": "추가", "차감": "차감"}, # '추가' 또는 '차감'을 선택할 수 있는 드롭다운 메뉴
        description="잔액에 금액을 추가할지, 차감할지 선택하세요."
    )
):
    try:
        # 1. 명령어 사용 권한 확인 (ALLOWED_USER_IDS에 있는지)
        if inter.author.id not in ALLOWED_USER_IDS:
            embed = disnake.Embed(
                title="**접근 거부**",
                description="**이 명령어는 허용된 관리자만 사용할 수 있습니다.**",
                color=disnake.Color.red()
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 2. 관리자 권한 재확인 (check_admin 함수를 사용하여 더 세분화된 권한 체크 가능)
        if not check_admin(inter.author.id):
            embed = disnake.Embed(
                title="**오류**",
                description="**이 명령어를 실행할 권한이 없습니다.**",
                color=disnake.Color.orange()
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 3. 대상 유저의 인증 상태 확인
        user_db_info = get_user_balance_info(유저.id)
        if not user_db_info:
            embed = disnake.Embed(
                title="**오류**",
                description="**해당 고객님은 데이터베이스에 등록되어 있지 않습니다.**",
                color=disnake.Color.orange()
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        
        # DB에서 가져온 유저 정보 사용
        target_user_id, current_balance, total_amount, user_name = user_db_info
        
        # 4. 잔액 업데이트 시도
        success = update_user_balance(유저.id, 금액, 액션)

        if not success:
            # 잔액 업데이트 실패 (주로 차감 시 잔액 부족)
            embed_title = f"**{액션} 실패**"
            embed_description = ""
            if 액션 == "차감" and current_balance < 금액:
                embed_description = f"**고객님의 현재 잔액은 ₩{current_balance:,}원 입니다.**\n**요청하신 차감 금액(₩{금액:,}원)이 잔액보다 많습니다.**"
                embed_color = disnake.Color.red()
            else:
                embed_description = f"**{액션} 처리 중 오류가 발생했습니다. 로그를 확인하거나 관리자에게 문의하세요.**"
                embed_color = disnake.Color.orange()

            embed = disnake.Embed(
                title=embed_title,
                description=embed_description,
                color=embed_color
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        # 5. 잔액 업데이트 성공 후 최신 정보 다시 가져오기
        updated_user_info = get_user_balance_info(유저.id)
        if not updated_user_info: # 업데이트 후 정보 조회 실패 시 (매우 드물게 발생)
            logger.error(f"수동잔액관리: 업데이트 후 유저({유저.id}) 정보 재조회 실패.")
            current_balance = "알 수 없음"
            total_amount = "알 수 없음"
        else:
            _, current_balance, total_amount, _ = updated_user_info

        # 6. 사용자에게 처리 완료 메시지 전송
        embed = disnake.Embed(
            title=f"잔액 {액션} 완료",
            description=(
                f"**대상 고객: {유저.display_name} ({user_name})**\n"
                f"**처리 금액: ₩{금액:,}원 ({액션})**\n"
                f"**현재 잔액: ₩{current_balance:,}원**"
            ),
            color=disnake.Color.green() if 액션 == "추가" else disnake.Color.red()
        )
        embed.set_thumbnail(url=유저.display_avatar.url)
        embed.set_footer(text=f"처리자: {inter.author.display_name} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        await inter.response.send_message(embed=embed)

        # 7. 로그 채널에 알림 전송
        log_channel = inter.guild.get_channel(CHANNEL_CHARGE_LOG)
        if log_channel:
            log_embed = disnake.Embed(
                title=f"잔액 {액션} 로그",
                description=(
                    f"**대상: {유저.display_name} ({user_name})**\n"
                    f"**처리 금액: ₩{금액:,}원 ({액션})**\n"
                    f"**최종 잔액: ₩{current_balance:,}원**"
                ),
                color=disnake.Color.blue()
            )
            log_embed.set_footer(text=f"처리자: {inter.author.display_name} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            await log_channel.send(embed=log_embed)
        else:
            logger.error(f"로그 채널({CHANNEL_CHARGE_LOG})을 찾을 수 없습니다.")

    except Exception as e:
        logger.error(f"[/수동잔액관리] 명령어 처리 중 오류 발생: {e}", exc_info=True)
        embed = disnake.Embed(
            title="**오류**",
            description="**명령어 처리 중 예상치 못한 오류가 발생했습니다. 관리자에게 문의해주세요.**",
            color=disnake.Color.red()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
