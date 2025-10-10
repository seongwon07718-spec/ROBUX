import discord
import sqlite3
import asyncio
import datetime
import threading
import re
from flask import Flask, request, jsonify
from discord import PartialEmoji, ui
from discord.ext import commands

# === 디스코드 봇 설정 ===
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)

# === DB 연결 및 안전 관리 ===
db_lock = threading.RLock()

def get_connection():
    conn = sqlite3.connect(
        "database.db",
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    return conn

# === DB 작업 함수 예시 ===
def add_or_update_user(user_id, balance, total_amount, transaction_count):
    with db_lock:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO users (user_id, balance, total_amount, transaction_count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                balance=excluded.balance,
                total_amount=excluded.total_amount,
                transaction_count=excluded.transaction_count
        ''', (user_id, balance, total_amount, transaction_count))
        conn.commit()
        conn.close()

def get_user_info(user_id):
    with db_lock:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        conn.close()
        return result

def create_charge_request(user_id, depositor_name, amount):
    with db_lock:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO charge_requests (user_id, depositor_name, amount, status, request_time)
            VALUES (?, ?, ?, '대기', ?)
        ''', (user_id, depositor_name, amount, datetime.datetime.now(datetime.timezone.utc).isoformat()))
        conn.commit()
        conn.close()

def get_payment_methods(user_id):
    with db_lock:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT account_transfer, coin_payment, mun_sang_payment FROM payment_methods WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        conn.close()
        if result:
            return (result["account_transfer"], result["coin_payment"], result["mun_sang_payment"])
        return ("미지원", "미지원", "미지원")

def get_bank_account(user_id):
    with db_lock:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT bank_name, account_holder, account_number FROM bank_accounts WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        conn.close()
        if result:
            return (result["bank_name"], result["account_holder"], result["account_number"])
        return (None, None, None)

def get_user_ban(user_id):
    with db_lock:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT banned FROM user_bans WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        conn.close()
        return result["banned"] if result else "x"

async def check_vending_access(user_id):
    return get_user_ban(user_id) != "o"

# === 자동 충전 처리 태스크 ===
async def auto_process_charge_requests():
    while True:
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            with db_lock:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT id, user_id, amount, depositor_name, request_time FROM charge_requests WHERE status = '대기'")
                requests = cur.fetchall()
                conn.close()

            for req in requests:
                req_id = req['id']
                user_id = req['user_id']
                amount = req['amount']
                depositor_name = req['depositor_name']
                request_time = req['request_time']
                
                if isinstance(request_time, str):
                    request_time = datetime.datetime.fromisoformat(request_time.replace('Z', '+00:00'))

                elapsed_seconds = (now - request_time).total_seconds()

                try:
                    user = await bot.fetch_user(int(user_id))
                except:
                    user = None

                if elapsed_seconds > 300:
                    with db_lock:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("UPDATE charge_requests SET status='만료' WHERE id=?", (req_id,))
                        conn.commit()
                        conn.close()
                    if user:
                        try:
                            await user.send(view=ChargeExpiredView(depositor_name, amount))
                        except:
                            pass
                    continue

                user_info = get_user_info(user_id)
                old_balance = user_info['balance'] if user_info else 0
                new_balance = old_balance + amount
                total_amount = (user_info['total_amount'] if user_info else 0) + amount
                transaction_count = (user_info['transaction_count'] if user_info else 0) + 1

                add_or_update_user(user_id, new_balance, total_amount, transaction_count)

                with db_lock:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE charge_requests SET status='완료' WHERE id=?", (req_id,))
                    conn.commit()
                    conn.close()

                if user:
                    try:
                        await user.send(view=ChargeCompleteView(old_balance, new_balance))
                    except:
                        pass

        except Exception as e:
            print(f"자동충전 처리 오류: {e}")

        await asyncio.sleep(30)

# === UI 뷰들 작성 (컨테이너 박스 형식) ===
class ChargeCompleteView(ui.LayoutView):
    def __init__(self, old_balance, new_balance):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay("✅ **정상적으로 충전이 완료되었습니다**"))
        c.add_item(ui.TextDisplay(f"**원래 금액** = `{old_balance:,}원`"))
        c.add_item(ui.TextDisplay(f"**충전 후 금액** = `{new_balance:,}원`"))
        c.add_item(ui.TextDisplay(""))
        c.add_item(ui.TextDisplay("오늘도 즐거운 하루 되시길 바랍니다"))
        self.add_item(c)

class ChargeExpiredView(ui.LayoutView):
    def __init__(self, depositor_name, amount):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay("⚠️ **충전 요청 만료 안내**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"입금자명: __{depositor_name}__"))
        c.add_item(ui.TextDisplay(f"금액: __{amount:,}원__"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("5분 이내 입금 확인이 안되어 충전 요청이 만료되었습니다. 다시 신청해주세요."))
        self.add_item(c)

# ... 나머지 UI 및 명령어, 모달 등 기존 코드 동일하게 유지 ...

# === Flask API 서버 구현 ===
flask_app = Flask(__name__)

@flask_app.route("/api/charge", methods=["POST"])
def charge_api():
    data = request.get_json()
    sms_text = data.get("message", "")

    pattern = r"([가-힣]{2,4})(?:님|이)?\s*(\d[\d,]*)원"
    match = re.search(pattern, sms_text)

    if not match:
        return jsonify({"status": "error", "message": "입금 정보를 찾을 수 없습니다"}), 400

    depositor_name = match.group(1).strip()
    amount_str = match.group(2).replace(",", "")
    try:
        amount = int(amount_str)
        if amount <= 0:
            raise ValueError()
    except:
        return jsonify({"status": "error", "message": "유효하지 않은 금액"}), 400

    with db_lock:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM bank_accounts WHERE account_holder = ?", (depositor_name,))
        row = cur.fetchone()
        conn.close()

    if not row:
        return jsonify({"status": "error", "message": f"입금자 '{depositor_name}'과 연결된 계정을 찾을 수 없습니다."}), 404

    discord_user_id = row["user_id"]
    create_charge_request(discord_user_id, depositor_name, amount)

    return jsonify({"status": "success", "message": "충전 요청 등록 완료"}), 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=5000)

def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    bot.run("YOUR_BOT_TOKEN")  # 토큰 교체 필수

if __name__ == "__main__":
    main()
