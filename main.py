import sqlite3
import json
import os

DB_PATH = 'DB/buy_panel.db'
OUT_JSON = 'db.json'

def fetch_all():
    if not os.path.exists(DB_PATH):
        print("DB 파일이 없습니다. init_db.py를 먼저 실행하세요.")
        return {}

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    data = {}

    # bank_accounts
    c.execute('SELECT id, user_id, bank_name, account_number, created_at FROM bank_accounts')
    rows = c.fetchall()
    data['bank_accounts'] = [
        {'id': r[0], 'user_id': r[1], 'bank_name': r[2], 'account_number': r[3], 'created_at': r[4]}
        for r in rows
    ]

    # coin_addresses
    c.execute('SELECT id, user_id, coin, address, created_at FROM coin_addresses')
    rows = c.fetchall()
    data['coin_addresses'] = [
        {'id': r[0], 'user_id': r[1], 'coin': r[2], 'address': r[3], 'created_at': r[4]}
        for r in rows
    ]

    # purchases
    c.execute('SELECT id, user_id, bank_id, coin, address, txid, amount, currency, status, created_at FROM purchases')
    rows = c.fetchall()
    data['purchases'] = [
        {
            'id': r[0], 'user_id': r[1], 'bank_id': r[2], 'coin': r[3], 'address': r[4],
            'txid': r[5], 'amount': r[6], 'currency': r[7], 'status': r[8], 'created_at': r[9]
        }
        for r in rows
    ]

    conn.close()
    return data

def write_json(out):
    data = fetch_all()
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"DB 덤프 완료: {out}")

if __name__ == "__main__":
    write_json(OUT_JSON)
