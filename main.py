import discord
import sqlite3
import asyncio
from discord import PartialEmoji, ui
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)

# DB 설정
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

# 계좌번호 정보 저장 테이블 추가
cur.execute('''
    CREATE TABLE IF NOT EXISTS bank_accounts (
        user_id TEXT PRIMARY KEY,
        bank_name TEXT,
        account_holder TEXT,
        account_number TEXT
    )
''')

conn.commit()

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

def set_user_ban(user_id, banned_status):
    cur.execute('''
        INSERT INTO user_bans (user_id, banned) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET banned=excluded.banned
    ''', (user_id, banned_status))
    conn.commit()

def get_user_ban(user_id):
    cur.execute('SELECT banned FROM user_bans WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    if result:
        return result[0]
    return 'x'

def get_user_info(user_id):
    cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    if result:
        return result
    return None

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
    if result:
        return result
    return ('미지원', '미지원', '미지원')

# 계좌번호 설정 함수
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

# 계좌번호 조회 함수
def get_bank_account(user_id):
    cur.execute('SELECT bank_name, account_holder, account_number FROM bank_accounts WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    if result:
        return result
    return (None, None, None)

async def check_vending_access(user_id):
    banned = get_user_ban(user_id)
    return banned != 'o'

class VendingBanView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        container = ui.Container()
        container.add_item(ui.TextDisplay("**자판기 이용 관련**"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("현재 고객님은 자판기 이용이 __불가능__합니다"))
        container.add_item(ui.TextDisplay("자세한 이유를 알고 싶다면 __문의하기__ 해주세요"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("자판기 이용이 제한되어 있습니다"))
        self.add_item(container)

class BanSetView(ui.LayoutView):
    def __init__(self, user_name):
        super().__init__(timeout=None)
        container = ui.Container()
        container.add_item(ui.TextDisplay("**자판기 밴 설정**"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"{user_name}님은 이제 자판기 이용 불가능합니다"))
        container.add_item(ui.TextDisplay("밴 해제는 /자판기_이용_설정"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("성공적으로 완료되었습니다."))
        self.add_item(container)

class UnbanSetView(ui.LayoutView):
    def __init__(self, user_name):
        super().__init__(timeout=None)
        container = ui.Container()
        container.add_item(ui.TextDisplay("**자판기 밴 설정**"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"{user_name}님은 이제 자판기 이용 가능합니다"))
        container.add_item(ui.TextDisplay("밴 하기는 /자판기_이용_설정"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("성공적으로 완료되었습니다."))
        self.add_item(container)

class PaymentMethodView(ui.LayoutView):
    def __init__(self, account_transfer, coin_payment, mun_sang):
        super().__init__(timeout=None)
        container = ui.Container()
        container.add_item(ui.TextDisplay("**결제 수단 설정**"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"**계좌이체** = __{account_transfer}__"))
        container.add_item(ui.TextDisplay(f"**코인결제** = __{coin_payment}__"))
        container.add_item(ui.TextDisplay(f"**문상결제** = __{mun_sang}__"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("성공적으로 완료되었습니다."))
        self.add_item(container)

class BankAccountSetView(ui.LayoutView):
    def __init__(self, bank_name, account_holder, account_number):
        super().__init__(timeout=None)
        container = ui.Container()
        container.add_item(ui.TextDisplay("**정보 변경**"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"**은행명** = __{bank_name}__"))
        container.add_item(ui.TextDisplay(f"**예금주** = __{account_holder}__"))
        container.add_item(ui.TextDisplay(f"**계좌번호** = __{account_number}__"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("성공적으로 완료되었습니다."))
        self.add_item(container)

class ChargeRequestCompleteView(ui.LayoutView):
    def __init__(self, bank_name, account_holder, account_number, amount):
        super().__init__(timeout=None)
        container = ui.Container()
        container.add_item(ui.TextDisplay("**계좌이체 신청 완료**"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"은행명 = {bank_name}"))
        container.add_item(ui.TextDisplay(f"예금주 = {account_holder}"))
        container.add_item(ui.TextDisplay(f"계좌번호 = `{account_number}`"))
        container.add_item(ui.TextDisplay(f"")) # 한 줄 띄움
        container.add_item(ui.TextDisplay(f"입금 금액 = {amount}원"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("-# 5분안에 입금해주셔야 지충됩니다."))
        container.add_item(ui.TextDisplay("-# 입금자명 틀릴시 자충 인식 안 합니다."))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("자충 오류시 티켓 열고 이중창해주세요."))
        self.add_item(container)

class ChargeView(ui.LayoutView):
    def __init__(self, account_transfer, coin_payment, mun_sang):
        super().__init__(timeout=None)
        container = ui.Container()
        container.add_item(ui.TextDisplay("**결제수단 선택**"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("아래 원하시는 결제수단을 클릭해주세요"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        custom_emoji7 = PartialEmoji(name="TOSS", id=1423544803559342154) # TOSS 이모지
        custom_emoji8 = PartialEmoji(name="bitcoin", id=1423544805975265374) # 비트코인 이모지
        custom_emoji9 = PartialEmoji(name="1200x630wa", id=1423544804721164370) # 문화상품권 이모지

        # 버튼 생성 및 콜백 연결
        account_button = None
        if account_transfer == "지원":
            account_button = ui.Button(label="계좌이체", custom_id="pay_account", emoji=custom_emoji7, style=discord.ButtonStyle.primary)
            account_button.callback = self.account_button_callback  # 여기에 콜백 연결
        else:
            account_button = ui.Button(label="계좌이체", disabled=True, emoji=custom_emoji7, style=discord.ButtonStyle.secondary)

        coin_button = None
        if coin_payment == "지원":
            coin_button = ui.Button(label="코인결제", custom_id="pay_coin", emoji=custom_emoji8, style=discord.ButtonStyle.primary)
        else:
            coin_button = ui.Button(label="코인결제", disabled=True, emoji=custom_emoji8, style=discord.ButtonStyle.secondary)

        mun_sang_button = None
        if mun_sang == "지원":
            mun_sang_button = ui.Button(label="문상결제", custom_id="pay_munsang", emoji=custom_emoji9, style=discord.ButtonStyle.primary)
        else:
            mun_sang_button = ui.Button(label="문상결제", disabled=True, emoji=custom_emoji9, style=discord.ButtonStyle.secondary)

        action_row = ui.ActionRow(account_button, coin_button, mun_sang_button)
        container.add_item(action_row)
        
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        supported = []
        if account_transfer == "지원":
            supported.append("계좌이체")
        if coin_payment == "지원":
            supported.append("코인결제")
        if mun_sang == "지원":
            supported.append("문상결제")

        supported_text = ", ".join(supported) if supported else "없음"
        container.add_item(ui.TextDisplay(f"결제가능한 서비스 = {supported_text}"))
        self.add_item(container)
    
    # 계좌이체 버튼 콜백 함수 추가
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


class UserInfoView(ui.LayoutView):
    def __init__(self, user_name, balance, total_amount, transaction_count):
        super().__init__(timeout=None)
        container = ui.Container()
        container.add_item(ui.TextDisplay(f"**{user_name}님 정보**"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"**남은 금액** = __{balance}원__"))
        container.add_item(ui.TextDisplay(f"**누적 금액** = __{total_amount}원__"))
        container.add_item(ui.TextDisplay(f"**거래 횟수** = __{transaction_count}번__"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("항상 이용해주셔서 감사합니다."))
        self.add_item(container)

class NoticeView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        container = ui.Container()
        container.add_item(ui.TextDisplay("**공지사항**"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("__3자 입금__할 시 법적 조치합니다\n충전 신청하고 잠수시 __자판기 이용금지__\n__오류__나 __버그__문의는 티켓 열어주세요"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("윈드마켓 / 로벅스 자판기 / 2025 / GMT+09:00"))
        self.add_item(container)

# 버튼 상호작용 오류 방지를 위한 뷰 저장소
# 이 딕셔너리에 View 객체를 참조하면 Python의 GC에 의해 제거되지 않아 오래된 메시지의 버튼도 작동 가능
active_views = {}

class MyLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        
        container = ui.Container(ui.TextDisplay(
            "**로벅스 자판기**\n아래 버튼을 눌러 이용해주세요\n자충 오류시 [문의 바로가기](http://discord.com/channels/1419200424636055592/1423477824865439884)"
        ))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        sessao = ui.Section(ui.TextDisplay("**로벅스 재고**\n-# 60초마다 갱신됩니다"), accessory=ui.Button(label="0로벅스", disabled=True))
        container.add_item(sessao)
        
        sessao2 = ui.Section(ui.TextDisplay("**총 판매량**\n-# 총 판매된 로벅스량"), accessory=ui.Button(label="0로벅스", disabled=True))
        container.add_item(sessao2)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        custom_emoji1 = PartialEmoji(name="emoji_5", id=1424003478275231916) # 공지사항 이모지
        custom_emoji2 = PartialEmoji(name="charge", id=1424003480007475281) # 충전 이모지
        custom_emoji3 = PartialEmoji(name="info", id=1424003482247237908) # 내 정보 이모지
        custom_emoji4 = PartialEmoji(name="category", id=1424003481240469615) # 구매 이모지

        button_1 = ui.Button(label="공지사항", custom_id="button_1", emoji=custom_emoji1)
        button_2 = ui.Button(label="충전", custom_id="button_2", emoji=custom_emoji2)
        button_3 = ui.Button(label="내 정보", custom_id="button_3", emoji=custom_emoji3)
        button_4 = ui.Button(label="구매", custom_id="button_4", emoji=custom_emoji4)

        linha = ui.ActionRow(button_1, button_2)
        linha2 = ui.ActionRow(button_3, button_4)

        container.add_item(linha)
        container.add_item(linha2)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("윈드마켓 / 로벅스 자판기 / 2025 / GMT+09:00"))

        self.add_item(container)

        button_1.callback = self.button_1_callback
        button_2.callback = self.button_2_callback
        button_3.callback = self.button_3_callback
        button_4.callback = self.button_4_callback

    async def button_1_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if not await check_vending_access(user_id):
            view = VendingBanView()
            await interaction.response.send_message(view=view, ephemeral=True)
            return

        view = NoticeView()
        await interaction.response.send_message(view=view, ephemeral=True)

    async def button_2_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if not await check_vending_access(user_id):
            view = VendingBanView()
            await interaction.response.send_message(view=view, ephemeral=True)
            return
        
        account, coin, mun_sang = get_payment_methods(user_id)
        view = ChargeView(account, coin, mun_sang)
        await interaction.response.send_message(view=view, ephemeral=True)

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

    async def button_4_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if not await check_vending_access(user_id):
            view = VendingBanView()
            await interaction.response.send_message(view=view, ephemeral=True)
            return

        await interaction.response.send_message("설정중...", ephemeral=True)

# Note: PaymentSelectionView 클래스는 ChargeView 내에서 직접 콜백을 처리하도록 수정했으므로 더 이상 필요하지 않습니다.

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
class AccountTransferModal(ui.Modal, title="계좌이체 신청"):
    def __init__(self, bank_name, account_holder, account_number):
        super().__init__()
        self.bank_name = bank_name
        self.account_holder = account_holder
        self.account_number = account_number

        self.depositor_name_input = ui.TextInput(label="입금자명 (한글 2~4글자)", style=discord.TextStyle.short, required=True, min_length=2, max_length=4)
        self.amount_input = ui.TextInput(label="금액", style=discord.TextStyle.short, required=True)
        self.add_item(self.depositor_name_input)
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        depositor_name = self.depositor_name_input.value
        amount_str = self.amount_input.value

        # 입금자명 검증 (2-4글자 한글만)
        if not (2 <= len(depositor_name) <= 4 and all('가' <= char <= '힣' for char in depositor_name)):
            await interaction.response.send_message("입금자명은 2~4글자 한글만 가능합니다.", ephemeral=True)
            return

        # 금액 검증
        try:
            amount = int(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("유효한 금액을 숫자로 입력해주세요.", ephemeral=True)
            return
        
        # 실제 충전 신청 로직
        user_id = str(interaction.user.id)
        # save_charge_request(user_id, depositor_name, amount) # 필요시 이 함수로 DB에 저장
        
        view = ChargeRequestCompleteView(self.bank_name, self.account_holder, self.account_number, amount)
        await interaction.response.send_message(view=view, ephemeral=True)


@bot.tree.command(name="버튼패널", description="로벅스 버튼 패널 표시하기")
async def button_panel(interaction: discord.Interaction):
    layout = MyLayout()
    # 뷰 보존을 위해 저장 (메시지 ID가 없는 경우를 대비하여 None 대신 "no_msg_id" 사용)
    # 봇 재시작 후에도 이전 메시지의 버튼을 다시 연결하기 위함 (Peristence)
    if interaction.message:
        message_id_key = str(interaction.message.id)
        active_views[message_id_key] = layout
    await interaction.response.send_message(view=layout)

@bot.tree.command(name="자판기_이용_설정", description="자판기 밴 설정 포함 대상 유저 옵션")
@discord.app_commands.describe(
    target_user="밴 상태를 설정할 유저를 선택하세요",
    ban_status="밴 여부 확인"
)
@discord.app_commands.choices(ban_status=[
    discord.app_commands.Choice(name='허용', value='x'),
    discord.app_commands.Choice(name='차단', value='o')
])
async def vending_machine_ban(interaction: discord.Interaction, target_user: discord.User, ban_status: discord.app_commands.Choice[str]):
    user_id = str(target_user.id)
    set_user_ban(user_id, ban_status.value)

    if ban_status.value == 'o':
        view = BanSetView(target_user.name)
        await interaction.response.send_message(view=view, ephemeral=True)
    else:
        view = UnbanSetView(target_user.name)
        await interaction.response.send_message(view=view, ephemeral=True)

@bot.tree.command(name="결제수단_설정", description="결제 수단 설정")
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


@bot.event
async def on_ready():
    print(f"로벅스 자판기 봇이 {bot.user}로 로그인했습니다.")
    try:
        # 봇이 켜질 때 이전에 남아있던 뷰들 다시 등록 시도 (Persistency)
        for view_key, view_obj in active_views.items():
            if view_key != "no_msg_id": # 메시지 ID가 실제 있는 경우만
                try:
                    message = await bot.get_channel(int(view_obj.message_id_channel)).fetch_message(int(view_key))
                    bot.add_view(view_obj, message_id=message.id)
                    print(f"View re-added for message {view_key}")
                except Exception as e:
                    print(f"Failed to re-add view for message {view_key}: {e}")
            else:
                # 'no_msg_id' 키로 저장된 뷰는 message_id가 없으므로 재추가하지 않습니다.
                # 이는 임시적인 뷰이거나, 메시지가 삭제되어 뷰를 찾을 수 없는 경우입니다.
                pass
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'슬래시 명령어 동기화 중 오류 발생.: {e}')

bot.run("토큰을_여기에_입력하세요")
