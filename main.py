import discord
import sqlite3
import asyncio # asyncio는 직접 사용하지 않지만, discord.py는 비동기 라이브러리이므로 필요할 수 있습니다.
from discord impo
rt PartialEmoji, ui
from discord.ext import commands
# --- 인텐트 및 봇 설정 ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)

# --- DB 설정 및 테이블 생성 ---
conn = sqlite3.connect('database.db')
cur = conn.cursor()

cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        balance INTEGER,
        total_amount INTEGER,
        transaction_count INTEGER
    )
''')

cur.execute('''
    CREATE TABLE IF NOT EXISTS user_bans (
        user_id TEXT PRIMARY KEY,
        banned TEXT CHECK(banned IN ('o', 'x'))
    )
''')

cur.execute('''
    CREATE TABLE IF NOT EXISTS payment_methods (
        user_id TEXT PRIMARY KEY,
        account_transfer TEXT CHECK(account_transfer IN ('지원', '미지원')),
        coin_payment TEXT CHECK(coin_payment IN ('지원', '미지원')),
        mun_sang_payment TEXT CHECK(mun_sang_payment IN ('지원', '미지원'))
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

conn.commit()

# --- DB 관련 함수들 ---
def add_or_update_user(user_id, balance, total_amount, transaction_count):
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
    cur.execute('''
        INSERT INTO user_bans (user_id, banned) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET banned=excluded.banned
    ''', (user_id, status))
    conn.commit()

def get_user_ban(user_id):
    cur.execute('SELECT banned FROM user_bans WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    return result[0] if result else 'x' # 기본값 'x' (밴 아님)

def get_user_info(user_id):
    cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return cur.fetchone()

def set_payment_methods(user_id, account_transfer, coin_payment, mun_sang):
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
    cur.execute('SELECT account_transfer, coin_payment, mun_sang_payment FROM payment_methods WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    return result if result else ('미지원', '미지원', '미지원')

def set_bank_account(user_id, bank_name, account_holder, account_number):
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
    cur.execute('SELECT bank_name, account_holder, account_number FROM bank_accounts WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    return result if result else (None, None, None)

async def check_vending_access(user_id):
    return get_user_ban(user_id) != 'o'

# --- UI 뷰 클래스 정의 ---

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

        account_button = None
        if account_transfer == "지원":
            account_button = ui.Button(label="계좌이체", custom_id="pay_account", emoji=custom_emoji7, style=discord.ButtonStyle.primary)
            account_button.callback = self.account_button_callback
        else:
            account_button = ui.Button(label="계좌이체", disabled=True, emoji=custom_emoji7, style=discord.ButtonStyle.secondary)

        coin_button = None
        if coin_payment == "지원":
            coin_button = ui.Button(label="코인결제", custom_id="pay_coin", emoji=custom_emoji8, style=discord.ButtonStyle.primary)
            coin_button.callback = self.coin_button_callback # 코인결제 콜백 추가 (필요시 구현)
        else:
            coin_button = ui.Button(label="코인결제", disabled=True, emoji=custom_emoji8, style=discord.ButtonStyle.secondary)

        mun_sang_button = None
        if mun_sang == "지원":
            mun_sang_button = ui.Button(label="문상결제", custom_id="pay_munsang", emoji=custom_emoji9, style=discord.ButtonStyle.primary)
            mun_sang_button.callback = self.munsang_button_callback # 문상결제 콜백 추가 (필요시 구현)
        else:
            mun_sang_button = ui.Button(label="문상결제", disabled=True, emoji=custom_emoji9, style=discord.ButtonStyle.secondary)

        c.add_item(ui.ActionRow(account_button, coin_button, mun_sang_button))
        
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        supported = []
        if account_transfer == "지원":
            supported.append("계좌이체")
        if coin_payment == "지원":
            supported.append("코인결제")
        if mun_sang == "지원":
            supported.append("문상결제")

        supported_text = ", ".join(supported) if supported else "없음"
        c.add_item(ui.TextDisplay(f"결제가능한 서비스 = {supported_text}"))
        self.add_item(c)
    
    # 계좌이체 버튼 콜백
    async def account_button_callback(self, interaction: discord.Interaction):
        try:
            user_id = str(interaction.user.id)
            bank_name, account_holder, account_number = get_bank_account(user_id)

            if not bank_name:
                await interaction.response.send_message("먼저 `/계좌번호_설정` 명령어로 계좌 정보를 설정해주세요.", ephemeral=True)
                return

            modal = AccountTransferModal(bank_name, account_holder, account_number)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"계좌이체 버튼 오류: {e}")
            await interaction.response.send_message("오류가 발생했습니다. 다시 시도해주세요.", ephemeral=True)

    # 코인결제 버튼 콜백 (필요시 구현)
    async def coin_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("코인결제 기능은 아직 구현되지 않았습니다.", ephemeral=True)

    # 문상결제 버튼 콜백 (필요시 구현)
    async def munsang_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("문상결제 기능은 아직 구현되지 않았습니다.", ephemeral=True)

class UserInfoView(ui.LayoutView):
    def __init__(self, user_name, balance, total_amount, transaction_count):
        super().__init__(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay(f"**{user_name}님 정보**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"**남은 금액** = __{balance}원__"))
        c.add_item(ui.TextDisplay(f"**누적 금액** = __{total_amount}원__"))
        c.add_item(ui.TextDisplay(f"**거래 횟수** = __{transaction_count}번__"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay("항상 이용해주셔서 감사합니다."))
        self.add_item(c)

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

# 버튼 상호작용 오류 방지를 위한 뷰 저장소 (Persistent View를 위한 기본 틀, 현재 코드에서 직접적인 재등록 로직은 비활성화)
active_views = {}

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
            view = VendingBanView()
            await interaction.response.send_message(view=view, ephemeral=True)
            return

        view = NoticeView()
        await interaction.response.send_message(view=view, ephemeral=True)

    # 충전 버튼 콜백
    async def button_2_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if not await check_vending_access(user_id):
            view = VendingBanView()
            await interaction.response.send_message(view=view, ephemeral=True)
            return
        
        account, coin, mun_sang = get_payment_methods(user_id)
        view = ChargeView(account, coin, mun_sang)
        await interaction.response.send_message(view=view, ephemeral=True)

    # 내 정보 버튼 콜백
    async def button_3_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if not await check_vending_access(user_id):
            view = VendingBanView()
            await interaction.response.send_message(view=view, ephemeral=True)
            return

        info = get_user_info(user_id)
        if info:
            balance = info[1]
            total_amount = info[2]
            transaction_count = info[3]
        else:
            balance = total_amount = transaction_count = 0

        view = UserInfoView(interaction.user.name, balance, total_amount, transaction_count)
        await interaction.response.send_message(view=view, ephemeral=True)

    # 구매 버튼 콜백
    async def button_4_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if not await check_vending_access(user_id):
            view = VendingBanView()
            await interaction.response.send_message(view=view, ephemeral=True)
            return

        await interaction.response.send_message("구매 기능은 아직 구현되지 않았습니다.", ephemeral=True) # 임시 메시지


# --- 모달 클래스 정의 ---

# 계좌번호 설정 모달
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
        view = BankAccountSetView(bank_name, account_holder, account_number)
        await interaction.response.send_message(view=view, ephemeral=True)

# 계좌이체 신청 모달
# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
# 이 부분이 수정되었습니다.
# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
class AccountTransferModal(ui.Modal, title="계좌이체 신청"):
    def __init__(self, bank_name, account_holder, account_number):
        super().__init__(timeout=None)
        self.bank_name = bank_name
        self.account_holder = account_holder
        self.account_number = account_number

        self.depositor_name_input = ui.TextInput(
            label="입금자명",
            style=discord.TextStyle.short,
            required=True,
            min_length=2, max_length=10
        )
        self.amount_input = ui.TextInput(
            label="금액",
            placeholder="숫자만 입력해주세요. (예: 5000)",
            style=discord.TextStyle.short,
            required=True,
            min_length=3, max_length=15
        )
        self.add_item(self.depositor_name_input)
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        depositor_name = self.depositor_name_input.value
        amount = self.amount_input.value

        try:
            amount_value = int(amount.replace(',', ''))
        except ValueError:
            await interaction.response.send_message("금액은 숫자로만 입력해주세요!", ephemeral=True)
            return

        view = ChargeRequestCompleteView(
            bank_name=self.bank_name,
            account_holder=self.account_holder,
            account_number=self.account_number,
            amount=f"{amount_value:,}"
        )
        
        await interaction.response.send_message(view=view, ephemeral=True)

# --- 슬래시 명령어 정의 ---

@bot.tree.command(name="버튼패널", description="버튼 패널을 표시합니다.")
async def button_panel(interaction: discord.Interaction):
    layout = MyLayout()
    await interaction.response.send_message(view=layout, ephemeral=None)

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
        view = BanSetView(target_user.name)
        await interaction.response.send_message(view=view, ephemeral=True)
    else:
        view = UnbanSetView(target_user.name)
        await interaction.response.send_message(view=view, ephemeral=True)

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
    view = PaymentMethodView(account_transfer.value, coin_payment.value, mun_sang.value)
    await interaction.response.send_message(view=view, ephemeral=True)

@bot.tree.command(name="계좌번호_설정", description="봇에 사용될 계좌 정보를 설정합니다.")
async def set_bank_account_cmd(interaction: discord.Interaction):
    modal = AccountSettingModal()
    await interaction.response.send_modal(modal)


# --- 봇 이벤트 핸들러 ---

@bot.event
async def on_ready():
    print(f"로벅스 자판기 봇이 {bot.user}로 로그인했습니다.")
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'슬래시 명령어 동기화 중 오류 발생.: {e}')

# --- 봇 실행 ---
bot.run("MTQyNjQ3Njk4MDE3NzYwMDU2NA.GyMruh.niRY3cQH2ECAX9oeDgyHwQ6X8fK0BxENH_dqJI") # 여기에 봇 토큰을 입력하세요
