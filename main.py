import sqlite3
import json
import os
import logging
from datetime import datetime

# --- 로깅 설정 (이 코드를 사용하는 파일 상단에 한 번만 추가) ---
# 예:
# import logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 상수 정의 (필요에 따라 설정) ---
# DEFAULT_ADMIN_ID: 봇 관리자의 기본 Discord User ID. 이 ID는 admin.db에 없어도 항상 관리자 권한을 가집니다.
DEFAULT_ADMIN_ID = 1402654236570812467 # 실제 관리자 ID로 변경해주세요!

# --- 데이터베이스 파일 경로 ---
ADMIN_DB_PATH = 'DB/admin.db'
VERIFY_USER_DB_PATH = 'DB/verify_user.db' # 유저 잔액 및 인증 정보
VERIFIED_USERS_JSON_PATH = 'DB/verified_users.json' # 유저 인증 및 거래 내역 JSON
HISTORY_DB_PATH = 'DB/history.db' # 모든 거래 내역 기록 (별도 SQLite)

# --- 데이터베이스 초기화 함수 (봇 시작 시 한 번 호출 권장) ---
def init_db():
    try:
        os.makedirs(os.path.dirname(ADMIN_DB_PATH), exist_ok=True) # DB 폴더 생성

        conn_admin = sqlite3.connect(ADMIN_DB_PATH)
        cursor_admin = conn_admin.cursor()
        cursor_admin.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT
            )
        ''')
        conn_admin.commit()
        conn_admin.close()

        conn_verify = sqlite3.connect(VERIFY_USER_DB_PATH)
        cursor_verify = conn_verify.cursor()
        cursor_verify.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                phone TEXT,
                DOB TEXT,
                name TEXT,
                telecom TEXT,
                Total_amount INTEGER DEFAULT 0,
                now_amount INTEGER DEFAULT 0
            )
        ''')
        conn_verify.commit()
        conn_verify.close()

        conn_history = sqlite3.connect(HISTORY_DB_PATH)
        cursor_history = conn_history.cursor()
        cursor_history.execute('''
            CREATE TABLE IF NOT EXISTS transaction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount INTEGER,
                coin_type TEXT,
                address TEXT,
                txid TEXT,
                api_txid TEXT,
                fee INTEGER,
                timestamp TEXT
            )
        ''')
        conn_history.commit()
        conn_history.close()
        
        logger.info("데이터베이스 초기화 완료.")

    except Exception as e:
        logger.error(f"데이터베이스 초기화 오류: {e}", exc_info=True)


# --- 관리자 관련 DB 함수 ---
def check_admin(user_id: int) -> bool:
    try:
        if user_id == DEFAULT_ADMIN_ID:
            return True
        conn = sqlite3.connect(ADMIN_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM admins WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"직원 확인 오류 (user_id: {user_id}): {e}", exc_info=True)
        return False

def add_admin(user_id: int, username: str):
    try:
        conn = sqlite3.connect(ADMIN_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)', (user_id, username))
        conn.commit()
        conn.close()
        logger.info(f"관리자 추가 완료: {username} ({user_id})")
    except Exception as e:
        logger.error(f"직원 추가 오류 (user_id: {user_id}): {e}", exc_info=True)

def remove_admin(user_id: int):
    try:
        if user_id == DEFAULT_ADMIN_ID:
            logger.warning(f"기본 관리자({DEFAULT_ADMIN_ID})는 삭제할 수 없습니다.")
            return False
        conn = sqlite3.connect(ADMIN_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        logger.info(f"관리자 삭제 완료: {user_id}")
        return True
    except Exception as e:
        logger.error(f"직원 삭제 오류 (user_id: {user_id}): {e}", exc_info=True)
        return False


# --- JSON 파일 관련 유틸리티 ---
def _load_json_data() -> dict:
    if os.path.exists(VERIFIED_USERS_JSON_PATH):
        try:
            with open(VERIFIED_USERS_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파일 로드 오류: {VERIFIED_USERS_JSON_PATH} - {e}. 새 파일로 초기화합니다.", exc_info=True)
            return {}
    return {}

def _save_json_data(data: dict):
    try:
        os.makedirs(os.path.dirname(VERIFIED_USERS_JSON_PATH), exist_ok=True)
        temp_file = VERIFIED_USERS_JSON_PATH + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, VERIFIED_USERS_JSON_PATH)
    except Exception as e:
        logger.error(f"JSON 파일 저장 오류: {e}", exc_info=True)


# --- 사용자 인증 및 잔액 관련 DB 함수 ---
def _get_user_balances_from_sqlite(user_id: int) -> tuple[int, int]:
    """SQLite에서 유저의 현재 잔액과 총액만 가져옵니다."""
    conn = None
    try:
        conn = sqlite3.connect(VERIFY_USER_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT Total_amount, now_amount FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return result[0] or 0, result[1] or 0
        return 0, 0
    except sqlite3.Error as e:
        logger.error(f"DB Error (_get_user_balances_from_sqlite) for user_id {user_id}: {e}", exc_info=True)
        return 0, 0
    finally:
        if conn: conn.close()

def save_to_json(user_id: int, phone: str, dob: str, name: str, telecom: str):
    """
    사용자 인증 정보를 JSON에 저장하거나 업데이트합니다.
    기존의 now_amount와 total_amount는 유지합니다.
    """
    data = _load_json_data()
    str_user_id = str(user_id)
    
    # SQLite에서 기존 잔액 정보를 가져옵니다.
    existing_total_amount, existing_now_amount = _get_user_balances_from_sqlite(user_id)

    data[str_user_id] = {
        'user_id': user_id,
        'phone': phone,
        'dob': dob,
        'name': name,
        'telecom': telecom,
        'verified_at': datetime.now().isoformat(),
        'total_amount': data.get(str_user_id, {}).get('total_amount', existing_total_amount),
        'now_amount': data.get(str_user_id, {}).get('now_amount', existing_now_amount),
        'transactions': data.get(str_user_id, {}).get('transactions', [])
    }
    _save_json_data(data)
    logger.info(f"JSON 파일에 유저 정보 저장/업데이트 완료: {user_id}")

def add_verified_user(user_id: int, phone: str, dob: str, name: str, telecom: str):
    """
    새로운 인증 고객을 SQLite와 JSON에 추가/업데이트합니다.
    이미 존재하는 경우 잔액 정보는 SQLite의 현재 값을 유지합니다.
    """
    try:
        conn = sqlite3.connect(VERIFY_USER_DB_PATH)
        cursor = conn.cursor()
        
        # INSERT OR REPLACE 전에 기존 Total_amount, now_amount를 가져옴
        existing_total_amount, existing_now_amount = _get_user_balances_from_sqlite(user_id)
        
        cursor.execute(
            'INSERT OR REPLACE INTO users (user_id, phone, DOB, name, telecom, Total_amount, now_amount) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, phone, dob, name, telecom, existing_total_amount, existing_now_amount)
        )
        conn.commit()
        conn.close()
        
        # JSON 파일에도 추가/업데이트 (이때는 SQLite에서 가져온 현재 잔액으로 업데이트)
        save_to_json(user_id, phone, dob, name, telecom)
        logger.info(f"인증고객 추가 완료 (SQLite & JSON): {user_id}")
    except Exception as e:
        logger.error(f"인증고객 추가 오류 (user_id: {user_id}): {e}", exc_info=True)

def remove_verified_user(user_id: int):
    """
    인증 고객을 SQLite와 JSON에서 삭제합니다.
    """
    try:
        conn = sqlite3.connect(VERIFY_USER_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

        data = _load_json_data()
        if str(user_id) in data:
            del data[str(user_id)]
            _save_json_data(data)
        
        logger.info(f"인증고객 삭제 완료 (SQLite & JSON): {user_id}")
    except Exception as e:
        logger.error(f"인증고객 삭제 오류 (user_id: {user_id}): {e}", exc_info=True)

def add_transaction(user_id: int, transaction_type: str, amount: int, coin_type: str='KRW', address: str=None, txid: str=None, api_txid: str=None, fee: int=0):
    """
    거래 내역을 JSON 파일의 사용자 기록 및 별도의 SQLite 거래 내역 DB에 저장합니다.
    """
    try:
        timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        transaction = {
            'type': transaction_type,
            'amount': amount,
            'coin_type': coin_type,
            'address': address or '',
            'txid': txid or '',
            'api_txid': api_txid or '',
            'fee': fee,
            'timestamp': timestamp_str
        }
        
        # 1. JSON 파일의 사용자 거래 내역에 추가
        json_data = _load_json_data()
        str_user_id = str(user_id)
        
        if str_user_id not in json_data:
            logger.warning(f"JSON에 유저 {user_id} 정보가 없어 기본 구조 생성 후 거래 추가.")
            user_info_from_sqlite = get_user_balance_info(user_id) # SQLite에서 기본 정보 가져옴
            json_data[str_user_id] = {
                'user_id': user_id,
                'phone': user_info_from_sqlite[1] if user_info_from_sqlite else '',
                'dob': user_info_from_sqlite[2] if user_info_from_sqlite else '',
                'name': user_info_from_sqlite[3] if user_info_from_sqlite else '',
                'telecom': user_info_from_sqlite[4] if user_info_from_sqlite else '',
                'total_amount': user_info_from_sqlite[5] if user_info_from_sqlite else 0,
                'now_amount': user_info_from_sqlite[6] if user_info_from_sqlite else 0,
                'transactions': []
            }
        
        if 'transactions' not in json_data[str_user_id]:
            json_data[str_user_id]['transactions'] = []
            
        json_data[str_user_id]['transactions'].append(transaction)
        
        if len(json_data[str_user_id]['transactions']) > 100: # 최대 100개 유지
            json_data[str_user_id]['transactions'] = json_data[str_user_id]['transactions'][-100:]
        
        _save_json_data(json_data)
        logger.info(f"JSON 거래내역 추가 완료: {user_id} - {transaction_type} {amount}")

        # 2. SQLite history.db에 모든 거래 내역 기록
        conn_history = sqlite3.connect(HISTORY_DB_PATH)
        cursor_history = conn_history.cursor()
        cursor_history.execute(
            'INSERT INTO transaction_history (user_id, type, amount, coin_type, address, txid, api_txid, fee, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (user_id, transaction_type, amount, coin_type, address, txid, api_txid, fee, timestamp_str)
        )
        conn_history.commit()
        conn_history.close()
        logger.info(f"SQLite transaction_history DB에 기록 완료: {user_id} - {transaction_type} {amount}")

    except Exception as e:
        logger.error(f"거래내역 저장 오류 (user_id: {user_id}): {e}", exc_info=True)


def get_transaction_history(user_id: int, limit: int=100) -> list:
    """
    사용자의 거래 내역을 JSON 파일에서 최신순으로 조회합니다.
    """
    try:
        json_data = _load_json_data()
        user_data = json_data.get(str(user_id), {})
        transactions = user_data.get('transactions', [])
        transactions = sorted(transactions, key=lambda x: x.get('timestamp', ''), reverse=True)
        return transactions[:limit]
    except Exception as e:
        logger.error(f"거래내역 조회 오류 (user_id: {user_id}): {e}", exc_info=True)
        return []

def update_balance_in_json(user_id: int, new_total_amount: int, new_now_amount: int):
    """
    JSON 파일 내 특정 사용자의 now_amount 및 Total_amount만 업데이트합니다.
    """
    data = _load_json_data()
    str_user_id = str(user_id)
    if str_user_id in data:
        data[str_user_id]['total_amount'] = new_total_amount
        data[str_user_id]['now_amount'] = new_now_amount
        _save_json_data(data)
        logger.info(f"JSON 잔액 업데이트 완료: {user_id}, 현재: {new_now_amount}, 총액: {new_total_amount}")
    else:
        logger.warning(f"JSON에 없는 유저의 잔액 업데이트 시도: {user_id}")

def get_user_balance_info(user_id: int) -> tuple | None:
    """
    유저 잔액 및 인증 정보를 SQLite에서 가져옵니다.
    반환 형식: (user_id, phone, DOB, name, telecom, Total_amount, now_amount)
    """
    conn = None
    try:
        conn = sqlite3.connect(VERIFY_USER_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT user_id, phone, DOB, name, telecom, Total_amount, now_amount '
            'FROM users WHERE user_id = ?', (user_id,)
        )
        user_info = cursor.fetchone()
        conn.close()
        
        if user_info:
            return user_info
        logger.info(f"유저 정보 찾을 수 없음 (SQLite): {user_id}")
        return None
    except sqlite3.Error as e:
        logger.error(f"DB Error (get_user_balance_info) for user_id {user_id}: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()


def add_balance(user_id: int, amount: int, transaction_type: str="충전"):
    """
    사용자 잔액을 SQLite와 JSON 모두에 추가하고 거래 내역을 기록합니다.
    """
    conn = None
    try:
        conn = sqlite3.connect(VERIFY_USER_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT Total_amount, now_amount FROM users WHERE user_id = ?', (user_id,))
        current = cursor.fetchone()
        
        if current:
            new_balance = current[1] + amount
            new_total = current[0] + amount
            cursor.execute('UPDATE users SET Total_amount = ?, now_amount = ? WHERE user_id = ?', 
                          (new_total, new_balance, user_id))
            
            # JSON 파일도 업데이트
            update_balance_in_json(user_id, new_total, new_balance)
        else:
            # 유저 정보가 없으면 삽입 (기본값으로 0, 0을 사용하고 amount만큼 더함)
            # 이 경우는 add_verified_user로 먼저 유저를 생성하는 것이 좋습니다.
            new_balance = amount
            new_total = amount
            cursor.execute('INSERT INTO users (user_id, Total_amount, now_amount) VALUES (?, ?, ?)', 
                          (user_id, new_total, new_balance))
            
            # JSON 파일도 업데이트
            update_balance_in_json(user_id, new_total, new_balance) # JSON에 없으면 이 함수는 경고만 띄웁니다.
        
        conn.commit()
        conn.close()

        # 거래내역 저장 (SQLite history.db와 JSON transactions 모두)
        add_transaction(user_id=user_id, transaction_type=transaction_type, amount=amount, coin_type="KRW")
        
        logger.info(f"잔액 추가 완료 (user_id: {user_id}, 금액: {amount})")
    except Exception as e:
        logger.error(f"잔액 추가 오류 (user_id: {user_id}, 금액: {amount}): {e}", exc_info=True)
    finally:
        if conn: conn.close()

def subtract_balance(user_id: int, amount: int) -> bool:
    """
    사용자 잔액을 SQLite와 JSON 모두에서 차감하고 거래 내역을 기록합니다.
    잔액 부족 시 False 반환.
    """
    conn = None
    try:
        conn = sqlite3.connect(VERIFY_USER_DB_PATH)
        cursor = conn.cursor()
        
        # 특별 케이스: user_id가 None이면 전역 차감 로직 (이 경우는 /수동잔액관리에서는 사용되지 않음)
        if user_id is None: 
            logger.warning("subtract_balance: user_id가 None인 전역 차감 로직은 현재 명령어에서 사용되지 않습니다.")
            # 기존 로직을 따라가나, JSON 동기화 로직은 추가하지 않습니다.
            cursor.execute('UPDATE users SET now_amount = now_amount - ? WHERE now_amount >= ?', 
                          (amount, amount))
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            if affected_rows == 0:
                logger.warning("전역 차감 실패: 잔액 부족")
                return False
            return True # 전역 차감은 거래내역 기록 로직이 명확치 않아 스킵
        
        # 특정 사용자 차감
        cursor.execute('SELECT Total_amount, now_amount FROM users WHERE user_id = ?', (user_id,))
        current = cursor.fetchone()
        
        if current:
            current_total_amount, current_now_amount = current[0] or 0, current[1] or 0
            if current_now_amount >= amount:
                new_balance = current_now_amount - amount
                # 차감은 Total_amount (누적 구매액)에 영향을 주지 않음
                new_total_amount = current_total_amount 
                
                cursor.execute('UPDATE users SET now_amount = ? WHERE user_id = ?', 
                              (new_balance, user_id))
                conn.commit()
                
                # JSON 파일도 업데이트
                update_balance_in_json(user_id, new_total_amount, new_balance)

                # 거래내역 저장 (SQLite history.db와 JSON transactions 모두)
                add_transaction(user_id=user_id, transaction_type="잔액차감", amount=amount, coin_type="KRW")
                
                conn.close()
                logger.info(f"잔액 차감 완료 (user_id: {user_id}, 금액: {amount})")
                return True
            else:
                logger.warning(f"사용자 {user_id} 잔액 부족 (현재: {current_now_amount}, 요청: {amount})")
                conn.close()
                return False
        else:
            logger.warning(f"사용자 {user_id}를 데이터베이스에서 찾을 수 없습니다.")
            conn.close()
            return False
        
    except Exception as e:
        logger.error(f"잔액 차감 오류 (user_id: {user_id}, 금액: {amount}): {e}", exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()
