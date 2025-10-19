# main.py (튜어오오오옹님 요청 반영: shelve 기반, 구매 오류 수정, 드롭다운/모달 정리)
import discord
from discord import PartialEmoji, ui, app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
from datetime import datetime
import asyncio
from functools import partial
import shelve
import threading

# .env 로드
load_dotenv()

intents = discord.Intents.all()
command_prefix = "!"
bot = commands.Bot(command_prefix=command_prefix, intents=intents)

# 환경 설정
NOTIFICATION_ROLE_ID = 1429436071539773561  # 본인 서버에 맞게 수정
SHELVE_PATH = "vending_shelve.db"  # shelve 파일(실제로는 여러 파일로 생성될 수 있음)
_shelve_lock = threading.Lock()    # shelve 접근 동기화 (간단한 잠금)

# ------------------ shelve 헬퍼 (블로킹이므로 executor 사용) ------------------
def _shelve_get(key):
    with _shelve_lock:
        with shelve.open(SHELVE_PATH) as db:
            return db.get(key)

def _shelve_set(key, value):
    with _shelve_lock:
        with shelve.open(SHELVE_PATH, writeback=True) as db:
            db[key] = value

def _shelve_delete(key):
    with _shelve_lock:
        with shelve.open(SHELVE_PATH, writeback=True) as db:
            if key in db:
                del db[key]

async def shelve_get(key):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_shelve_get, key))

async def shelve_set(key, value):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_shelve_set, key, value))

async def shelve_delete(key):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_shelve_delete, key))

# ------------------ 데이터 모델(간단) ------------------
# keys:
# - "users:{guild_id}:{user_id}" -> dict {balance,total,tx_count,can_use}
# - "transactions:{guild_id}:{user_id}" -> list of tx dicts (최신 우선)
# - "products:{guild_id}" -> dict product_id(str) -> product dict {name,category,price,emoji_name,emoji_id}
# - "inventory:{guild_id}:{product_id}" -> list of stock strings
# - "subscriptions:{guild_id}:{user_id}" -> bool (notify)
# - "bans:{guild_id}:{user_id}" -> bool (banned)

# ------------------ 유틸 함수 ------------------
def _user_key(guild_id, user_id): return f"users:{guild_id}:{user_id}"
def _tx_key(guild_id, user_id): return f"transactions:{guild_id}:{user_id}"
def _products_key(guild_id): return f"products:{guild_id}"
def _inventory_key(guild_id, product_id): return f"inventory:{guild_id}:{product_id}"
def _sub_key(guild_id, user_id): return f"subscriptions:{guild_id}:{user_id}"
def _ban_key(guild_id, user_id): return f"bans:{guild_id}:{user_id}"

# ------------------ DB 작업 함수 (shelve 기반) ------------------
async def init_db_async():
    # 초기화: 키가 없으면 빈 구조체 생성
    # (별도 작업 필요 없음 — lazy 생성)
    return

async def record_transaction(guild_id: int, user_id: int, amount: int, ttype: str = "거래", note: str = ""):
    # 트랜잭션을 저장하고 유저 잔액 업데이트
    user_key = _user_key(guild_id, user_id)
    tx_key = _tx_key(guild_id, user_id)

    user = await shelve_get(user_key) or {"balance":0,"total":0,"tx_count":0,"can_use":1}
    now = datetime.utcnow().isoformat(sep=' ', timespec='seconds')
    tx = {"_id": f"{int(datetime.utcnow().timestamp()*1000)}_{user_id}", "amount": amount, "type": ttype, "note": note, "created_at": now}

    # prepend to transactions
    txs = await shelve_get(tx_key) or []
    txs.insert(0, tx)
    await shelve_set(tx_key, txs[:100])  # 최근 100건만 보관

    # update user
    user["balance"] = user.get("balance",0) + amount
    if amount > 0:
        user["total"] = user.get("total",0) + amount
    user["tx_count"] = user.get("tx_count",0) + 1
    await shelve_set(user_key, user)

async def get_user_info(guild_id: int, user_id: int):
    user = await shelve_get(_user_key(guild_id, user_id))
    if user:
        return user
    return {"balance":0,"total":0,"tx_count":0,"can_use":1}

async def get_recent_transactions(guild_id:int, user_id:int, limit=10):
    txs = await shelve_get(_tx_key(guild_id, user_id)) or []
    return txs[:limit]

# products
async def add_product_shelf(guild_id, name, category, price, emoji_name=None, emoji_id=None):
    key = _products_key(guild_id)
    prods = await shelve_get(key) or {}
    # product_id as timestamp string
    pid = f"{int(datetime.utcnow().timestamp()*1000)}"
    # unique name check
    for v in prods.values():
        if v.get("name") == name:
            raise ValueError("DUPLICATE_NAME")
    prods[pid] = {"name":name,"category":category,"price":int(price),"emoji_name":emoji_name,"emoji_id":emoji_id}
    await shelve_set(key, prods)
    return pid

async def remove_product_shelf(guild_id, product_id):
    key = _products_key(guild_id)
    prods = await shelve_get(key) or {}
    if product_id in prods:
        del prods[product_id]
        await shelve_set(key, prods)
    # also remove inventory
    inv_key = _inventory_key(guild_id, product_id)
    await shelve_delete(inv_key)

async def get_all_products_shelf(guild_id):
    prods = await shelve_get(_products_key(guild_id)) or {}
    # return list of tuples like (product_id, name, category, price, emoji_name, emoji_id)
    return [(pid, d["name"], d["category"], d["price"], d.get("emoji_name"), d.get("emoji_id")) for pid,d in prods.items()]

async def get_product_by_id_shelf(guild_id, product_id):
    prods = await shelve_get(_products_key(guild_id)) or {}
    p = prods.get(str(product_id))
    if p: return (p["name"], p["price"])
    return None

# inventory
async def add_stock_shelf(guild_id, product_id, stock_list):
    key = _inventory_key(guild_id, product_id)
    inv = await shelve_get(key) or []
    inv.extend(stock_list)
    await shelve_set(key, inv)

async def get_stock_count_shelf(guild_id, product_id):
    inv = await shelve_get(_inventory_key(guild_id, product_id)) or []
    return len(inv)

async def pop_stock_items_shelf(guild_id, product_id, quantity):
    key = _inventory_key(guild_id, product_id)
    inv = await shelve_get(key) or []
    if len(inv) < quantity:
        return None
    items = inv[:quantity]
    remaining = inv[quantity:]
    await shelve_set(key, remaining)
    return items

# subscriptions & bans
async def toggle_subscription_shelf(guild_id, user_id):
    key = _sub_key(guild_id, user_id)
    cur = await shelve_get(key)
    new = not bool(cur)
    await shelve_set(key, new)
    return new

async def set_ban_shelf(guild_id, user_id, banned:bool):
    await shelve_set(_ban_key(guild_id, user_id), bool(banned))
    # also set user can_use flag
    user = await shelve_get(_user_key(guild_id, user_id)) or {"balance":0,"total":0,"tx_count":0,"can_use":1}
    user["can_use"] = 0 if banned else 1
    await shelve_set(_user_key(guild_id, user_id), user)

async def is_banned_shelf(guild_id, user_id):
    v = await shelve_get(_ban_key(guild_id, user_id))
    return bool(v)

# transaction-like purchase using shelve inventory
async def purchase_items_shelf(guild_id, user_id, product_id, quantity):
    # check product
    prod = await get_product_by_id_shelf(guild_id, product_id)
    if not prod:
        return "PRODUCT_NOT_FOUND", None
    product_name, price = prod
    total_cost = price * quantity
    user = await get_user_info(guild_id, user_id)
    if user["balance"] < total_cost:
        return "INSUFFICIENT_FUNDS", None
    # pop stock
    items = await pop_stock_items_shelf(guild_id, product_id, quantity)
    if items is None:
        return "OUT_OF_STOCK", None
    # deduct money and record tx
    await record_transaction(guild_id, user_id, -total_cost, "구매", f"{product_name} x{quantity}")
    return "SUCCESS", items

# ------------------ UI / 상호작용 (기존 로직 유지하되 shelve 함수 사용) ------------------

def create_ephemeral_container(title, message):
    view = ui.LayoutView()
    container = ui.Container(ui.TextDisplay(title))
    container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(message))
    view.add_item(container)
    return view

class PurchaseQuantityModal(ui.Modal):
    def __init__(self, guild_id, product_id, product_name, price, stock_count):
        super().__init__(title=f"{product_name} 구매")
        self.guild_id = guild_id
        self.product_id = product_id
        self.product_name = product_name
        self.price = price
        self.stock_count = stock_count
        # 설명 제거: 단순 입력
        self.quantity_input = ui.TextInput(label="구매 수량")
        self.add_item(self.quantity_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            quantity = int(self.quantity_input.value)
            if not (1 <= quantity <= self.stock_count):
                raise ValueError
        except:
            await interaction.response.send_message("올바른 수량을 입력해주세요.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        status, items = await purchase_items_shelf(self.guild_id, interaction.user.id, self.product_id, quantity)
        if status == "SUCCESS":
            # 성공 컨테이너
            success_view = ui.LayoutView()
            c = ui.Container(ui.TextDisplay("**구매 성공**"))
            c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(ui.TextDisplay(f"**제품 이름** = {self.product_name}"))
            c.add_item(ui.TextDisplay(f"**구매 개수** = {quantity}"))
            c.add_item(ui.TextDisplay(f"**차감 금액** = {self.price*quantity}원"))
            c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(ui.TextDisplay("성공적으로 구매 완료되었습니다."))
            success_view.add_item(c)
            # interaction.edit_original_response is only valid if a message was created earlier; we deferred -> use followup
            await interaction.followup.send(view=success_view, ephemeral=True)

            # DM
            try:
                dm_view = ui.LayoutView()
                dm_c = ui.Container(ui.TextDisplay("구매 제품"))
                dm_c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                dm_c.add_item(ui.TextDisplay("\n".join(items)))
                dm_c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                dm_view.add_item(dm_c)
                await interaction.user.send(view=dm_view)
            except discord.Forbidden:
                pass
        else:
            msg = {
                "INSUFFICIENT_FUNDS":"잔액이 부족합니다.",
                "OUT_OF_STOCK":"재고가 부족합니다.",
                "PRODUCT_NOT_FOUND":"제품을 찾을 수 없습니다.",
                "DB_ERROR":"구매 처리 중 오류가 발생했습니다."
            }.get(status, "알 수 없는 오류")
            await interaction.followup.send(view=create_ephemeral_container("오류", msg), ephemeral=True)

class ProductSelect(ui.Select):
    def __init__(self, guild_id, products):
        options = []
        for p_id, name, price, e_name, e_id in products:
            options.append(discord.SelectOption(label=f"{name} ({price}원)", value=str(p_id)))
        super().__init__(placeholder="원하시는 제품을 선택해주세요", options=options, min_values=1, max_values=1)
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        product_id = int(self.values[0])
        stock_count = await get_stock_count_shelf(interaction.guild_id, product_id)
        if stock_count == 0:
            await interaction.response.send_message("해당 제품은 현재 재고가 없습니다.", ephemeral=True)
            return
        prod = await get_product_by_id_shelf(interaction.guild_id, product_id)
        if not prod:
            await interaction.response.send_message("제품 정보를 불러올 수 없습니다.", ephemeral=True)
            return
        product_name, price = prod
        modal = PurchaseQuantityModal(interaction.guild_id, product_id, product_name, price, stock_count)
        await interaction.response.send_modal(modal)

class CategorySelect(ui.Select):
    def __init__(self, guild_id, categories):
        options = [discord.SelectOption(label=c[0], value=c[0]) for c in categories]
        super().__init__(placeholder="원하시는 카테고리를 선택해주세요", options=options, min_values=1, max_values=1)
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        products = await get_products_by_category(self.guild_id, category)
        if not products:
            await interaction.response.edit_message(view=create_ephemeral_container("알림", "해당 카테고리에 제품이 없습니다."))
            return
        view = ui.LayoutView()
        container = ui.Container(ui.TextDisplay("제품"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("원하시는 제품을 선택해주세요"))
        view.add_item(container)
        view.add_item(ProductSelect(self.guild_id, products))
        await interaction.response.edit_message(view=view)

class MyLayoutVending(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.c = ui.Container(ui.TextDisplay("24시간 OTT 자판기\n-# 버튼을 눌러 이용해주세요 !"))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        button_1 = ui.Button(label="충전", custom_id="charge_button")
        button_2 = ui.Button(label="입고알림", custom_id="notification_button")
        button_3 = ui.Button(label="내 정보", custom_id="my_info_button")
        button_4 = ui.Button(label="구매", custom_id="purchase_button")
        linha = ui.ActionRow(button_1, button_2)
        linha2 = ui.ActionRow(button_3, button_4)
        self.c.add_item(linha)
        self.c.add_item(linha2)
        self.add_item(self.c)
        button_2.callback = self.on_notification_click
        button_3.callback = self.on_my_info_click
        button_4.callback = self.on_purchase_click

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if await is_banned_shelf(interaction.guild_id, interaction.user.id):
            await interaction.response.send_message(view=create_ephemeral_container("**사용불가**","현재 자판기 이용이 제한되었습니다\n자세한 이유를 알고 싶으면 문의해주세요"), ephemeral=True)
            return False
        return True

    async def on_notification_click(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(NOTIFICATION_ROLE_ID)
        if not role:
            await interaction.response.send_message("알림 역할이 서버에 존재하지 않습니다.", ephemeral=True)
            return
        member = interaction.user
        new_state = await toggle_subscription_shelf(interaction.guild_id, member.id)
        if new_state:
            view = create_ephemeral_container("**알림받기**","이제 재고가 추가될 때마다 알림을 받으실 수 있습니다\n버튼을 한번 더 누르시면 알림이 취소됩니다.")
        else:
            view = create_ephemeral_container("**알림받기 취소**","이제 재고 알림을 받지 않습니다.")
        await interaction.response.send_message(view=view, ephemeral=True)

    async def on_my_info_click(self, interaction: discord.Interaction):
        user_info = await get_user_info(interaction.guild_id, interaction.user.id)
        view = ui.LayoutView()
        c = ui.Container(ui.TextDisplay(f"{interaction.user.display_name}님 정보"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"보유 금액 = __{user_info.get('balance',0)}__원"))
        c.add_item(ui.TextDisplay(f"누적 금액 = __{user_info.get('total',0)}__원"))
        c.add_item(ui.TextDisplay(f"거래 횟수 = __{user_info.get('tx_count',0)}__번"))
        view.add_item(c)
        await interaction.response.send_message(view=view, ephemeral=True)

    async def on_purchase_click(self, interaction: discord.Interaction):
        categories = await get_categories(interaction.guild_id)
        if not categories:
            await interaction.response.send_message(view=create_ephemeral_container("알림","현재 판매중인 상품이 없습니다."), ephemeral=True)
            return
        view = ui.LayoutView()
        container = ui.Container(ui.TextDisplay("EMOJI_0 카테고리"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("원하시는 카테고리를 선택해주세요"))
        view.add_item(container)
        view.add_item(CategorySelect(interaction.guild_id, categories))
        await interaction.response.send_message(view=view, ephemeral=True)

# ------------------ 슬래시 커맨드 (관리자 전용 포함) ------------------
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
    amount = 금액 if 종류=="추가" else -금액
    await record_transaction(interaction.guild_id, 유저.id, amount, "관리자", f"관리자({interaction.user.name})")
    new_info = await get_user_info(interaction.guild_id, 유저.id)
    view = ui.LayoutView()
    c = ui.Container(ui.TextDisplay(f"금액 {종류}"))
    c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    c.add_item(ui.TextDisplay(f"유저 = __{유저.display_name}__님"))
    c.add_item(ui.TextDisplay(f"{종류} 금액 = __{금액}__원"))
    c.add_item(ui.TextDisplay(f"{종류} 후 금액 = __{new_info.get('balance',0)}__원"))
    view.add_item(c)
    await interaction.response.send_message(view=view, ephemeral=True)

@bot.tree.command(name="이용제한", description="유저의 자판기 이용을 제한하거나 허용합니다.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(유저="상태를 변경할 유저", 상태="사용 또는 불가")
async def manage_restriction(interaction: discord.Interaction, 유저: discord.Member, 상태: str):
    if 상태 not in ["사용", "불가"]:
        await interaction.response.send_message("상태는 '사용' 또는 '불가'만 가능합니다.", ephemeral=True)
        return
    is_banned = (상태=="불가")
    await set_ban_shelf(interaction.guild_id, 유저.id, is_banned)
    status_text = "사용 불가" if is_banned else "사용 가능"
    view = ui.LayoutView()
    c = ui.Container(ui.TextDisplay("**자판기 사용 여부**"))
    c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    c.add_item(ui.TextDisplay(f"**유저** = {유저.mention}"))
    c.add_item(ui.TextDisplay(f"**사용 가능 여부** = __{status_text}__"))
    view.add_item(c)
    await interaction.response.send_message(view=view, ephemeral=True)

# 제품 설정(관리자) — 모달, 드롭다운, 재고추가 등
class ProductModal(ui.Modal):
    def __init__(self, guild_id):
        super().__init__(title="제품 추가")
        self.guild_id = guild_id
        self.emoji_input = ui.TextInput(label="이모지")
        self.name_input = ui.TextInput(label="제품 이름")
        self.category_input = ui.TextInput(label="카테고리")
        self.price_input = ui.TextInput(label="가격")
        self.add_item(self.emoji_input)
        self.add_item(self.name_input)
        self.add_item(self.category_input)
        self.add_item(self.price_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            price = int(self.price_input.value)
        except:
            await interaction.response.send_message("가격은 숫자만 입력하세요.", ephemeral=True); return
        emoji_str = self.emoji_input.value
        e_name, e_id = parse_custom_emoji(emoji_str)
        if not e_name and not e_id:
            e_name = emoji_str
            e_id = None
        try:
            pid = await add_product_shelf(interaction.guild_id, self.name_input.value, self.category_input.value, price, e_name, e_id)
            v = ui.LayoutView()
            c = ui.Container(ui.TextDisplay("**제품추가**"))
            c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(ui.TextDisplay(f"**제품 이름** = __{self.name_input.value}__"))
            c.add_item(ui.TextDisplay(f"**카테고리** = __{self.category_input.value}__"))
            c.add_item(ui.TextDisplay(f"**가격** = __{price}__원"))
            v.add_item(c)
            await interaction.response.send_message(view=v, ephemeral=True)
        except ValueError:
            await interaction.response.send_message("동일한 이름의 제품이 이미 있습니다.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"제품 추가 오류: {e}", ephemeral=True)

class ProductManagementSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="제품 추가", value="add_product"),
            discord.SelectOption(label="제품 삭제", value="delete_product"),
        ]
        super().__init__(placeholder="아래 드롭다운을 눌러 제품을 설정해주세요", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        try:
            choice = self.values[0]
            if choice == "add_product":
                await interaction.response.send_modal(ProductModal(interaction.guild_id))
            elif choice == "delete_product":
                products = await get_all_products_shelf(interaction.guild_id)
                if not products:
                    await interaction.response.send_message("삭제할 제품이 없습니다.", ephemeral=True); return
                view = ui.LayoutView()
                cont = ui.Container(ui.TextDisplay("삭제할 제품을 선택해주세요"))
                cont.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                view.add_item(cont)
                del_sel = ProductDeleteSelect(products)
                view.add_item(del_sel)
                await interaction.response.send_message(view=view, ephemeral=True)
        except Exception:
            try:
                await interaction.response.send_message("작업 처리 중 오류가 발생했습니다.", ephemeral=True)
            except:
                pass

class ProductDeleteSelect(ui.Select):
    def __init__(self, products):
        options = []
        for p_id, name, cat, price, e_name, e_id in products:
            options.append(discord.SelectOption(label=f"[{cat}] {name}", value=str(p_id)))
        super().__init__(placeholder="삭제할 제품 선택", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        try:
            pid = int(self.values[0])
            await remove_product_shelf(interaction.guild_id, pid)
            await interaction.response.send_message("선택 제품이 삭제되었습니다.", ephemeral=True)
        except Exception:
            await interaction.response.send_message("제품 삭제 중 오류가 발생했습니다.", ephemeral=True)

@bot.tree.command(name="제품설정", description="자판기의 제품을 추가하거나 삭제합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def product_settings(interaction: discord.Interaction):
    view = ui.LayoutView()
    cont = ui.Container(ui.TextDisplay("**제품 설정**"))
    cont.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    cont.add_item(ui.TextDisplay("아래 드롭다운을 눌러 제품을 설정해주세요"))
    view.add_item(cont)
    view.add_item(ui.ActionRow(ProductManagementSelect()))
    await interaction.response.send_message(view=view, ephemeral=True)

class StockAddModal(ui.Modal):
    def __init__(self, guild_id, product_id, product_name):
        super().__init__(title=f"{product_name} 재고 추가")
        self.guild_id = guild_id
        self.product_id = product_id
        self.product_name = product_name
        self.stock_input = ui.TextInput(label="추가할 재고 (줄바꿈으로 각 항목 입력)")
        self.add_item(self.stock_input)

    async def on_submit(self, interaction: discord.Interaction):
        stock_list = [s.strip() for s in self.stock_input.value.split('\n') if s.strip()]
        if not stock_list:
            await interaction.response.send_message("추가할 재고가 없습니다.", ephemeral=True); return
        await add_stock_shelf(self.guild_id, self.product_id, stock_list)
        view = ui.LayoutView()
        c = ui.Container(ui.TextDisplay("**재고 추가 완료**"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(ui.TextDisplay(f"**제품 이름** = __{self.product_name}__"))
        c.add_item(ui.TextDisplay(f"**추가된 재고 개수** = __{len(stock_list)}__개"))
        view.add_item(c)
        await interaction.response.send_message(view=view, ephemeral=True)
        # 알림 역할 멘션 (채널에 공지)
        role = interaction.guild.get_role(NOTIFICATION_ROLE_ID)
        if role:
            await interaction.channel.send(f"{role.mention} **{self.product_name}** 제품의 재고가 추가되었습니다!")

class StockAddSelect(ui.Select):
    def __init__(self, products):
        options = []
        for p_id, name, cat, price, e_name, e_id in products:
            options.append(discord.SelectOption(label=name, value=str(p_id)))
        super().__init__(placeholder="재고를 추가할 제품 선택", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        try:
            pid = int(self.values[0])
            product_name = next((p[1] for p in self.options if p.value == str(pid)), "알 수 없는 제품")
            await interaction.response.send_modal(StockAddModal(interaction.guild_id, pid, product_name))
        except Exception:
            await interaction.response.send_message("재고 추가 처리 중 오류가 발생했습니다.", ephemeral=True)

@bot.tree.command(name="재고추가", description="제품의 재고를 추가합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def add_stock_command(interaction: discord.Interaction):
    prods = await get_all_products_shelf(interaction.guild_id)
    if not prods:
        await interaction.response.send_message("먼저 제품을 추가해주세요.", ephemeral=True); return
    view = ui.LayoutView()
    cont = ui.Container(ui.TextDisplay("**재고 추가**"))
    cont.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    cont.add_item(ui.TextDisplay("드롭다운을 눌러 재고를 추가할 제품을 선택해주세요."))
    view.add_item(cont)
    view.add_item(ui.ActionRow(StockAddSelect(prods)))
    await interaction.response.send_message(view=view, ephemeral=True)

# ------------------ on_ready ------------------
@bot.event
async def on_ready():
    try:
        await init_db_async()
        print("DB 초기화 완료 (shelve)")
    except Exception as e:
        print("DB 초기화 오류:", e)
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)}개의 슬래시 명령이 동기화되었습니다.")
    except Exception as e:
        print("명령 동기화 오류:", e)
    print(f"{bot.user}로 로그인했습니다.")

# ------------------ 실행 ------------------
# .env 에 DISCORD_TOKEN 설정 권장
bot.run(os.getenv("DISCORD_TOKEN") or "")
