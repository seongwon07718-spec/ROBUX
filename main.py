# 필요한 라이브러리 임포트
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

# === DB 설정 및 초기화 ===
# DB 연결 (스레드 안전성 확보)
conn = sqlite3.connect(
    "database.db",
    detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    check_same_thread=False,  # asyncio와 SQLite 사용 시 필수
)
conn.row_factory = sqlite3.Row  # 결과를 딕셔너리처럼 접근 가능하게 설정
cur = conn.cursor()

# DB 접근 시 스레드 간 충돌 방지를 위한 락 (Lock)
db_lock = threading.RLock()

def initialize_database():
    """데이터베이스 테이블을 생성하고 초기화합니다."""
    with db_lock:
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
                request_time TIMESTAMP NOT NULL
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
            INSERT INTO user_bans (user_id, banned) VALUES (?, ?)
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
        cur.execute("SELECT account_transfer, coin_payment, mun_sang_payment FROM payment_methods WHERE user_id = ?", (user_id,))
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
        # 시간을 UTC ISO 8601 형식의 문자열로 저장하여 시간대 문제 방지
        request_time_utc_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur.execute('''
            INSERT INTO charge_requests (user_id, depositor_name, amount, status, request_time)
            VALUES (?, ?, ?, '대기', ?)
        ''', (user_id, depositor_name, amount, request_time_utc_str))
        conn.commit()

async def check_vending_access(user_id):
    return get_user_ban(user_id) != "o"

# === 자동 충전 처리 태스크 (안정성 강화) ===
async def auto_process_charge_requests():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            with db_lock:
                cur.execute("SELECT * FROM charge_requests WHERE status = '대기'")
                pending_requests = cur.fetchall()

            for req in pending_requests:
                req_id = req["id"]
                user_id = req["user_id"]
                amount = req["amount"]
                
                # DB에서 문자열로 저장된 시간을 datetime 객체로 변환
                request_time_utc = datetime.datetime.fromisoformat(req["request_time"])
                
                elapsed_seconds = (now_utc - request_time_utc).total_seconds()

                if elapsed_seconds > 300:  # 5분(300초) 초과 시 만료 처리
                    with db_lock:
                        cur.execute("UPDATE charge_requests SET status='만료' WHERE id=?", (req_id,))
                        conn.commit()
                    print(f"충전 요청 {req_id} 만료 처리 (5분 초과)")
                    try:
                        user = await bot.fetch_user(int(user_id))
                        await user.send(view=ChargeExpiredView(req["depositor_name"], amount))
                    except Exception as e:
                        print(f"만료 알림 DM 전송 실패 user_id={user_id}: {e}")
                    continue

                # [안정성 강화] 이중 충전 방지를 위해 상태를 '처리중'으로 먼저 변경
                with db_lock:
                    cur.execute("UPDATE charge_requests SET status='처리중' WHERE id=?", (req_id,))
                    conn.commit()

                # 사용자 정보 조회 및 잔액 업데이트
                user_info = get_user_info(user_id)
                old_balance = user_info["balance"] if user_info else 0
                new_balance = old_balance + amount
                total_amount = (user_info["total_amount"] if user_info else 0) + amount
                transaction_count = (user_info["transaction_count"] if user_info else 0) + 1

                add_or_update_user(user_id, new_balance, total_amount, transaction_count)

                # 최종적으로 상태를 '완료'로 변경
                with db_lock:
                    cur.execute("UPDATE charge_requests SET status='완료' WHERE id=?", (req_id,))
                    conn.commit()
                
                print(f"자동충전 완료: 사용자 {user_id}, 금액 {amount}원")
                
                try:
                    user = await bot.fetch_user(int(user_id))
                    await user.send(view=ChargeCompleteView(old_balance, new_balance, amount))
                except Exception as e:
                    print(f"충전 완료 알림 DM 전송 실패 user_id={user_id}: {e}")
        
        except Exception as e:
            print(f"자동충전 처리 태스크 전체 오류: {e}")
        
        await asyncio.sleep(30)  # 30초마다 확인

# === UI 뷰 클래스 정의 (생성자 '__init__' 수정) ===
class ChargeCompleteView(ui.LayoutView):
    def __init__(self, old_balance, new_balance, charged_amount):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay("✅ **정상적으로 충전이 완료되었습니다**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"충전 금액: **{charged_amount:,}원**"))
        c.add_item(ui.TextDisplay(f"충전 후 금액: **{new_balance:,}원**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("오늘도 즐거운 하루 되시길 바랍니다."))
        self.add_item(c)

class ChargeExpiredView(ui.LayoutView):
    def __init__(self, depositor_name, amount):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay("⚠️ **충전 요청 만료 안내**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"입금자명: `{depositor_name}`"))
        c.add_item(ui.TextDisplay(f"금액: `{amount:,}원`"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("5분 이내 입금 확인이 안되어 충전 요청이 만료되었습니다.\n다시 신청해주세요."))
        self.add_item(c)

class VendingBanView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        c = ui.Container(ui.TextDisplay("**자판기 이용 관련**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("현재 고객님은 자판기 이용이 __불가능__합니다.\n자세한 이유를 알고 싶다면 __문의하기__ 해주세요."))
        self.add_item(c)

class BanSetView(ui.LayoutView):
    def __init__(self, user_name):
        super().__init__(timeout=None)
        c = ui.Container(ui.TextDisplay("**자판기 밴 설정**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"`{user_name}`님은 이제 자판기 이용이 **불가능**합니다.\n밴 해제는 `/자판기_이용_설정`을 이용하세요."))
        self.add_item(c)

class UnbanSetView(ui.LayoutView):
    def __init__(self, user_name):
        super().__init__(timeout=None)
        c = ui.Container(ui.TextDisplay("**자판기 밴 설정**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"`{user_name}`님은 이제 자판기 이용이 **가능**합니다.\n밴 설정은 `/자판기_이용_설정`을 이용하세요."))
        self.add_item(c)

class PaymentMethodView(ui.LayoutView):
    def __init__(self, account_transfer, coin_payment, mun_sang):
        super().__init__(timeout=None)
        c = ui.Container(ui.TextDisplay("**결제 수단 설정 완료**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"계좌이체 = **{account_transfer}**"))
        c.add_item(ui.TextDisplay(f"코인결제 = **{coin_payment}**"))
        c.add_item(ui.TextDisplay(f"문상결제 = **{mun_sang}**"))
        self.add_item(c)

class BankAccountSetView(ui.LayoutView):
    def __init__(self, bank_name, account_holder, account_number):
        super().__init__(timeout=None)
        c = ui.Container(ui.TextDisplay("**계좌 정보 변경 완료**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"은행명 = **{bank_name}**"))
        c.add_item(ui.TextDisplay(f"예금주 = **{account_holder}**"))
        c.add_item(ui.TextDisplay(f"계좌번호 = **{account_number}**"))
        self.add_item(c)

class ChargeRequestCompleteView(ui.LayoutView):
    def __init__(self, bank_name, account_holder, account_number, amount):
        super().__init__(timeout=None)
        c = ui.Container(ui.TextDisplay("**계좌이체 신청 완료**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"은행명 = `{bank_name}`"))
        c.add_item(ui.TextDisplay(f"예금주 = `{account_holder}`"))
        c.add_item(ui.TextDisplay(f"계좌번호 = `{account_number}`"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"입금 금액 = **{amount}원**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("-# 5분 안에 입금해주셔야 자동충전됩니다.\n-# 입금자명이 다를 시 자동충전이 불가능합니다."))
        self.add_item(c)

class ChargeView(ui.LayoutView):
    def __init__(self, account_transfer, coin_payment, mun_sang):
        super().__init__(timeout=None)
        c = ui.Container(ui.TextDisplay("**결제수단 선택**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("아래 원하시는 결제수단을 클릭해주세요."))
        
        custom_emoji7 = PartialEmoji(name="TOSS", id=123456789012345678) # 실제 ID로 변경
        custom_emoji8 = PartialEmoji(name="bitcoin", id=123456789012345678) # 실제 ID로 변경
        custom_emoji9 = PartialEmoji(name="1200x630wa", id=123456789012345678) # 실제 ID로 변경

        account_button = ui.Button(label="계좌이체", custom_id="pay_account", emoji=custom_emoji7, style=discord.ButtonStyle.primary, disabled=(account_transfer != "지원"))
        coin_button = ui.Button(label="코인결제", custom_id="pay_coin", emoji=custom_emoji8, style=discord.ButtonStyle.primary, disabled=(coin_payment != "지원"))
        mun_sang_button = ui.Button(label="문상결제", custom_id="pay_munsang", emoji=custom_emoji9, style=discord.ButtonStyle.primary, disabled=(mun_sang != "지원"))

        account_button.callback = self.account_button_callback
        coin_button.callback = self.coin_button_callback
        mun_sang_button.callback = self.munsang_button_callback

        c.add_item(ui.ActionRow(account_button, coin_button, mun_sang_button))
        self.add_item(c)

    async def account_button_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        bank_name, _, _ = get_bank_account(user_id)
        if not bank_name:
            await interaction.response.send_message(view=ErrorMessageView("먼저 `/계좌번호_설정`으로 계좌 정보를 설정해주세요."), ephemeral=True)
            return
        await interaction.response.send_modal(AccountTransferModal())

    async def coin_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=ErrorMessageView("코인결제 기능은 아직 구현되지 않았습니다."), ephemeral=True)

    async def munsang_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=ErrorMessageView("문상결제 기능은 아직 구현되지 않았습니다."), ephemeral=True)

class UserInfoView(ui.LayoutView):
    def __init__(self, user_name, balance, total_amount, transaction_count):
        super().__init__(timeout=None)
        c = ui.Container(ui.TextDisplay(f"**{user_name}님 정보**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"남은 금액 = **{balance:,}원**"))
        c.add_item(ui.TextDisplay(f"누적 금액 = **{total_amount:,}원**"))
        c.add_item(ui.TextDisplay(f"거래 횟수 = **{transaction_count}번**"))
        self.add_item(c)

class NoticeView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        c = ui.Container(ui.TextDisplay("**공지사항**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("__3자 입금__ 시 법적 조치합니다\n충전 신청 후 잠수 시 __자판기 이용금지__\n__오류__나 __버그__ 문의는 티켓을 열어주세요"))
        self.add_item(c)

class ErrorMessageView(ui.LayoutView):
    def __init__(self, message="오류가 발생했습니다. 다시 시도해주세요."):
        super().__init__(timeout=None)
        c = ui.Container(ui.TextDisplay("❌ **오류 발생**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(message))
        self.add_item(c)

class MyLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        c = ui.Container(ui.TextDisplay("**로벅스 자판기**\n-# 버튼을 눌러 이용해주세요 !"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # ... (이모지 및 버튼 설정 부분은 기존 코드와 동일하게 유지) ...
        # 이모지 ID는 실제 사용 가능한 ID로 변경해야 합니다.
        custom_emoji1 = PartialEmoji(name="emoji_5", id=123456789012345678)
        custom_emoji2 = PartialEmoji(name="charge", id=123456789012345678)
        custom_emoji3 = PartialEmoji(name="info", id=123456789012345678)
        custom_emoji4 = PartialEmoji(name="category", id=123456789012345678)

        button_1 = ui.Button(label="공지사항", custom_id="button_1", emoji=custom_emoji1)
        button_2 = ui.Button(label="충전", custom_id="button_2", emoji=custom_emoji2)
        button_3 = ui.Button(label="내 정보", custom_id="button_3", emoji=custom_emoji3)
        button_4 = ui.Button(label="구매", custom_id="button_4", emoji=custom_emoji4)
        
        button_1.callback = self.button_1_callback
        button_2.callback = self.button_2_callback
        button_3.callback = self.button_3_callback
        button_4.callback = self.button_4_callback

        c.add_item(ui.ActionRow(button_1, button_2))
        c.add_item(ui.ActionRow(button_3, button_4))
        self.add_item(c)
    
    async def button_1_callback(self, interaction: discord.Interaction):
        if not await check_vending_access(str(interaction.user.id)):
            await interaction.response.send_message(view=VendingBanView(), ephemeral=True)
            return
        await interaction.response.send_message(view=NoticeView(), ephemeral=True)

    async def button_2_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if not await check_vending_access(user_id):
            await interaction.response.send_message(view=VendingBanView(), ephemeral=True)
            return
        account, coin, mun_sang = get_payment_methods(user_id)
        await interaction.response.send_message(view=ChargeView(account, coin, mun_sang), ephemeral=True)

    async def button_3_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if not await check_vending_access(user_id):
            await interaction.response.send_message(view=VendingBanView(), ephemeral=True)
            return
        info = get_user_info(user_id)
        await interaction.response.send_message(view=UserInfoView(
            interaction.user.display_name,
            info['balance'] if info else 0,
            info['total_amount'] if info else 0,
            info['transaction_count'] if info else 0
        ), ephemeral=True)

    async def button_4_callback(self, interaction: discord.Interaction):
        if not await check_vending_access(str(interaction.user.id)):
            await interaction.response.send_message(view=VendingBanView(), ephemeral=True)
            return
        await interaction.response.send_message(view=ErrorMessageView("구매 기능은 아직 구현되지 않았습니다."), ephemeral=True)

# === 모달 클래스 정의 ===
class AccountSettingModal(ui.Modal, title="계좌번호 설정"):
    bank_name_input = ui.TextInput(label="은행명", required=True)
    account_holder_input = ui.TextInput(label="예금주 (본인 실명)", required=True)
    account_number_input = ui.TextInput(label="계좌번호", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        set_bank_account(user_id, self.bank_name_input.value, self.account_holder_input.value, self.account_number_input.value)
        await interaction.response.send_message(view=BankAccountSetView(self.bank_name_input.value, self.account_holder_input.value, self.account_number_input.value), ephemeral=True)

class AccountTransferModal(ui.Modal, title="계좌이체 신청"):
    depositor_name_input = ui.TextInput(label="입금자명", required=True)
    amount_input = ui.TextInput(label="금액", placeholder="숫자만 입력 (예: 5000)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        depositor_name = self.depositor_name_input.value.strip()
        
        try:
            amount = int(self.amount_input.value.replace(',', '').strip())
            if amount <= 0: raise ValueError
        except ValueError:
            await interaction.response.send_message(view=ErrorMessageView("금액은 0보다 큰 숫자로만 입력해주세요."), ephemeral=True)
            return
        
        # 관리자 계좌 정보 가져오기 (여기서는 봇 주인 계좌로 가정)
        # 실제 운영 시에는 설정 파일이나 다른 DB 테이블에서 관리자 계좌를 가져와야 합니다.
        admin_id = str(bot.owner_id) # 예시, 실제 봇 주인 ID로 설정 필요
        bank_name, account_holder, account_number = get_bank_account(admin_id)

        if not bank_name:
             await interaction.response.send_message(view=ErrorMessageView("관리자 계좌 정보가 설정되지 않았습니다. 관리자에게 문의하세요."), ephemeral=True)
             return

        create_charge_request(user_id, depositor_name, amount)
        await interaction.response.send_message(view=ChargeRequestCompleteView(bank_name, account_holder, account_number, f"{amount:,}"), ephemeral=True)

# === 슬래시 명령어 정의 ===
@bot.tree.command(name="버튼패널", description="메인 버튼 패널을 현재 채널에 보냅니다.")
async def button_panel(interaction: discord.Interaction):
    await interaction.response.send_message(view=MyLayout())

@bot.tree.command(name="자판기_이용_설정", description="사용자의 자판기 이용 권한을 설정합니다.")
@discord.app_commands.describe(target_user="설정할 사용자", ban_status="차단 또는 허용")
@discord.app_commands.choices(ban_status=[
    discord.app_commands.Choice(name='허용', value='x'),
    discord.app_commands.Choice(name='차단', value='o')
])
async def vending_machine_ban(interaction: discord.Interaction, target_user: discord.User, ban_status: str):
    set_user_ban(str(target_user.id), ban_status)
    if ban_status == 'o':
        await interaction.response.send_message(view=BanSetView(target_user.display_name), ephemeral=True)
    else:
        await interaction.response.send_message(view=UnbanSetView(target_user.display_name), ephemeral=True)

@bot.tree.command(name="결제수단_설정", description="봇에서 지원할 결제 수단을 설정합니다.")
async def payment_method_set(interaction: discord.Interaction, account_transfer: str, coin_payment: str, mun_sang: str):
    user_id = str(interaction.user.id) # 관리자만 사용한다고 가정
    set_payment_methods(user_id, account_transfer, coin_payment, mun_sang)
    await interaction.response.send_message(view=PaymentMethodView(account_transfer, coin_payment, mun_sang), ephemeral=True)

@bot.tree.command(name="계좌번호_설정", description="봇에 사용될 자신의 계좌 정보를 설정합니다.")
async def set_bank_account_cmd(interaction: discord.Interaction):
    await interaction.response.send_modal(AccountSettingModal())


# === 봇 이벤트 핸들러 ===
@bot.event
async def on_ready():
    print(f"로벅스 자판기 봇이 {bot.user}로 로그인했습니다.")
    bot.loop.create_task(auto_process_charge_requests())
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'슬래시 명령어 동기화 중 오류 발생: {e}')

# === Flask API 서버 구현 ===
flask_app = Flask(__name__)

@flask_app.route("/api/charge", methods=["POST"])
def charge_api():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"status": "error", "message": "잘못된 요청입니다."}), 400
    
    sms_text = data["message"]
    
    # 은행 메시지 형식에 따른 정규식 (예: "국민 김철수 50,000원 입금")
    # [입금자명(한글 2~4자)][공백][금액(숫자,쉼표)][원]
    pattern = r"([가-힣]{2,4})\s*([\d,]+)원"
    match = re.search(pattern, sms_text)

    if not match:
        print(f"API - 오류: 입금 정보를 찾을 수 없음. 메시지: {sms_text}")
        return jsonify({"status": "error", "message": "입금 정보를 찾을 수 없습니다."}), 400

    depositor_name = match.group(1)
    amount = int(match.group(2).replace(",", ""))

    # DB에서 입금자명으로 디스코드 user_id 찾기
    with db_lock:
        cur.execute("SELECT user_id FROM bank_accounts WHERE account_holder = ?", (depositor_name,))
        row = cur.fetchone()

    if not row:
        print(f"API - 오류: 입금자명({depositor_name}) 매칭 실패.")
        return jsonify({"status": "error", "message": f"입금자 '{depositor_name}'에 해당하는 사용자를 찾을 수 없습니다."}), 404

    discord_user_id = row["user_id"]
    create_charge_request(discord_user_id, depositor_name, amount)

    print(f"API - 성공: 충전 요청 등록됨 - UserID: {discord_user_id}, Name: {depositor_name}, Amount: {amount}")
    return jsonify({"status": "success", "message": "충전 요청이 등록되었습니다."}), 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=5000)

# === 봇과 플라스크 API 동시 실행 ===
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    bot.run("YOUR_BOT_TOKEN") # 🚨 여기에 실제 봇 토큰을 입력하세요!
