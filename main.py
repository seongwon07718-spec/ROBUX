def check_admin(user_id):
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

def add_admin(user_id, username):
    try:
        conn = sqlite3.connect('DB/admin.db')
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)', (user_id, username))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"직원 추가 오류: {e}")

def remove_admin(user_id):
    try:
        conn = sqlite3.connect('DB/admin.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"직원 삭제 오류: {e}")

def save_to_json(user_id, phone, dob, name, telecom):
    try:
        json_file = 'DB/verified_users.json'
        
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
        
        data[str(user_id)] = {
            'user_id': user_id,
            'phone': phone,
            'dob': dob,
            'name': name,
            'telecom': telecom,
            'verified_at': datetime.now().isoformat(),
            'total_amount': 0,
            'now_amount': 0
        }
        
        temp_file = json_file + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        os.replace(temp_file, json_file)
        
    except Exception as e:
        logger.error(f"JSON 저장 오류: {e}")

def add_verified_user(user_id, phone, dob, name, telecom):
    try:
        conn = sqlite3.connect('DB/verify_user.db')
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO users (user_id, phone, DOB, name, telecom, Total_amount, now_amount) VALUES (?, ?, ?, ?, ?, 0, 0)', 
                       (user_id, phone, dob, name, telecom))
        conn.commit()
        conn.close()
        
        # JSON 파일에도 저장
        save_to_json(user_id, phone, dob, name, telecom)
        
    except Exception as e:
        logger.error(f"인증고객 추가 오류: {e}")

def remove_verified_user(user_id):
    try:
        conn = sqlite3.connect('DB/verify_user.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"인증고객 삭제 오류: {e}")

def add_transaction(user_id, transaction_type, amount, coin_type=None, address=None, txid=None, api_txid=None, fee=0):
    """거래내역을 JSON 파일에 저장"""
    try:
        json_file = 'DB/verified_users.json'
        
        # 거래 데이터 생성
        transaction = {
            'type': transaction_type,
            'amount': amount,
            'coin_type': coin_type or 'KRW',
            'address': address or '',
            'txid': txid or '',
            'api_txid': api_txid or '',
            'fee': fee,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
        
        # 사용자 데이터 초기화
        if str(user_id) not in data:
            data[str(user_id)] = {
                'total_amount': 0,
                'now_amount': 0,
                'transactions': []
            }
        
        # 거래내역 추가
        if 'transactions' not in data[str(user_id)]:
            data[str(user_id)]['transactions'] = []
        
        data[str(user_id)]['transactions'].append(transaction)
        
        # 최대 100개까지만 저장 (메모리 절약)
        if len(data[str(user_id)]['transactions']) > 100:
            data[str(user_id)]['transactions'] = data[str(user_id)]['transactions'][-100:]
        
        # 파일 저장
        temp_file = json_file + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        os.replace(temp_file, json_file)
        logger.info(f"거래내역 저장 완료: {user_id} - {transaction_type} {amount}")
        
    except Exception as e:
        logger.error(f"거래내역 저장 오류: {e}")

def get_transaction_history(user_id, limit=100):
    """사용자의 거래내역을 조회"""
    try:
        json_file = 'DB/verified_users.json'
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            user_data = data.get(str(user_id), {})
            transactions = user_data.get('transactions', [])
            # 최신순 정렬
            transactions = sorted(transactions, key=lambda x: x.get('timestamp', ''), reverse=True)
            return transactions[:limit] if transactions else []
        else:
            return []
    except Exception as e:
        logger.error(f"거래내역 조회 오류: {e}")
        return []

def update_json_balance(user_id, total_amount, now_amount):
    try:
        json_file = 'DB/verified_users.json'
        
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if str(user_id) in data:
                data[str(user_id)]['total_amount'] = total_amount
                data[str(user_id)]['now_amount'] = now_amount
                
                temp_file = json_file + '.tmp'
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                os.replace(temp_file, json_file)
                
    except Exception as e:
        logger.error(f"JSON 잔액 업데이트 오류: {e}")

def add_balance(user_id, amount, transaction_type="충전"):
    try:
        conn = sqlite3.connect('DB/verify_user.db')
        cursor = conn.cursor()
        cursor.execute('SELECT Total_amount, now_amount FROM users WHERE user_id = ?', (user_id,))
        current = cursor.fetchone()
        
        if current:
            new_balance = current[1] + amount
            new_total = current[0] + amount
            cursor.execute('UPDATE users SET Total_amount = ?, now_amount = ? WHERE user_id = ?', 
                          (new_total, new_balance, user_id))
            
            # JSON 파일도 업데이트
            update_json_balance(user_id, new_total, new_balance)
        else:
            cursor.execute('INSERT INTO users (user_id, Total_amount, now_amount) VALUES (?, ?, ?)', 
                          (user_id, amount, amount))
            
            # JSON 파일도 업데이트
            update_json_balance(user_id, amount, amount)
        
        # 거래내역 저장
        add_transaction(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            coin_type="KRW"
        )
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"잔액 추가 오류: {e}")

def subtract_balance(user_id, amount):
    try:
        conn = sqlite3.connect('DB/verify_user.db')
        cursor = conn.cursor()
        
        if user_id is None:
            # 전역 차감 (송금 수수료)
            cursor.execute('UPDATE users SET now_amount = now_amount - ? WHERE now_amount >= ?', 
                          (amount, amount))
            affected_rows = cursor.rowcount
            if affected_rows == 0:
                logger.warning("전역 차감 실패: 잔액 부족")
                return False
        else:
            # 특정 사용자 차감
            cursor.execute('SELECT now_amount FROM users WHERE user_id = ?', (user_id,))
            current = cursor.fetchone()
            
            if current and current[0] >= amount:
                cursor.execute('UPDATE users SET now_amount = now_amount - ? WHERE user_id = ?', 
                              (amount, user_id))
            else:
                logger.warning(f"사용자 {user_id} 잔액 부족")
                return False
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"잔액 차감 오류: {e}")
        return False
