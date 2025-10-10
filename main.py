import discord
import sqlite3
import asyncio
import datetime
import threading
import re
from flask import Flask, request, jsonify # Flask API 서버를 위한 임포트
from discord import PartialEmoji, ui
from discord.ext import commands

# === 디스코드 봇 설정 ===
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)

# === DB 설정 및 초기화 ===
# DB 연결 (스레드 안전성 확보)
conn = sqlite3.connect(
    "database.db",
    detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    check_same_thread=False, # asyncio와 SQLite 사용 시 필수적
)
conn.row_factory = sqlite3.Row # 결과를 딕셔너리처럼 접근 가능하게 설정
cur = conn.cursor()

# DB 접근 시 스레드 간 충돌 방지를 위한 락 (Lock)
db_lock = threading.RLock()

def initialize_database():
    with db_lock: # DB 작업은 락으로 보호
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                total_amount INTEGER DEFAULT 0,
                transaction_count INTEGER DEFAULT 0
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_bans (
                user_id TEXT PRIMARY KEY,
                banned TEXT CHECK(banned IN ('o', 'x')) DEFAULT 'x'
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS payment_methods (
                user_id TEXT PRIMARY KEY,
                account_transfer TEXT CHECK(account_transfer IN ('지원', '미지원')) DEFAULT '미지원',
                coin_payment TEXT CHECK(coin_payment IN ('지원', '미지원')) DEFAULT '미지원',
                mun_sang_payment TEXT CHECK(mun_sang_payment IN ('지원', '미지원')) DEFAULT '미지원'
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS bank_accounts (
                user_id TEXT PRIMARY KEY,
                bank_name TEXT,
                account_holder TEXT,
                account_number TEXT
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS charge_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                depositor_name TEXT NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT DEFAULT '대기',
                request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

initialize_database()

# === DB 함수 정의 (모든 DB 접근은 락으로 보호) ===

def add_or_update_user(user_id, balance, total_amount, transaction_count):
    with db_lock:
        cur.execute('''
            INSERT INTO users (user_id, balance, total_amount, transaction_count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                balance=excluded.balance,
                total_amount=excluded.total_amount,
                transaction_count=excluded.transaction_count
        ''', (user_id, balance, total_amount, transaction_count))
        conn.commit()

def set_user_ban(user_id, status):
    with db_lock:
        cur.execute('''
            INSERT INTO user_bans (user_id, banned)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET banned=excluded.banned
        ''', (user_id, status))
        conn.commit()

def get_user_ban(user_id):
    with db_lock:
        cur.execute("SELECT banned FROM user_bans WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        return result["banned"] if result else "x"

def get_user_info(user_id):
    with db_lock:
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cur.fetchone()

def set_payment_methods(user_id, account_transfer, coin_payment, mun_sang):
    with db_lock:
        cur.execute('''
            INSERT INTO payment_methods (user_id, account_transfer, coin_payment, mun_sang_payment)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                account_transfer=excluded.account_transfer,
                coin_payment=excluded.coin_payment,
                mun_sang_payment=excluded.mun_sang_payment
        ''', (user_id, account_transfer, coin_payment, mun_sang))
        conn.commit()

def get_payment_methods(user_id):
    with db_lock:
        cur.execute(
            "SELECT account_transfer, coin_payment, mun_sang_payment FROM payment_methods WHERE user_id = ?",
            (user_id,),
        )
        result = cur.fetchone()
        if result:
            return (result["account_transfer"], result["coin_payment"], result["mun_sang_payment"])
        return ("미지원", "미지원", "미지원")

def set_bank_account(user_id, bank_name, account_holder, account_number):
    with db_lock:
        cur.execute('''
            INSERT INTO bank_accounts (user_id, bank_name, account_holder, account_number)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                bank_name=excluded.bank_name,
                account_holder=excluded.account_holder,
                account_number=excluded.account_number
        ''', (user_id, bank_name, account_holder, account_number))
        conn.commit()

def get_bank_account(user_id):
    with db_lock:
        cur.execute("SELECT bank_name, account_holder, account_number FROM bank_accounts WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        if result:
            return (result["bank_name"], result["account_holder"], result["account_number"])
        return (None, None, None)

def create_charge_request(user_id, depositor_name, amount):
    with db_lock:
        cur.execute('''
            INSERT INTO charge_requests (user_id, depositor_name, amount, status, request_time)
            VALUES (?, ?, ?, '대기', ?)
        ''', (user_id, depositor_name, amount, datetime.datetime.utcnow().isoformat())) # UTC 시간 저장
        conn.commit()

async def check_vending_access(user_id):
    return get_user_ban(user_id) != "o"
# === 자동 충전 처리 태스크 (5분 제한 및 컨테이너 메시지 포함) ===
async def auto_process_charge_requests():
    while True:
        try:
            now = datetime.datetime.now(datetime.timezone.utc)  # UTC 시간으로 통일
            with db_lock:
                cur.execute(
                    "SELECT * FROM charge_requests WHERE status = '대기'"
                )
                requests = cur.fetchall()

            for req in requests:
                req_id = req["id"]
                user_id = req["user_id"]
                amount = req["amount"]
                depositor_name = req["depositor_name"]
                # SQLite가 저장한 timestamp가 UTC 가정
                request_time = req["request_time"]
                if isinstance(request_time, str):  # 문자열이면 datetime으로 변환
                    request_time = datetime.datetime.fromisoformat(request_time.replace('Z', '+00:00'))

                elapsed = (now - request_time).total_seconds()

                # 사용자 객체 가져오기 (알림용)
                try:
                    user = await bot.fetch_user(int(user_id))
                except Exception:
                    user = None

                if elapsed > 300:  # 5분(300초) 초과 시 만료
                    with db_lock:
                        cur.execute("UPDATE charge_requests SET status='만료' WHERE id=?", (req_id,))
                        conn.commit()
                    if user:
                        try:
                            view = ChargeExpiredView(depositor_name, amount)
                            await user.send(view=view)
                            print(f"충전 요청 {req_id} 만료 처리 및 알림 전송 (5분 초과)")
                        except Exception as e:
                            print(f"만료 알림 전송 실패 user_id={user_id}: {e}")
                    continue  # 다음 요청으로 넘어감

                # 5분 이내의 요청만 처리 (실제 충전)
                user_info = get_user_info(user_id)  # 최신 유저 정보 가져오기 (락 이미 걸림)
                
                old_balance = user_info["balance"] if user_info else 0
                new_balance = old_balance + amount
                total_amount = (user_info["total_amount"] if user_info else 0) + amount
                transaction_count = (user_info["transaction_count"] if user_info else 0) + 1

                add_or_update_user(user_id, new_balance, total_amount, transaction_count)  # 사용자 정보 업데이트

                with db_lock:
                    cur.execute("UPDATE charge_requests SET status='완료' WHERE id=?", (req_id,))
                    conn.commit()
                
                print(f"자동충전 완료: 사용자 {user_id}, 금액 {amount}원")
                
                # 충전 완료 알림 전송 (컨테이너 뷰 사용)
                if user:
                    try:
                        view = ChargeCompleteView(old_balance, new_balance)
                        await user.send(view=view)
                    except Exception as e:
                        print(f"충전 완료 알림 전송 실패 user_id={user_id}: {e}")
                    
        except Exception as e:
            print(f"자동충전 처리 태스크 전체 오류: {e}")
        
        await asyncio.sleep(30)  # 30초마다 확인

# === UI 뷰 클래스 정의 ===

# 충전 완료 컨테이너 뷰
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

# 충전 만료 컨테이너 뷰
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

# 자판기 밴 상태 안내 뷰
class VendingBanView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay("**자판기 이용 관련**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("현재 고객님은 자판기 이용이 __불가능__합니다"))
        c.add_item(ui.TextDisplay("자세한 이유를 알고 싶다면 __문의하기__ 해주세요"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("자판기 이용이 제한되어 있습니다"))
        self.add_item(c)
# 밴 설정 결과 안내 뷰 (차단)
class BanSetView(ui.LayoutView):
    def __init__(self, user_name):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay("**자판기 밴 설정**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"{user_name}님은 이제 자판기 이용 불가능합니다"))
        c.add_item(ui.TextDisplay("밴 해제는 /자판기_이용_설정"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("성공적으로 완료되었습니다."))
        self.add_item(c)

# 밴 설정 결과 안내 뷰 (허용)
class UnbanSetView(ui.LayoutView):
    def __init__(self, user_name):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay("**자판기 밴 설정**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"{user_name}님은 이제 자판기 이용 가능합니다"))
        c.add_item(ui.TextDisplay("밴 하기는 /자판기_이용_설정"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("성공적으로 완료되었습니다."))
        self.add_item(c)

# 결제 수단 설정 결과 안내 뷰
class PaymentMethodView(ui.LayoutView):
    def __init__(self, account_transfer, coin_payment, mun_sang):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay("**결제 수단 설정**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"**계좌이체** = __{account_transfer}__"))
        c.add_item(ui.TextDisplay(f"**코인결제** = __{coin_payment}__"))
        c.add_item(ui.TextDisplay(f"**문상결제** = __{mun_sang}__"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("성공적으로 완료되었습니다."))
        self.add_item(c)

# 계좌번호 설정 결과 안내 뷰
class BankAccountSetView(ui.LayoutView):
    def __init__(self, bank_name, account_holder, account_number):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay("**정보 변경**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"**은행명** = __{bank_name}__"))
        c.add_item(ui.TextDisplay(f"**예금주** = __{account_holder}__"))
        c.add_item(ui.TextDisplay(f"**계좌번호** = __{account_number}__"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("성공적으로 완료되었습니다."))
        self.add_item(c)

# 계좌이체 신청 완료 안내 뷰
class ChargeRequestCompleteView(ui.LayoutView):
    def __init__(self, bank_name, account_holder, account_number, amount):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay("**계좌이체 신청 완료**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"**은행명** = {bank_name}"))
        c.add_item(ui.TextDisplay(f"**예금주** = {account_holder}"))
        c.add_item(ui.TextDisplay(f"**계좌번호** = `{account_number}`"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"**입금 금액** = {amount}원"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("-# 5분안에 입금해주셔야 지충됩니다."))
        c.add_item(ui.TextDisplay("-# 입금자명 틀릴시 자충 인식 안 합니다."))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("자충 오류시 티켓 열고 이중창해주세요."))
        self.add_item(c)
# 충전 결제수단 선택 뷰
class ChargeView(ui.LayoutView):
    def __init__(self, account_transfer, coin_payment, mun_sang):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay("**결제수단 선택**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("아래 원하시는 결제수단을 클릭해주세요"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        custom_emoji7 = PartialEmoji(name="TOSS", id=1423544803559342154) # TOSS 이모지 (예시 ID, 실제 사용 시 올바른 ID로 변경)
        custom_emoji8 = PartialEmoji(name="bitcoin", id=1423544805975265374) # 비트코인 이모지 (예시 ID)
        custom_emoji9 = PartialEmoji(name="1200x630wa", id=1423544804721164370) # 문화상품권 이모지 (예시 ID)

        # 지원 여부에 따라 버튼 활성화/비활성화
        account_button = ui.Button(label="계좌이체", custom_id="pay_account", emoji=custom_emoji7,
                                   style=discord.ButtonStyle.primary if account_transfer == "지원" else discord.ButtonStyle.secondary,
                                   disabled=account_transfer != "지원")
        account_button.callback = self.account_button_callback

        coin_button = ui.Button(label="코인결제", custom_id="pay_coin", emoji=custom_emoji8,
                                style=discord.ButtonStyle.primary if coin_payment == "지원" else discord.ButtonStyle.secondary,
                                disabled=coin_payment != "지원")
        coin_button.callback = self.coin_button_callback

        mun_sang_button = ui.Button(label="문상결제", custom_id="pay_munsang", emoji=custom_emoji9,
                                    style=discord.ButtonStyle.primary if mun_sang == "지원" else discord.ButtonStyle.secondary,
                                    disabled=mun_sang != "지원")
        mun_sang_button.callback = self.munsang_button_callback

        c.add_item(ui.ActionRow(account_button, coin_button, mun_sang_button))
        
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        supported = []
        if account_transfer == "지원": supported.append("계좌이체")
        if coin_payment == "지원": supported.append("코인결제")
        if mun_sang == "지원": supported.append("문상결제")

        supported_text = ", ".join(supported) if supported else "없음"
        c.add_item(ui.TextDisplay(f"결제가능한 서비스 = {supported_text}"))
        self.add_item(c)
    
    async def account_button_callback(self, interaction: discord.Interaction):
        try:
            user_id = str(interaction.user.id)
            bank_name, account_holder, account_number = get_bank_account(user_id)

            if not bank_name:
                await interaction.response.send_message(view=ErrorMessageView("먼저 `/계좌번호_설정` 명령어로 계좌 정보를 설정해주세요."), ephemeral=True)
                return

            modal = AccountTransferModal(bank_name, account_holder, account_number)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"계좌이체 버튼 오류: {e}")
            await interaction.response.send_message(view=ErrorMessageView("오류가 발생했습니다. 다시 시도해주세요."), ephemeral=True)

    async def coin_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=ErrorMessageView("코인결제 기능은 아직 구현되지 않았습니다."), ephemeral=True)

    async def munsang_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=ErrorMessageView("문상결제 기능은 아직 구현되지 않았습니다."), ephemeral=True)

# 유저 정보 뷰
class UserInfoView(ui.LayoutView):
    def __init__(self, user_name, balance, total_amount, transaction_count):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay(f"**{user_name}님 정보**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"**남은 금액** = __{balance:,}원__"))
        c.add_item(ui.TextDisplay(f"**누적 금액** = __{total_amount:,}원__"))
        c.add_item(ui.TextDisplay(f"**거래 횟수** = __{transaction_count}번__"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("항상 이용해주셔서 감사합니다."))
        self.add_item(c)

# 공지사항 뷰
class NoticeView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay("**공지사항**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("__3자 입금__할 시 법적 조치합니다\n충전 신청하고 잠수시 __자판기 이용금지__\n__오류__나 __버그__문의는 티켓 열어주세요"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("윈드마켓 / 로벅스 자판기 / 2025 / GMT+09:00"))
        self.add_item(c)

# 오류 메시지 뷰
class ErrorMessageView(ui.LayoutView):
    def __init__(self, message="오류가 발생했습니다. 다시 시도해주세요."):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay(f"❌ **오류 발생**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(message))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("문의가 필요하면 관리자에게 연락해주세요."))
        self.add_item(c)
# 메인 레이아웃 클래스 (MyLayout)
class MyLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None) # 뷰 만료 시간 없음
        
        c = ui.Container(ui.TextDisplay(
            "**로벅스 자판기**\n-# 버튼을 눌러 이용해주세요 !"
        ))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 로벅스 재고 및 총 판매량 섹션 (업데이트 로직은 별도 구현 필요)
        sessao = ui.Section(ui.TextDisplay("**로벅스 재고\n-# 60초마다 갱신됩니다.**"), accessory=ui.Button(label="0로벅스", disabled=True))
        c.add_item(sessao)
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 이모지 (예시 ID, 실제 사용 시 올바른 ID로 변경)
        custom_emoji1 = PartialEmoji(name="emoji_5", id=1424003478275231916)
        custom_emoji2 = PartialEmoji(name="charge", id=1424003480007475281)
        custom_emoji3 = PartialEmoji(name="info", id=1424003482247237908)
        custom_emoji4 = PartialEmoji(name="category", id=1424003481240469615)

        # 메인 버튼들
        button_1 = ui.Button(label="공지사항", custom_id="button_1", emoji=custom_emoji1)
        button_2 = ui.Button(label="충전", custom_id="button_2", emoji=custom_emoji2)
        button_3 = ui.Button(label="내 정보", custom_id="button_3", emoji=custom_emoji3)
        button_4 = ui.Button(label="구매", custom_id="button_4", emoji=custom_emoji4)

        linha = ui.ActionRow(button_1, button_2)
        linha2 = ui.ActionRow(button_3, button_4)

        c.add_item(linha)
        c.add_item(linha2)
        self.add_item(c)

        # 콜백 함수 연결
        button_1.callback = self.button_1_callback
        button_2.callback = self.button_2_callback
        button_3.callback = self.button_3_callback
        button_4.callback = self.button_4_callback

    # 공지사항 버튼 콜백
    async def button_1_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if not await check_vending_access(user_id):
            await interaction.response.send_message(view=VendingBanView(), ephemeral=True)
            return
        await interaction.response.send_message(view=NoticeView(), ephemeral=True)

    # 충전 버튼 콜백
    async def button_2_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if not await check_vending_access(user_id):
            await interaction.response.send_message(view=VendingBanView(), ephemeral=True)
            return
        
        account, coin, mun_sang = get_payment_methods(user_id)
        await interaction.response.send_message(view=ChargeView(account, coin, mun_sang), ephemeral=True)

    # 내 정보 버튼 콜백
    async def button_3_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if not await check_vending_access(user_id):
            await interaction.response.send_message(view=VendingBanView(), ephemeral=True)
            return

        info = get_user_info(user_id)
        balance = info['balance'] if info else 0
        total_amount = info['total_amount'] if info else 0
        transaction_count = info['transaction_count'] if info else 0

        await interaction.response.send_message(view=UserInfoView(interaction.user.name, balance, total_amount, transaction_count), ephemeral=True)

    # 구매 버튼 콜백
    async def button_4_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if not await check_vending_access(user_id):
            await interaction.response.send_message(view=VendingBanView(), ephemeral=True)
            return
        await interaction.response.send_message(view=ErrorMessageView("구매 기능은 아직 구현되지 않았습니다."), ephemeral=True)
# === 모달 클래스 정의 ===

# 계좌 설정 모달
class AccountSettingModal(ui.Modal, title="계좌번호 설정"):
    bank_name_input = ui.TextInput(label="은행명", style=discord.TextStyle.short, required=True, max_length=20)
    account_holder_input = ui.TextInput(label="예금주", style=discord.TextStyle.short, required=True, max_length=20)
    account_number_input = ui.TextInput(label="계좌번호", style=discord.TextStyle.short, required=True, min_length=5, max_length=30)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        bank_name = self.bank_name_input.value
        account_holder = self.account_holder_input.value
        account_number = self.account_number_input.value

        set_bank_account(user_id, bank_name, account_holder, account_number)
        await interaction.response.send_message(view=BankAccountSetView(bank_name, account_holder, account_number), ephemeral=True)

# 계좌 이체 모달 (충전 신청용)
class AccountTransferModal(ui.Modal, title="계좌이체 신청"):
    def __init__(self, bank_name, account_holder, account_number):
        super().__init__(timeout=None)
        self.bank_name = bank_name
        self.account_holder = account_holder
        self.account_number = account_number

        self.depositor_name_input = ui.TextInput(label="입금자명", style=discord.TextStyle.short, required=True, min_length=2, max_length=10)
        self.amount_input = ui.TextInput(label="금액", placeholder="숫자만 입력해주세요. (예: 5000)", style=discord.TextStyle.short, required=True, min_length=1, max_length=15)
        self.add_item(self.depositor_name_input)
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        depositor_name = self.depositor_name_input.value.strip()
        amount_str = self.amount_input.value.strip()

        try:
            amount_value = int(amount_str.replace(',', ''))
            if amount_value <= 0:
                raise ValueError("금액은 0보다 커야 합니다.")
        except ValueError:
            await interaction.response.send_message(view=ErrorMessageView("금액은 유효한 숫자로 입력해주세요!"), ephemeral=True)
            return
        
        # 충전 요청 DB에 기록 (auto_process_charge_requests가 처리)
        create_charge_request(user_id, depositor_name, amount_value)

        await interaction.response.send_message(view=ChargeRequestCompleteView(self.bank_name, self.account_holder, self.account_number, f"{amount_value:,}"), ephemeral=True)

# === 일반적인 오류 메시지 뷰 ===
class ErrorMessageView(ui.LayoutView):
    def __init__(self, message="오류가 발생했습니다. 다시 시도해주세요."):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay(f"❌ **오류 발생**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(message))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("문의가 필요하면 관리자에게 연락해주세요."))
        self.add_item(c)
# === 슬래시 명령어 정의 ===

@bot.tree.command(name="버튼패널", description="버튼 패널을 표시합니다.")
async def button_panel(interaction: discord.Interaction):
    await interaction.response.send_message(view=MyLayout(), ephemeral=None)

@bot.tree.command(name="자판기_이용_설정", description="자판기 이용을 금지할 수 있습니다")
@discord.app_commands.describe(
    target_user="밴 상태를 설정할 유저를 선택하세요",
    ban_status="밴 여부 선택 (허용 또는 차단)"
)
@discord.app_commands.choices(
    ban_status=[
        discord.app_commands.Choice(name='허용', value='x'),
        discord.app_commands.Choice(name='차단', value='o')
    ]
)
async def vending_machine_ban(interaction: discord.Interaction, target_user: discord.User, ban_status: discord.app_commands.Choice[str]):
    user_id = str(target_user.id)
    set_user_ban(user_id, ban_status.value)

    if ban_status.value == 'o':
        await interaction.response.send_message(view=BanSetView(target_user.name), ephemeral=True)
    else:
        await interaction.response.send_message(view=UnbanSetView(target_user.name), ephemeral=True)

@bot.tree.command(name="결제수단_설정", description="봇에서 지원할 결제 수단을 설정합니다.")
@discord.app_commands.describe(
    account_transfer="계좌이체 지원 여부",
    coin_payment="코인결제 지원 여부",
    mun_sang="문상결제 지원 여부"
)
@discord.app_commands.choices(
    account_transfer=[
        discord.app_commands.Choice(name='지원', value='지원'),
        discord.app_commands.Choice(name='미지원', value='미지원')
    ],
    coin_payment=[
        discord.app_commands.Choice(name='지원', value='지원'),
        discord.app_commands.Choice(name='미지원', value='미지원')
    ],
    mun_sang=[
        discord.app_commands.Choice(name='지원', value='지원'),
        discord.app_commands.Choice(name='미지원', value='미지원')
    ]
)
async def payment_method_set(
    interaction: discord.Interaction,
    account_transfer: discord.app_commands.Choice[str],
    coin_payment: discord.app_commands.Choice[str],
    mun_sang: discord.app_commands.Choice[str]
):
    user_id = str(interaction.user.id)
    set_payment_methods(user_id, account_transfer.value, coin_payment.value, mun_sang.value)
    await interaction.response.send_message(view=PaymentMethodView(account_transfer.value, coin_payment.value, mun_sang.value), ephemeral=True)

@bot.tree.command(name="계좌번호_설정", description="봇에 사용될 계좌 정보를 설정합니다.")
async def set_bank_account_cmd(interaction: discord.Interaction):
    modal = AccountSettingModal()
    await interaction.response.send_modal(modal)


# === 디스코드 봇 이벤트 핸들러 ===

@bot.event
async def on_ready():
    print(f"로벅스 자판기 봇이 {bot.user}로 로그인했습니다.")
    bot.loop.create_task(auto_process_charge_requests()) # 자동 충전 태스크 시작
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'슬래시 명령어 동기화 중 오류 발생.: {e}')

# === Flask API 서버 구현 시작 ===
# 외부에서 HTTP 요청(예: 아이폰 단축어)을 받기 위한 웹 서버
flask_app = Flask(__name__)

@flask_app.route("/api/charge", methods=["POST"])
def charge_api():
    # 이 부분에서 봇 내부의 DB 함수들을 사용하게 됩니다.
    # Flask 앱과 디스코드 봇이 같은 프로세스에서 실행되므로, 같은 conn, cur, db_lock을 공유합니다.
    
    data = request.get_json()
    sms_text = data.get("message", "")

    # 정규식으로 입금자명, 금액 추출 (한글 2~4글자, 금액 숫자)
    # 은행 메시지 형식에 따라 이 정규식 패턴을 미세 조정해야 합니다.
    # 예: "국민 김철수 50000원 입금", "5만원 입금 신한 이지수"
    # 현재 패턴: '입금자명' 뒤에 '님'/'이'가 오거나 안 올 수 있고, 그 뒤 공백, '금액' 뒤 '원'이 오는 형태
    pattern = r"([가-힣]{2,4})(?:님|이)?\s*(\d[\d,]*)원" 
    match = re.search(pattern, sms_text)
    
    if not match:
        print(f"API - 오류: 입금 정보를 찾을 수 없습니다. 메시지: {sms_text}")
        return jsonify({"status": "error", "message": "입금 정보를 찾을 수 없습니다"}), 400

    depositor_name = match.group(1).strip()
    amount_str = match.group(2).replace(",", "").strip()
    try:
        amount = int(amount_str)
        if amount <= 0:
            raise ValueError("금액은 0보다 커야 합니다.")
    except ValueError:
        print(f"API - 오류: 금액 변환 또는 값 오류. 메시지: {sms_text}, 금액 부분: {amount_str}")
        return jsonify({"status": "error", "message": "금액 형식 오류 또는 유효하지 않은 금액"}), 400

    # DB에서 입금자명으로 디스코드 user_id 찾기
    with db_lock:
        cur.execute("SELECT user_id FROM bank_accounts WHERE account_holder = ?", (depositor_name,))
        row = cur.fetchone() # 결과를 Row 객체로 받음
    
    if not row:
        print(f"API - 오류: 입금자명({depositor_name})과 매칭되는 디스코드 사용자 ID를 찾을 수 없습니다. 메시지: {sms_text}")
        return jsonify({"status": "error", "message": f"입금자 '{depositor_name}'과 연결된 디스코드 계정을 찾을 수 없습니다. '/계좌번호_설정'으로 등록해주세요."}), 404

    discord_user_id = row["user_id"] # Row 객체에서 user_id 컬럼으로 접근

    # 충전 요청을 DB에 저장 (auto_process_charge_requests가 이를 처리)
    create_charge_request(discord_user_id, depositor_name, amount)
    
    print(f"API - 성공: 충전 요청 등록됨 - Discord User ID: {discord_user_id}, 입금자명: {depositor_name}, 금액: {amount}, 메시지: {sms_text}")
    return jsonify({"status": "success", "message": "충전 요청이 성공적으로 등록되었습니다. 잠시 후 처리됩니다."}), 200

# Flask 앱을 별도의 스레드에서 실행하는 함수
def run_flask():
    print("Flask API 서버 시작 중...")
    flask_app.run(host="0.0.0.0", port=5000) # 포트 5000으로 서버 시작

# === 봇과 플라스크 API 동시에 실행하는 메인 함수 ===
def main():
    # Flask 서버를 별도의 스레드에서 시작
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True # 메인 스레드(봇)가 종료되면 같이 종료되도록 설정
    flask_thread.start()

    # 디스코드 봇 시작
    bot.run("YOUR_BOT_TOKEN")  # 여기에 봇 토큰을 입력하세요

if __name__ == "__main__":
    main()
