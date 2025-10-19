import discord
from discord import PartialEmoji, ui, app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
from datetime import datetime
import sqlite3
import asyncio
from functools import partial
import re

# .env 파일 로드
load_dotenv()

# Discord 봇 설정
intents = discord.Intents.all()
command_prefix = "!"
bot = commands.Bot(command_prefix=command_prefix, intents=intents)

# --- 설정 변수 ---
# // TODO: 여기에 실제 알림 역할 ID를 입력하세요.
NOTIFICATION_ROLE_ID = 1429436071539773561 

# --- SQLite 데이터베이스 설정 ---
DB_PATH = "vending_machine.db"

# 데이터베이스 초기화 (새로운 테이블 추가)
def _init_sqlite():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    
    # users 테이블 (기존)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        balance INTEGER DEFAULT 0,
        total INTEGER DEFAULT 0,
        tx_count INTEGER DEFAULT 0,
        PRIMARY KEY (guild_id, user_id)
    )
    """)
    # transactions 테이블 (기존)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        tx_id TEXT PRIMARY KEY,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        type TEXT,
        note TEXT,
        created_at TEXT
    )
    """)
    # user_restrictions 테이블 (이용제한 기능용)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_restrictions (
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        is_banned INTEGER DEFAULT 0,
        PRIMARY KEY (guild_id, user_id)
    )
    """)
    # products 테이블 (제품 정보 저장용)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price INTEGER NOT NULL,
        emoji_name TEXT,
        emoji_id INTEGER,
        UNIQUE(guild_id, name)
    )
    """)
    # inventory 테이블 (재고 저장용)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        stock_content TEXT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products (product_id) ON DELETE CASCADE
    )
    """)
    conn.commit()
    conn.close()

# --- 비동기 DB 헬퍼 함수들 ---
# (기존 함수들은 그대로 유지하고, 새로운 기능에 필요한 함수들을 추가합니다)

async def run_db_query(query, params=(), fetch=None, loop=None):
    """범용 비동기 DB 쿼리 실행기"""
    if loop is None:
        loop = asyncio.get_running_loop()

    def db_operation():
        conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
        cur = conn.cursor()
        cur.execute(query, params)
        result = None
        if fetch == 'one':
            result = cur.fetchone()
        elif fetch == 'all':
            result = cur.fetchall()
        conn.commit()
        conn.close()
        return result

    return await loop.run_in_executor(None, db_operation)

# --- 기존 DB 함수 ---
async def init_db_async(loop=None):
    if loop is None:
        loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _init_sqlite)

async def record_transaction_sqlite(guild_id: int, user_id: int, amount: int, ttype: str = "거래", note: str = ""):
    tx_id = f"{int(datetime.utcnow().timestamp()*1000)}{user_id}"
    created_at = datetime.utcnow().isoformat(sep=' ', timespec='seconds')
    
    # 트랜잭션 기록
    await run_db_query(
        """INSERT OR REPLACE INTO transactions (tx_id, guild_id, user_id, amount, type, note, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (tx_id, guild_id, user_id, amount, ttype, note, created_at)
    )
    # 유저 정보 업데이트 (Upsert)
    await run_db_query(
        """INSERT INTO users (guild_id, user_id, balance, total, tx_count) VALUES (?, ?, ?, ?, 1)
           ON CONFLICT(guild_id, user_id) DO UPDATE SET
           balance = balance + excluded.balance,
           total = CASE WHEN excluded.total > 0 THEN total + excluded.total ELSE total END,
           tx_count = tx_count + 1""",
        (guild_id, user_id, amount, amount)
    )

async def get_user_info_sqlite(guild_id: int, user_id: int):
    row = await run_db_query(
        "SELECT balance, total, tx_count FROM users WHERE guild_id=? AND user_id=?",
        (guild_id, user_id), fetch='one'
    )
    if row:
        return {"balance": row[0], "total": row[1], "tx_count": row[2]}
    return {"balance": 0, "total": 0, "tx_count": 0}

async def get_recent_tx_sqlite(guild_id, user_id, limit=10):
    return await run_db_query(
        "SELECT tx_id, amount, type, note, created_at FROM transactions WHERE guild_id=? AND user_id=? ORDER BY created_at DESC LIMIT ?",
        (guild_id, user_id, limit), fetch='all'
    )

# --- 새로운 DB 함수 ---
async def set_user_restriction(guild_id: int, user_id: int, is_banned: bool):
    await run_db_query(
        """INSERT INTO user_restrictions (guild_id, user_id, is_banned) VALUES (?, ?, ?)
           ON CONFLICT(guild_id, user_id) DO UPDATE SET is_banned = excluded.is_banned""",
        (guild_id, user_id, 1 if is_banned else 0)
    )

async def is_user_banned(guild_id: int, user_id: int) -> bool:
    result = await run_db_query(
        "SELECT is_banned FROM user_restrictions WHERE guild_id=? AND user_id=?",
        (guild_id, user_id), fetch='one'
    )
    return result[0] == 1 if result else False

async def add_product(guild_id, name, category, price, emoji_name, emoji_id):
    await run_db_query(
        "INSERT INTO products (guild_id, name, category, price, emoji_name, emoji_id) VALUES (?, ?, ?, ?, ?, ?)",
        (guild_id, name, category, price, emoji_name, emoji_id)
    )

async def delete_product(product_id: int):
    await run_db_query("DELETE FROM products WHERE product_id=?", (product_id,))

async def get_all_products(guild_id: int):
    return await run_db_query("SELECT product_id, name, category, price, emoji_name, emoji_id FROM products WHERE guild_id=?", (guild_id,), fetch='all')

async def get_product_by_id(product_id: int):
    return await run_db_query("SELECT name, price FROM products WHERE product_id=?", (product_id,), fetch='one')

async def add_stock(product_id: int, stock_list: list):
    params = [(product_id, content) for content in stock_list]
    
    def db_op_many():
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cur = conn.cursor()
        cur.executemany("INSERT INTO inventory (product_id, stock_content) VALUES (?, ?)", params)
        conn.commit()
        conn.close()
    
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, db_op_many)


async def get_stock_count(product_id: int):
    result = await run_db_query("SELECT COUNT(*) FROM inventory WHERE product_id=?", (product_id,), fetch='one')
    return result[0] if result else 0

async def get_categories(guild_id: int):
    return await run_db_query("SELECT DISTINCT category FROM products WHERE guild_id=?", (guild_id,), fetch='all')

async def get_products_by_category(guild_id: int, category: str):
    return await run_db_query("SELECT product_id, name, price, emoji_name, emoji_id FROM products WHERE guild_id=? AND category=?", (guild_id, category), fetch='all')

async def purchase_items(guild_id: int, user_id: int, product_id: int, quantity: int):
    """구매 로직을 처리하는 트랜잭션 함수"""
    product_info = await get_product_by_id(product_id)
    if not product_info:
        return "PRODUCT_NOT_FOUND", None
    
    product_name, price = product_info
    total_cost = price * quantity

    user_info = await get_user_info_sqlite(guild_id, user_id)
    if user_info['balance'] < total_cost:
        return "INSUFFICIENT_FUNDS", None

    # 재고 확인 및 구매 (트랜잭션)
    def db_transaction():
        conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None) # Auto-commit mode
        cur = conn.cursor()
        try:
            cur.execute("BEGIN")
            # 재고 확인 및 가져오기
            cur.execute("SELECT stock_id, stock_content FROM inventory WHERE product_id=? LIMIT ?", (product_id, quantity))
            items_to_purchase = cur.fetchall()

            if len(items_to_purchase) < quantity:
                conn.rollback()
                return "OUT_OF_STOCK", None

            # 재고 삭제
            ids_to_delete = tuple(item[0] for item in items_to_purchase)
            cur.execute(f"DELETE FROM inventory WHERE stock_id IN ({','.join('?' for _ in ids_to_delete)})", ids_to_delete)
            
            conn.commit()
            return "SUCCESS", [item[1] for item in items_to_purchase]
        except Exception as e:
            conn.rollback()
            print(f"Purchase Transaction Error: {e}")
            return "DB_ERROR", None
        finally:
            conn.close()
            
    loop = asyncio.get_running_loop()
    status, purchased_items = await loop.run_in_executor(None, db_transaction)

    if status == "SUCCESS":
        # 금액 차감
        await record_transaction_sqlite(guild_id, user_id, -total_cost, "구매", f"{product_name} x{quantity}")
    
    return status, purchased_items


# --- 유틸리티 함수 ---
def parse_custom_emoji(emoji_str: str):
    """<:name:id> 또는 <a:name:id> 형식의 커스텀 이모지를 파싱"""
    match = re.match(r'<a?:(\w+):(\d+)>', emoji_str.strip())
    if match:
        return match.group(1), int(match.group(2))
    return None, None


# --- 에러 및 확인 메시지용 컨테이너 ---
def create_ephemeral_container(title, message):
    view = ui.LayoutView()
    container = ui.Container(ui.TextDisplay(title))
    container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(message))
    view.add_item(container)
    return view


# --- 구매 플로우 UI ---
class PurchaseQuantityModal(ui.Modal):
    def __init__(self, product_id, product_name, price, stock_count):
        super().__init__(title=f"{product_name} 구매")
        self.product_id = product_id
        self.product_name = product_name
        self.price = price
        self.stock_count = stock_count

        self.quantity_input = ui.TextInput(
            label="구매 수량",
            placeholder=f"1부터 {stock_count} 사이의 숫자를 입력하세요."
        )
        self.add_item(self.quantity_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            quantity = int(self.quantity_input.value)
            if not (1 <= quantity <= self.stock_count):
                raise ValueError
        except (ValueError, TypeError):
            await interaction.response.send_message("올바른 수량을 입력해주세요.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        total_cost = self.price * quantity
        status, purchased_items = await purchase_items(interaction.guild_id, interaction.user.id, self.product_id, quantity)

        if status == "SUCCESS":
            # 성공 메시지 (채널)
            success_view = ui.LayoutView()
            c = ui.Container(ui.TextDisplay("✅ 구매 성공"))
            c.add_item(ui.Separator())
            c.add_item(ui.TextDisplay(f"제품 이름 = __{self.product_name}__"))
            c.add_item(ui.TextDisplay(f"구매 개수 = __{quantity}__개"))
            c.add_item(ui.TextDisplay(f"차감 금액 = __{total_cost}__원"))
            c.add_item(ui.Separator())
            c.add_item(ui.TextDisplay("성공적으로 구매 완료되었습니다."))
            success_view.add_item(c)
            await interaction.edit_original_response(view=success_view)

            # DM으로 제품 정보 발송
            try:
                dm_view = ui.LayoutView()
                dm_c = ui.Container(ui.TextDisplay("📦 구매 제품"))
                dm_c.add_item(ui.Separator())
                dm_c.add_item(ui.TextDisplay("구매한 제품 목록:"))
                dm_c.add_item(ui.TextDisplay("\n".join(purchased_items)))
                dm_c.add_item(ui.Separator())
                dm_c.add_item(ui.TextDisplay("구매해주셔서 감사합니다."))
                dm_view.add_item(dm_c)
                await interaction.user.send(view=dm_view)
            except discord.Forbidden:
                await interaction.followup.send("DM을 보낼 수 없습니다. DM 설정을 확인해주세요.", ephemeral=True)
        
        else:
            error_messages = {
                "INSUFFICIENT_FUNDS": "잔액이 부족합니다.",
                "OUT_OF_STOCK": "재고가 부족합니다.",
                "PRODUCT_NOT_FOUND": "제품을 찾을 수 없습니다.",
                "DB_ERROR": "구매 처리 중 오류가 발생했습니다. 관리자에게 문의하세요."
            }
            await interaction.edit_original_response(view=create_ephemeral_container("오류", error_messages.get(status, "알 수 없는 오류")))


class ProductSelect(ui.Select):
    def __init__(self, products):
        options = []
        for p_id, name, price, e_name, e_id in products:
            emoji = PartialEmoji(name=e_name, id=e_id) if e_id else None
            options.append(ui.SelectOption(label=f"{name} ({price}원)", value=str(p_id), emoji=emoji))
        super().__init__(placeholder="원하시는 제품을 선택해주세요", options=options, min_values=1, max_values=1)
    
    async def callback(self, interaction: discord.Interaction):
        product_id = int(self.values[0])
        stock_count = await get_stock_count(product_id)

        if stock_count == 0:
            await interaction.response.send_message("해당 제품은 현재 재고가 없습니다.", ephemeral=True)
            return
            
        product_info = await get_product_by_id(product_id)
        if not product_info:
            await interaction.response.send_message("제품 정보를 불러올 수 없습니다.", ephemeral=True)
            return
        
        product_name, price = product_info
        modal = PurchaseQuantityModal(product_id, product_name, price, stock_count)
        await interaction.response.send_modal(modal)


class CategorySelect(ui.Select):
    def __init__(self, categories):
        options = [ui.SelectOption(label=cat[0], value=cat[0]) for cat in categories]
        super().__init__(placeholder="원하시는 카테고리를 선택해주세요", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        products = await get_products_by_category(interaction.guild_id, category)

        if not products:
            await interaction.response.edit_message(view=create_ephemeral_container("알림", "해당 카테고리에 제품이 없습니다."))
            return

        view = ui.LayoutView()
        container = ui.Container(ui.TextDisplay("📦 제품"))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay("원하시는 제품을 선택해주세요"))
        view.add_item(container)
        view.add_item(ProductSelect(products))
        await interaction.response.edit_message(view=view)


# --- 자판기 메인 UI ---
class MyLayoutVending(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        self.c = ui.Container(ui.TextDisplay("24시간 OTT 자판기\n-# 버튼을 눌러 이용해주세요 !"))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # ... (총 판매 금액 부분은 동적 업데이트가 복잡하여 일단 제외)

        custom_emoji1 = PartialEmoji(name="3", id=1426934636428394678) # 충전
        custom_emoji2 = PartialEmoji(name="6", id=1426943544928505886) # 입고알림
        custom_emoji3 = PartialEmoji(name="5", id=1426936503635939428) # 내 정보
        custom_emoji4 = PartialEmoji(name="4", id=1426936460149395598) # 구매

        button_1 = ui.Button(label="충전", custom_id="charge_button", emoji=custom_emoji1)
        button_2 = ui.Button(label="입고알림", custom_id="notification_button", emoji=custom_emoji2)
        button_3 = ui.Button(label="내 정보", custom_id="my_info_button", emoji=custom_emoji3)
        button_4 = ui.Button(label="구매", custom_id="purchase_button", emoji=custom_emoji4)

        linha = ui.ActionRow(button_1, button_2)
        linha2 = ui.ActionRow(button_3, button_4)

        self.c.add_item(linha)
        self.c.add_item(linha2)
        self.add_item(self.c)
        
        # 콜백 연결
        button_2.callback = self.on_notification_click
        button_3.callback = self.on_my_info_click
        button_4.callback = self.on_purchase_click
        # '충전' 버튼은 별도 로직이 필요하여 일단 비워둡니다.

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """모든 상호작용 전에 이용 제한 여부를 확인합니다."""
        if await is_user_banned(interaction.guild_id, interaction.user.id):
            banned_view = create_ephemeral_container(
                "🚫 사용불가", 
                "현재 자판기 이용이 제한되었습니다\n자세한 이유를 알고 싶으면 문의해주세요"
            )
            await interaction.response.send_message(view=banned_view, ephemeral=True)
            return False
        return True

    async def on_notification_click(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(NOTIFICATION_ROLE_ID)
        if not role:
            await interaction.response.send_message("알림 역할이 서버에 존재하지 않습니다. 관리자에게 문의하세요.", ephemeral=True)
            return

        member = interaction.user
        container_title = ""
        container_message = ""

        if role in member.roles:
            await member.remove_roles(role)
            container_title = "🔕 알림받기 취소"
            container_message = "이제 재고 알림을 받지 않습니다."
        else:
            await member.add_roles(role)
            container_title = "🔔 알림받기"
            container_message = "이제 재고가 추가될 때마다 알림을 받으실 수 있습니다.\n버튼을 한번 더 누르시면 알림이 취소됩니다."
        
        view = create_ephemeral_container(container_title, container_message)
        await interaction.response.send_message(view=view, ephemeral=True)

    async def on_my_info_click(self, interaction: discord.Interaction):
        # ... (기존 '내 정보' 코드와 동일, 생략)
        # 단, interaction_check가 먼저 실행되므로 여기서는 로직만 구현
        member = interaction.user
        guild = interaction.guild

        user_info = await get_user_info_sqlite(guild.id, member.id)
        balance = user_info.get("balance", 0)
        total = user_info.get("total", 0)
        tx_count = user_info.get("tx_count", 0)

        ephemeral_view = ui.LayoutView(timeout=120)
        info_container = ui.Container(ui.TextDisplay(f"{member.display_name}님 정보"))
        info_container.add_item(ui.Separator())
        info_container.add_item(ui.TextDisplay(f"보유 금액 = __{balance}__원"))
        info_container.add_item(ui.TextDisplay(f"누적 금액 = __{total}__원"))
        info_container.add_item(ui.TextDisplay(f"거래 횟수 = __{tx_count}__번"))
        ephemeral_view.add_item(info_container)
        
        await interaction.response.send_message(view=ephemeral_view, ephemeral=True)

    async def on_purchase_click(self, interaction: discord.Interaction):
        categories = await get_categories(interaction.guild_id)
        if not categories:
            await interaction.response.send_message(view=create_ephemeral_container("알림", "현재 판매중인 상품이 없습니다."), ephemeral=True)
            return

        view = ui.LayoutView()
        container = ui.Container(ui.TextDisplay("🛒 카테고리"))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay("원하시는 카테고리를 선택해주세요"))
        view.add_item(container)
        view.add_item(CategorySelect(categories))

        await interaction.response.send_message(view=view, ephemeral=True)

# --- 봇 이벤트 ---
@bot.event
async def on_ready():
    try:
        await init_db_async()
        print("✅ SQLite DB 초기화 완료")
    except Exception as e:
        print(f"❌ SQLite 초기화 중 오류: {e}")

    print(f'✅ {bot.user}로 로그인했습니다.')
    try:
        synced = await bot.tree.sync()
        print(f'✅ {len(synced)}개의 슬래시 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'❌ 슬래시 명령어 동기화 중 오류 발생: {e}')

# --- 슬래시 명령어 ---
@bot.tree.command(name="자판기패널", description="자판기 패널을 표시합니다")
@app_commands.checks.has_permissions(administrator=True)
async def panel_vending(interaction: discord.Interaction):
    layout = MyLayoutVending()
    await interaction.response.send_message(view=layout, ephemeral=False)

@bot.tree.command(name="금액관리", description="유저의 금액을 관리합니다.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(유저="금액을 변경할 유저", 종류="추가 또는 차감", 금액="변경할 금액")
async def manage_balance(interaction: discord.Interaction, 유저: discord.Member, 종류: str, 금액: int):
    if 종류 not in ["추가", "차감"]:
        await interaction.response.send_message("종류는 '추가' 또는 '차감'만 가능합니다.", ephemeral=True)
        return
    if 금액 <= 0:
        await interaction.response.send_message("금액은 0보다 커야 합니다.", ephemeral=True)
        return

    amount_to_change = 금액 if 종류 == "추가" else -금액
    note = f"관리자({interaction.user.name})에 의한 금액 {종류}"
    
    await record_transaction_sqlite(interaction.guild_id, 유저.id, amount_to_change, "관리자", note)
    
    new_info = await get_user_info_sqlite(interaction.guild_id, 유저.id)
    new_balance = new_info['balance']

    title = f"💰 금액 {종류}"
    view = ui.LayoutView()
    c = ui.Container(ui.TextDisplay(title))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(f"유저 = __{유저.display_name}__님"))
    c.add_item(ui.TextDisplay(f"{종류} 금액 = __{금액}__원"))
    c.add_item(ui.TextDisplay(f"{종류} 후 금액 = __{new_balance}__원"))
    view.add_item(c)

    await interaction.response.send_message(view=view, ephemeral=True)

@bot.tree.command(name="이용제한", description="유저의 자판기 이용을 제한하거나 허용합니다.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(유저="상태를 변경할 유저", 상태="사용 가능 또는 사용 불가")
async def manage_restriction(interaction: discord.Interaction, 유저: discord.Member, 상태: str):
    if 상태 not in ["사용", "불가"]:
        await interaction.response.send_message("상태는 '사용' 또는 '불가'만 가능합니다.", ephemeral=True)
        return

    is_banned = (상태 == "불가")
    await set_user_restriction(interaction.guild_id, 유저.id, is_banned)
    
    status_text = "사용 불가" if is_banned else "사용 가능"

    view = ui.LayoutView()
    c = ui.Container(ui.TextDisplay("🚫 자판기 사용 여부"))
    c.add_item(ui.Separator())
    c.add_item(ui.TextDisplay(f"유저 = {유저.mention}"))
    c.add_item(ui.TextDisplay(f"사용 가능 여부 = __{status_text}__"))
    view.add_item(c)

    await interaction.response.send_message(view=view, ephemeral=True)

# --- 제품 설정 모달 ---
class ProductModal(ui.Modal):
    def __init__(self, title="제품 추가"):
        super().__init__(title=title)
        self.emoji_input = ui.TextInput(label="이모지", placeholder="서버의 커스텀 이모지 또는 유니코드 이모지")
        self.name_input = ui.TextInput(label="제품 이름", placeholder="예: 넷플릭스 1개월")
        self.category_input = ui.TextInput(label="카테고리", placeholder="예: OTT, 게임")
        self.price_input = ui.TextInput(label="가격 (숫자만)", placeholder="예: 3000")
        
        self.add_item(self.emoji_input)
        self.add_item(self.name_input)
        self.add_item(self.category_input)
        self.add_item(self.price_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            price = int(self.price_input.value)
        except ValueError:
            await interaction.response.send_message("가격은 숫자로만 입력해주세요.", ephemeral=True)
            return

        emoji_str = self.emoji_input.value
        e_name, e_id = parse_custom_emoji(emoji_str)
        
        if not e_name and not e_id: # 커스텀 이모지가 아니면 그냥 텍스트로 저장
            e_name = emoji_str
            e_id = None
            
        product_name = self.name_input.value
        category = self.category_input.value
        
        try:
            await add_product(interaction.guild_id, product_name, category, price, e_name, e_id)
            
            view = ui.LayoutView()
            c = ui.Container(ui.TextDisplay("✅ 제품 추가"))
            c.add_item(ui.Separator())
            c.add_item(ui.TextDisplay(f"이모지 = {emoji_str}"))
            c.add_item(ui.TextDisplay(f"제품 이름 = __{product_name}__"))
            c.add_item(ui.TextDisplay(f"카테고리 = __{category}__"))
            c.add_item(ui.TextDisplay(f"가격 = __{price}__원"))
            view.add_item(c)

            await interaction.response.send_message(view=view, ephemeral=True)

        except sqlite3.IntegrityError:
            await interaction.response.send_message(f"오류: 이미 '{product_name}' 이름의 제품이 존재합니다.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"제품 추가 중 오류 발생: {e}", ephemeral=True)

# --- 제품 설정 드롭다운 ---
class ProductManagementSelect(ui.Select):
    def __init__(self):
        options = [
            ui.SelectOption(label="제품 추가", value="add_product", emoji="➕"),
            ui.SelectOption(label="제품 삭제", value="delete_product", emoji="➖"),
        ]
        super().__init__(placeholder="아래 드롭다운을 눌러 제품을 설정해주세요", options=options)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        if choice == "add_product":
            await interaction.response.send_modal(ProductModal())
        elif choice == "delete_product":
            products = await get_all_products(interaction.guild_id)
            if not products:
                await interaction.response.send_message("삭제할 제품이 없습니다.", ephemeral=True)
                return

            view = ui.LayoutView()
            view.add_item(ProductDeleteSelect(products))
            await interaction.response.send_message("삭제할 제품을 선택해주세요.", view=view, ephemeral=True)

class ProductDeleteSelect(ui.Select):
    def __init__(self, products):
        options = []
        for p_id, name, cat, price, e_name, e_id in products:
            emoji = PartialEmoji(name=e_name, id=e_id) if e_id else None
            options.append(ui.SelectOption(label=f"[{cat}] {name}", value=str(p_id), emoji=emoji))
        super().__init__(placeholder="삭제할 제품 선택", options=options)

    async def callback(self, interaction: discord.Interaction):
        product_id = int(self.values[0])
        await delete_product(product_id)
        await interaction.response.edit_message(content="선택한 제품이 삭제되었습니다.", view=None)

@bot.tree.command(name="제품설정", description="자판기의 제품을 추가하거나 삭제합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def product_settings(interaction: discord.Interaction):
    view = ui.LayoutView()
    container = ui.Container(ui.TextDisplay("⚙️ 제품 설정"))
    container.add_item(ui.Separator())
    container.add_item(ui.TextDisplay("아래 드롭다운을 눌러 제품을 설정해주세요"))
    view.add_item(container)
    view.add_item(ProductManagementSelect())
    await interaction.response.send_message(view=view, ephemeral=True)

# --- 재고 추가 ---
class StockAddModal(ui.Modal):
    def __init__(self, product_id, product_name):
        super().__init__(title=f"{product_name} 재고 추가")
        self.product_id = product_id
        self.product_name = product_name
        self.stock_input = ui.TextInput(
            label="추가할 재고 (한 줄에 하나씩)",
            style=discord.TextStyle.paragraph,
            placeholder="제품코드1\n제품코드2\n제품코드3"
        )
        self.add_item(self.stock_input)

    async def on_submit(self, interaction: discord.Interaction):
        stock_list = [line.strip() for line in self.stock_input.value.split('\n') if line.strip()]
        if not stock_list:
            await interaction.response.send_message("추가할 재고 내용이 없습니다.", ephemeral=True)
            return
        
        await add_stock(self.product_id, stock_list)

        view = ui.LayoutView()
        c = ui.Container(ui.TextDisplay("📦 재고 추가 완료"))
        c.add_item(ui.Separator())
        c.add_item(ui.TextDisplay(f"제품 이름 = __{self.product_name}__"))
        c.add_item(ui.TextDisplay(f"추가된 재고 개수 = __{len(stock_list)}__개"))
        view.add_item(c)
        await interaction.response.send_message(view=view, ephemeral=True)
        
        # 알림 역할 멘션
        notif_role = interaction.guild.get_role(NOTIFICATION_ROLE_ID)
        if notif_role:
            await interaction.channel.send(f"{notif_role.mention} **{self.product_name}** 제품의 재고가 추가되었습니다!")


class StockAddSelect(ui.Select):
    def __init__(self, products):
        options = []
        for p_id, name, _, _, e_name, e_id in products:
            emoji = PartialEmoji(name=e_name, id=e_id) if e_id else None
            options.append(ui.SelectOption(label=name, value=str(p_id), emoji=emoji))
        super().__init__(placeholder="재고를 추가할 제품 선택", options=options)

    async def callback(self, interaction: discord.Interaction):
        product_id = int(self.values[0])
        product_name = next((p[1] for p in self.options if int(p.value) == product_id), "알 수 없는 제품")
        await interaction.response.send_modal(StockAddModal(product_id, product_name))

@bot.tree.command(name="재고추가", description="제품의 재고를 추가합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def add_stock_command(interaction: discord.Interaction):
    products = await get_all_products(interaction.guild_id)
    if not products:
        await interaction.response.send_message("먼저 제품을 추가해주세요.", ephemeral=True)
        return

    view = ui.LayoutView()
    container = ui.Container(ui.TextDisplay("➕ 재고 추가"))
    container.add_item(ui.Separator())
    container.add_item(ui.TextDisplay("드롭다운을 눌러 재고를 추가할 제품을 선택해주세요."))
    view.add_item(container)
    view.add_item(StockAddSelect(products))

    await interaction.response.send_message(view=view, ephemeral=True)


# --- 봇 실행 ---
# // TODO: 여기에 봇 토큰을 입력하세요.
bot.run("YOUR_BOT_TOKEN_HERE")
