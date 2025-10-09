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
        return result[0]  # 'o' or 'x'
    return 'x'

def get_user_info(user_id):
    cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    if result:
        return result
    return None

async def check_vending_access(user_id):
    banned = get_user_ban(user_id)
    return banned != 'o'

# 밴 안내 컨테이너 뷰
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

# 버튼 오류 방지를 위한 뷰 저장소
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

        custom_emoji1 = PartialEmoji(name="emoji_5", id=1424003478275231916)
        custom_emoji2 = PartialEmoji(name="charge", id=1424003480007475281)
        custom_emoji3 = PartialEmoji(name="info", id=1424003482247237908)
        custom_emoji4 = PartialEmoji(name="category", id=1424003481240469615)

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

        # 각 버튼 콜백에 밴 체크 후 밴 시 제한 메시지 띄우기
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

        await interaction.response.send_message("설정중...", ephemeral=True)

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

@bot.tree.command(name="버튼패널", description="로벅스 버튼 패널 표시하기")
async def button_panel(interaction: discord.Interaction):
    layout = MyLayout()
    # 뷰 보존을 위해 저장
    active_views[interaction.message.id if interaction.message else "no_msg_id"] = layout
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

@bot.event
async def on_ready():
    print(f"로벅스 자판기 봇이 {bot.user}로 로그인했습니다.")
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'슬래시 명령어 동기화 중 오류 발생.: {e}')

bot.run("토큰을_여기에_입력하세요")
