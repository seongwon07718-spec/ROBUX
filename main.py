import sqlite3
import json
import os
import logging
from datetime import datetime

# 로깅 설정 (파일 상단에서 한 번만 호출)
logger = logging.getLogger(__name__)
# 필요하면 아래 기본 설정 추가:
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 상수
DEFAULT_ADMIN_ID = 1402654236570812467
ADMIN_DB_PATH = 'DB/admin.db'
VERIFY_USER_DB_PATH = 'DB/verify_user.db'
VERIFIED_USERS_JSON_PATH = 'DB/verified_users.json'
HISTORY_DB_PATH = 'DB/history.db'

def _load_json_data() -> dict:
    if os.path.exists(VERIFIED_USERS_JSON_PATH):
        try:
            with open(VERIFIED_USERS_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 로드 오류: {e}", exc_info=True)
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
        logger.error(f"JSON 저장 오류: {e}", exc_info=True)

def check_admin(user_id: int) -> bool:
    if user_id == DEFAULT_ADMIN_ID:
        return True
    try:
        conn = sqlite3.connect(ADMIN_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM admins WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"직원 확인 오류: {e}", exc_info=True)
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
        logger.error(f"직원 추가 오류: {e}", exc_info=True)

def remove_admin(user_id: int) -> bool:
    if user_id == DEFAULT_ADMIN_ID:
        logger.warning(f"기본 관리자({DEFAULT_ADMIN_ID})는 삭제할 수 없습니다.")
        return False
    try:
        conn = sqlite3.connect(ADMIN_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        logger.info(f"관리자 삭제 완료: {user_id}")
        return True
    except Exception as e:
        logger.error(f"직원 삭제 오류: {e}", exc_info=True)
        return False

def save_to_json(user_id: int, phone: str, dob: str, name: str, telecom: str):
    try:
        data = _load_json_data()
        str_uid = str(user_id)
        prev = data.get(str_uid, {})
        data[str_uid] = {
            'user_id': user_id,
            'phone': phone,
            'dob': dob,
            'name': name,
            'telecom': telecom,
            'verified_at': datetime.now().isoformat(),
            'total_amount': prev.get('total_amount', 0),
            'now_amount': prev.get('now_amount', 0),
            'transactions': prev.get('transactions', []),
        }
        _save_json_data(data)
        logger.info(f"JSON 유저 정보 저장/업데이트 완료: {user_id}")
    except Exception as e:
        logger.error(f"JSON 저장 오류: {e}", exc_info=True)

def add_verified_user(user_id: int, phone: str, dob: str, name: str, telecom: str):
    try:
        conn = sqlite3.connect(VERIFY_USER_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT Total_amount, now_amount FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        total, now = row if row else (0,0)
        cursor.execute('INSERT OR REPLACE INTO users (user_id, phone, DOB, name, telecom, Total_amount, now_amount) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                      (user_id, phone, dob, name, telecom, total, now))
        conn.commit()
        conn.close()
        save_to_json(user_id, phone, dob, name, telecom)
        logger.info(f"인증고객 추가 완료: {user_id}")
    except Exception as e:
        logger.error(f"인증고객 추가 오류: {e}", exc_info=True)

def remove_verified_user(user_id: int):
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
        logger.info(f"인증고객 삭제 완료: {user_id}")
    except Exception as e:
        logger.error(f"인증고객 삭제 오류: {e}", exc_info=True)

def add_transaction(user_id: int, transaction_type: str, amount: int, coin_type: str='KRW', address: str=None, txid: str=None, api_txid: str=None, fee: int=0):
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        trans = {
            'type': transaction_type,
            'amount': amount,
            'coin_type': coin_type,
            'address': address or '',
            'txid': txid or '',
            'api_txid': api_txid or '',
            'fee': fee,
            'timestamp': timestamp
        }
        data = _load_json_data()
        str_uid = str(user_id)
        if str_uid not in data:
            data[str_uid] = {
                'total_amount': 0,
                'now_amount': 0,
                'transactions': []
            }
        data[str_uid].setdefault('transactions', []).append(trans)
        if len(data[str_uid]['transactions']) > 100:
            data[str_uid]['transactions'] = data[str_uid]['transactions'][-100:]
        _save_json_data(data)
        logger.info(f"JSON 거래내역 저장: {user_id} {transaction_type} {amount}")
        conn_history = sqlite3.connect(HISTORY_DB_PATH)
        cursor_history = conn_history.cursor()
        cursor_history.execute('CREATE TABLE IF NOT EXISTS transaction_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, amount INTEGER, coin_type TEXT, address TEXT, txid TEXT, api_txid TEXT, fee INTEGER, timestamp TEXT)')
        cursor_history.execute('INSERT INTO transaction_history (user_id, type, amount, coin_type, address, txid, api_txid, fee, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (user_id, transaction_type, amount, coin_type, address, txid, api_txid, fee, timestamp))
        conn_history.commit()
        conn_history.close()
        logger.info(f"SQLite 거래내역 저장: {user_id} {transaction_type} {amount}")
    except Exception as e:
        logger.error(f"거래내역 저장 오류: {e}", exc_info=True)

def get_transaction_history(user_id: int, limit: int=100):
    try:
        data = _load_json_data()
        transactions = data.get(str(user_id), {}).get('transactions', [])
        return sorted(transactions, key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]
    except Exception as e:
        logger.error(f"거래내역 조회 오류: {e}", exc_info=True)
        return []

def update_balance_in_json(user_id: int, total_amount: int, now_amount: int):
    try:
        data = _load_json_data()
        if str(user_id) in data:
            data[str(user_id)]['total_amount'] = total_amount
            data[str(user_id)]['now_amount'] = now_amount
            _save_json_data(data)
            logger.info(f"JSON 잔액 업데이트: {user_id}")
        else:
            logger.warning(f"JSON에 없는 유저 잔액 업데이트 시도: {user_id}")
    except Exception as e:
        logger.error(f"JSON 잔액 업데이트 오류: {e}", exc_info=True)

def get_user_balance_info(user_id: int):
    conn = None
    try:
        conn = sqlite3.connect(VERIFY_USER_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, phone, DOB, name, telecom, Total_amount, now_amount FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"DB 조회 오류: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()

def add_balance(user_id: int, amount: int, transaction_type: str="충전"):
    conn = None
    try:
        conn = sqlite3.connect(VERIFY_USER_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT Total_amount, now_amount FROM users WHERE user_id = ?', (user_id,))
        current = cursor.fetchone()
        if current:
            new_total = current[0] + amount
            new_now = current[1] + amount
            cursor.execute('UPDATE users SET Total_amount = ?, now_amount = ? WHERE user_id = ?', (new_total, new_now, user_id))
            update_balance_in_json(user_id, new_total, new_now)
        else:
            cursor.execute('INSERT INTO users (user_id, Total_amount, now_amount) VALUES (?, ?, ?)', (user_id, amount, amount))
            update_balance_in_json(user_id, amount, amount)
        add_transaction(user_id, transaction_type, amount, "KRW")
        conn.commit()
    except Exception as e:
        logger.error(f"잔액 추가 오류: {e}", exc_info=True)
    finally:
        if conn: conn.close()

def subtract_balance(user_id: int, amount: int) -> bool:
    conn = None
    try:
        conn = sqlite3.connect(VERIFY_USER_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT now_amount FROM users WHERE user_id = ?', (user_id,))
        current = cursor.fetchone()
        if current and current[0] >= amount:
            new_now = current[0] - amount
            cursor.execute('UPDATE users SET now_amount = ? WHERE user_id = ?', (new_now, user_id))
            update_balance_in_json(user_id, None, new_now)
            add_transaction(user_id, "잔액차감", amount, "KRW")
            conn.commit()
            return True
        else:
            logger.warning(f"{user_id} 잔액 부족")
            return False
    except Exception as e:
        logger.error(f"잔액 차감 오류: {e}", exc_info=True)
        return False
    finally:
        if conn: conn.close()
