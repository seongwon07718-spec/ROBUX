import discord
from discord import PartialEmoji, ui
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
from datetime import datetime

# SQLite 관련
import sqlite3
import asyncio
from functools import partial

# .env 로드
load_dotenv()

intents = discord.Intents.all()
command_prefix = "!"
bot = commands.Bot(command_prefix=command_prefix, intents=intents)

ROLE_ID = 1419336612956864712  # 예시: 필요하면 사용
NOTIFY_ROLE_ID = 1429436071539773561  # 입고알림 역할 ID (요청하신 ID)

# ------------------ SQLite 설정 (내장 DB) ------------------
DB_PATH = "data.db"  # DB 파일명

def _init_sqlite():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    # users 테이블 (guild_id + user_id 복합 PK)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        balance INTEGER DEFAULT 0,
        total INTEGER DEFAULT 0,
        tx_count INTEGER DEFAULT 0,
        can_use INTEGER DEFAULT 1,
        PRIMARY KEY (guild_id, user_id)
    )
    """)
    # transactions 테이블
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
    # products 테이블
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id TEXT PRIMARY KEY,
        emoji TEXT,
        name TEXT,
        category TEXT,
        price INTEGER,
        stock INTEGER DEFAULT 0
    )
    """)
    # subscriptions (입고알림 구독)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        notify INTEGER DEFAULT 1,
        PRIMARY KEY (guild_id, user_id)
    )
    """)
    # bans (이용 제한)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bans (
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        banned INTEGER DEFAULT 0,
        reason TEXT,
        PRIMARY KEY (guild_id, user_id)
    )
    """)
    conn.commit()
    conn.close()

async def init_db_async(loop=None):
    if loop is None:
        loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _init_sqlite)

def _record_transaction_sqlite_sync(tx_doc: dict):
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    # transactions 삽입 (혹시 동일 tx_id가 있으면 replace)
    cur.execute("""
    INSERT OR REPLACE INTO transactions (tx_id, guild_id, user_id, amount, type, note, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (tx_doc["_id"], tx_doc["guild_id"], tx_doc["user_id"], tx_doc["amount"], tx_doc.get("type"), tx_doc.get("note"), tx_doc["created_at"]))
    # users 업서트: INSERT ... ON CONFLICT DO UPDATE
    cur.execute("""
    INSERT INTO users (guild_id, user_id, balance, total, tx_count)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(guild_id, user_id) DO UPDATE SET
      balance = users.balance + excluded.balance,
      total = users.total + excluded.total,
      tx_count = users.tx_count + excluded.tx_count
    """, (tx_doc["guild_id"], tx_doc["user_id"], tx_doc["amount"], tx_doc["amount"], 1))
    conn.commit()
    conn.close()

async def record_transaction_sqlite(guild_id: int, user_id: int, amount: int, ttype: str = "구매", note: str = ""):
    loop = asyncio.get_running_loop()
    tx_doc = {
        "_id": f"{int(datetime.utcnow().timestamp()*1000)}_{user_id}",
        "guild_id": int(guild_id),
        "user_id": int(user_id),
        "amount": int(amount),
        "type": ttype,
        "note": note,
        "created_at": datetime.utcnow().isoformat(sep=' ', timespec='seconds')
    }
    await loop.run_in_executor(None, partial(_record_transaction_sqlite_sync, tx_doc))

def _get_user_info_sync(guild_id: int, user_id: int):
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT balance, total, tx_count, can_use FROM users WHERE guild_id=? AND user_id=?", (guild_id, user_id))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"balance": row[0], "total": row[1], "tx_count": row[2], "can_use": row[3]}
    else:
        return {"balance": 0, "total": 0, "tx_count": 0, "can_use": 1}

async def get_user_info_sqlite(guild_id: int, user_id: int):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_get_user_info_sync, int(guild_id), int(user_id)))

def _get_recent_tx_sync(guild_id, user_id, limit=10):
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT tx_id, amount, type, note, created_at FROM transactions WHERE guild_id=? AND user_id=? ORDER BY created_at DESC LIMIT ?", (guild_id, user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows

async def get_recent_tx_sqlite(guild_id, user_id, limit=10):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_get_recent_tx_sync, int(guild_id), int(user_id), int(limit)))

# Subscriptions helpers
def _toggle_subscription_sync(guild_id, user_id):
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT notify FROM subscriptions WHERE guild_id=? AND user_id=?", (guild_id, user_id))
    row = cur.fetchone()
    if row is None:
        cur.execute("INSERT INTO subscriptions (guild_id, user_id, notify) VALUES (?, ?, 1)", (guild_id, user_id))
        new = True
    else:
        new_val = 0 if row[0] == 1 else 1
        cur.execute("UPDATE subscriptions SET notify=? WHERE guild_id=? AND user_id=?", (new_val, guild_id, user_id))
        new = (new_val == 1)
    conn.commit()
    conn.close()
    return new

async def toggle_subscription(guild_id, user_id):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_toggle_subscription_sync, int(guild_id), int(user_id)))

# Product helpers
def _add_product_sync(product_id, emoji, name, category, price, stock):
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO products (product_id, emoji, name, category, price, stock) VALUES (?, ?, ?, ?, ?, ?)",
                (product_id, emoji, name, category, price, stock))
    conn.commit()
    conn.close()

def _remove_product_sync(product_id):
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE product_id=?", (product_id,))
    conn.commit()
    conn.close()

def _get_categories_sync():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM products")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows

def _get_products_by_category_sync(category):
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT product_id, emoji, name, price, stock FROM products WHERE category=?", (category,))
    rows = cur.fetchall()
    conn.close()
    return rows

def _get_product_sync(product_id):
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT product_id, emoji, name, category, price, stock FROM products WHERE product_id=?", (product_id,))
    row = cur.fetchone()
    conn.close()
    return row

async def add_product(product_id, emoji, name, category, price, stock):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, partial(_add_product_sync, product_id, emoji, name, category, int(price), int(stock)))

async def remove_product(product_id):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, partial(_remove_product_sync, product_id))

async def get_categories():
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_categories_sync)

async def get_products_by_category(category):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_get_products_by_category_sync, category))

async def get_product(product_id):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_get_product_sync, product_id))

# Stock update
def _update_stock_sync(product_id, delta):
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("UPDATE products SET stock = stock + ? WHERE product_id=?", (delta, product_id))
    conn.commit()
    cur.execute("SELECT stock FROM products WHERE product_id=?", (product_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

async def update_stock(product_id, delta):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_update_stock_sync, product_id, delta))

# Bans helpers
def _set_ban_sync(guild_id, user_id, banned, reason):
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("INSERT INTO bans (guild_id, user_id, banned, reason) VALUES (?, ?, ?, ?) ON CONFLICT(guild_id, user_id) DO UPDATE SET banned=excluded.banned, reason=excluded.reason",
                (guild_id, user_id, banned, reason))
    # Also update users.can_use for quick check
    cur.execute("INSERT INTO users (guild_id, user_id, balance, total, tx_count, can_use) VALUES (?, ?, 0, 0, 0, ?) ON CONFLICT(guild_id, user_id) DO UPDATE SET can_use=excluded.can_use",
                (guild_id, user_id, 1-banned))
    conn.commit()
    conn.close()

async def set_ban(guild_id, user_id, banned, reason=""):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_set_ban_sync, guild_id, user_id, int(banned), reason))

# ------------------ 기존 레이아웃 (변경 최소화) ------------------
class MyLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        self.c = ui.Container(ui.TextDisplay("**누락 보상 받기**"))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.c.add_item(ui.TextDisplay("-# 아래 누락보상 버튼을 누르시면 보상 받을 수 있습니다.\n-# 다만 제품 보증 없는거는 보상 받으실 수 없습니다."))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 기존에 사용하던 커스텀 이모지를 그대로 두었으나, 필요시 유니코드로 바꾸세요.
        custom_emoji1 = PartialEmoji(name="__", id=1429373065116123190)
        custom_emoji2 = PartialEmoji(name="1_7", id=1429373066588454943)

        self.button_1 = ui.Button(label="누락 보상 받기", custom_id="button_1", emoji=custom_emoji1)
        self.button_2 = ui.Button(label="누락 제품 확인", custom_id="button_2", emoji=custom_emoji2)

        linha = ui.ActionRow(self.button_1, self.button_2)

        self.c.add_item(linha)
        self.add_item(self.c)

active_views = {}

class MyLayoutVending(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        
        c = ui.Container(ui.TextDisplay(
            "**24시간 OTT 자판기**\n-# 버튼을 눌러 이용해주세요 !"
        ))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        sessao = ui.Section(ui.TextDisplay("**총 판매 금액\n-# 실시간으로 올라갑니다.**"), accessory=ui.Button(label="0원", disabled=True))
        c.add_item(sessao)
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 이모지 (예시 ID)
        custom_emoji1 = PartialEmoji(name="3", id=1426934636428394678)
        custom_emoji2 = PartialEmoji(name="6", id=1426943544928505886)
        custom_emoji3 = PartialEmoji(name="5", id=1426936503635939428)
        custom_emoji4 = PartialEmoji(name="4", id=1426936460149395598)

        # 메인 버튼들
        button_1 = ui.Button(label="충전", custom_id="button_1", emoji=custom_emoji1)
        button_2 = ui.Button(label="입고알림", custom_id="button_2", emoji=custom_emoji2)
        button_3 = ui.Button(label="내 정보", custom_id="button_3", emoji=custom_emoji3)
        button_4 = ui.Button(label="구매", custom_id="button_4", emoji=custom_emoji4)

        linha = ui.ActionRow(button_1, button_2)
        linha2 = ui.ActionRow(button_3, button_4)

        c.add_item(linha)
        c.add_item(linha2)
        self.add_item(c)

        # 버튼 콜백들 연결
        button_2.callback = self.on_notify_click  # 입고알림
        button_3.callback = self.on_my_info_click
        button_4.callback = self.on_purchase_click

    # "입고알림" 버튼 콜백: 역할 토글 및 DB 저장
    async def on_notify_click(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("서버에서만 사용할 수 있습니다.", ephemeral=True)
            return

        # 토글 DB
        try:
            new_state = await toggle_subscription(guild.id, member.id)
        except Exception as e:
            await interaction.response.send_message("알림 구독을 처리하는 중 오류가 발생했습니다.", ephemeral=True)
            return

        # 역할 부여/제거
        role = guild.get_role(NOTIFY_ROLE_ID)
        try:
            if new_state:
                if role:
                    await member.add_roles(role, reason="입고알림 구독")
                msg = "**알림받기**\n\n---\n이제 재고 올때마다 알림 받으실 수 있습니다\n버튼 한번더 누르시면 알림받기 취소됩니다"
            else:
                if role:
                    await member.remove_roles(role, reason="입고알림 구독 취소")
                msg = "**알림받기 취소**\n\n---\n이제 재고 알림을 받지 않습니다\n다시 누르면 알림을 다시 받습니다."
            # 컨테이너 뷰 전송 (에페메럴)
            view = ui.LayoutView(timeout=60)
            c = ui.Container(ui.TextDisplay(msg))
            c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            view.add_item(c)
            await interaction.response.send_message(view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("역할 부여/제거에 실패했습니다. 봇 권한을 확인해 주세요.", ephemeral=True)

    # "내 정보" 버튼 콜백: 기존 기능 유지(이미 SQLite로 연결)
    async def on_my_info_click(self, interaction: discord.Interaction):
        # 기존 내용 그대로 재사용 (상단에서 정의된 함수 사용)
        # 이전 코드 사용: 이미 정의된 get_user_info_sqlite/get_recent_tx_sqlite 사용
        member = interaction.user
        guild = interaction.guild

        try:
            if guild is None:
                await interaction.response.send_message("이 명령은 서버에서만 사용할 수 있습니다.", ephemeral=True)
                return

            user_info = await get_user_info_sqlite(guild.id, member.id)
            balance = user_info.get("balance", 0)
            total = user_info.get("total", 0)
            tx_count = user_info.get("tx_count", 0)
            can_use = user_info.get("can_use", 1)

            tx_list = await get_recent_tx_sqlite(guild.id, member.id, limit=10)

        except Exception as e:
            await interaction.response.send_message("DB 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.", ephemeral=True)
            return

        ephemeral_view = ui.LayoutView(timeout=120)
        info_container = ui.Container(ui.TextDisplay(f"**{member.display_name}님 정보**"))
        info_container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        info_container.add_item(ui.TextDisplay(f"**보유 금액** = __{balance}__원"))
        info_container.add_item(ui.TextDisplay(f"**누적 금액** = __{total}__원"))
        info_container.add_item(ui.TextDisplay(f"**거래 횟수** = __{tx_count}__번"))
        info_container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        info_container.add_item(ui.TextDisplay("항상 이용해주셔서 감사합니다."))
        ephemeral_view.add_item(info_container)

        if tx_list and len(tx_list) > 0:
            options = []
            for tx in tx_list:
                tx_id, amount, ttype, note, created_at = tx
                ts = created_at
                label = f"{ts} | {ttype or '거래'} | {amount}원"
                options.append(ui.SelectOption(label=label, value=str(tx_id)))
            select = ui.Select(placeholder="거래 내역 보기", options=options, min_values=1, max_values=1)
            async def select_callback(select_interaction: discord.Interaction):
                selected_id = select_interaction.data["values"][0]
                def _get_tx_detail_sync(tx_id):
                    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
                    cur = conn.cursor()
                    cur.execute("SELECT tx_id, amount, type, note, created_at FROM transactions WHERE tx_id=?", (tx_id,))
                    row = cur.fetchone()
                    conn.close()
                    return row
                loop = asyncio.get_running_loop()
                tx_doc = await loop.run_in_executor(None, partial(_get_tx_detail_sync, selected_id))
                if tx_doc is None:
                    await select_interaction.response.send_message("선택한 거래 내역을 불러오지 못했습니다.", ephemeral=True)
                    return
                tx_id_v, amount_v, ttype_v, note_v, created_v = tx_doc
                detail_view = ui.LayoutView(timeout=60)
                d_c = ui.Container(ui.TextDisplay("**거래 내역 상세**"))
                d_c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                d_c.add_item(ui.TextDisplay(f"거래 ID: {tx_id_v}"))
                d_c.add_item(ui.TextDisplay(f"종류: {ttype_v or '알수없음'}"))
                d_c.add_item(ui.TextDisplay(f"금액: {amount_v}원"))
                d_c.add_item(ui.TextDisplay(f"설명: {note_v or '-'}"))
                d_c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                d_c.add_item(ui.TextDisplay("감사합니다."))
                detail_view.add_item(d_c)
                await select_interaction.response.send_message(view=detail_view, ephemeral=True)
            select.callback = select_callback
            row = ui.ActionRow(select)
            ephemeral_view.add_item(row)

        await interaction.response.send_message(view=ephemeral_view, ephemeral=True)

    # "구매" 버튼 콜백: 카테고리 선택 -> 제품 선택 -> 수량 모달 -> 처리
    async def on_purchase_click(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        if guild is None:
            await interaction.response.send_message("서버에서만 사용 가능합니다.", ephemeral=True)
            return
        # 먼저 사용 제한 확인
        user_info = await get_user_info_sqlite(guild.id, member.id)
        if user_info.get("can_use", 1) == 0:
            # 사용불가 메시지
            view = ui.LayoutView(timeout=30)
            c = ui.Container(ui.TextDisplay("**사용불가**"))
            c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(ui.TextDisplay("현재 자판기 이용이 제한되었습니다\n자세한 이유를 알고 싶으면 문의해주세요"))
            view.add_item(c)
            await interaction.response.send_message(view=view, ephemeral=True)
            return

        # get categories
        categories = await get_categories()
        if not categories:
            await interaction.response.send_message("등록된 제품이 없습니다. 관리자에게 문의하세요.", ephemeral=True)
            return
        options = [ui.SelectOption(label=c, value=c) for c in categories]
        select = ui.Select(placeholder="카테고리 선택", options=options, min_values=1, max_values=1)
        async def category_select_cb(sel_inter: discord.Interaction):
            chosen = sel_inter.data["values"][0]
            products = await get_products_by_category(chosen)
            if not products:
                await sel_inter.response.send_message("해당 카테고리에 제품이 없습니다.", ephemeral=True)
                return
            prod_opts = []
            for p in products:
                pid, emoji, name, price, stock = p
                lab = f"{name} | {price}원 | 재고:{stock}"
                prod_opts.append(ui.SelectOption(label=lab, value=pid))
            prod_select = ui.Select(placeholder="제품 선택", options=prod_opts, min_values=1, max_values=1)
            async def prod_select_cb(prod_inter: discord.Interaction):
                pid = prod_inter.data["values"][0]
                # 수량 모달
                class QtyModal(ui.Modal):
                    def __init__(self):
                        super().__init__(title="구매 수량 입력")
                        self.add_item(ui.TextInput(label="구매 수량", style=discord.TextStyle.short, placeholder="숫자만 입력", required=True))
                    async def on_submit(self, modal_inter: discord.Interaction):
                        qty_text = self.children[0].value
                        try:
                            qty = int(qty_text)
                            if qty <= 0:
                                raise ValueError
                        except:
                            await modal_inter.response.send_message("올바른 수량을 입력해주세요.", ephemeral=True)
                            return
                        # 제품 확인
                        prod = await get_product(pid)
                        if prod is None:
                            await modal_inter.response.send_message("제품 정보를 불러오지 못했습니다.", ephemeral=True)
                            return
                        _, emoji_v, name_v, category_v, price_v, stock_v = prod
                        if stock_v < qty:
                            await modal_inter.response.send_message("재고가 부족합니다.", ephemeral=True)
                            return
                        total_price = price_v * qty
                        # 잔액 확인
                        user = await get_user_info_sqlite(guild.id, member.id)
                        if user.get("balance", 0) < total_price:
                            await modal_inter.response.send_message("보유 금액이 부족합니다.", ephemeral=True)
                            return
                        # 차감 및 재고 업데이트, 거래 기록
                        # 1) 차감: record_transaction_sqlite with negative amount to reduce balance
                        await record_transaction_sqlite(guild.id, member.id, -total_price, ttype="구매", note=f"{name_v} x{qty}")
                        await update_stock(pid, -qty)
                        # DM 발송
                        dm_view = ui.LayoutView(timeout=30)
                        dc = ui.Container(ui.TextDisplay("구매 제품"))
                        dc.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                        dc.add_item(ui.TextDisplay(f"구매한 제품 = {name_v} x{qty}"))
                        dc.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                        dc.add_item(ui.TextDisplay("구매해주셔서 감사합니다."))
                        dm_view.add_item(dc)
                        try:
                            await member.send(view=dm_view)
                        except:
                            pass
                        # 성공 메시지 (채널)
                        success_view = ui.LayoutView(timeout=30)
                        sc = ui.Container(ui.TextDisplay("**구매 성공**"))
                        sc.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                        sc.add_item(ui.TextDisplay(f"**제품 이름** = {name_v}"))
                        sc.add_item(ui.TextDisplay(f"**구매 개수** = {qty}"))
                        sc.add_item(ui.TextDisplay(f"**차감 금액** = {total_price}원"))
                        sc.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                        sc.add_item(ui.TextDisplay("성공적으로 구매 완료되었습니다."))
                        success_view.add_item(sc)
                        await modal_inter.response.send_message(view=success_view, ephemeral=True)
                    async def on_error(self, modal_inter: discord.Interaction, error: Exception):
                        await modal_inter.response.send_message("처리 중 오류가 발생했습니다.", ephemeral=True)
                await prod_inter.response.send_modal(QtyModal())
            prod_select.callback = prod_select_cb
            await sel_inter.response.edit_message(view=ui.LayoutView().add_item(ui.ActionRow(prod_select)))
        select.callback = category_select_cb
        # send initial category select as ephemeral
        row = ui.ActionRow(select)
        layout = ui.LayoutView(timeout=120)
        layout.add_item(ui.Container(ui.TextDisplay("**카테고리**\n\n원하시는 카테고리 선택해주세요")))
        layout.add_item(row)
        await interaction.response.send_message(view=layout, ephemeral=True)

# ------------------ DB 연결 및 봇 이벤트 ------------------
@bot.event
async def on_ready():
    # SQLite 초기화 (한 번만)
    try:
        await init_db_async()
        print("SQLite DB 초기화 완료")
    except Exception as e:
        print("SQLite 초기화 중 오류:", e)

    print(f"로벅스 자판기 봇이 {bot.user}로 로그인했습니다.")
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'슬래시 명령어 동기화 중 오류 발생.: {e}')

# ------------------ 슬래시 명령 구현 (관리자 체크 포함) ------------------

# 관리자(관리 권한)만 사용 가능 체크
def is_guild_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator

@bot.tree.command(name="금액관리", description="유저 금액을 추가하거나 차감합니다. (관리자 전용)")
@app_commands.describe(member="대상 유저", amount="변동 금액(양수)", action="추가 또는 차감 선택")
async def cmd_money_manage(interaction: discord.Interaction, member: discord.Member, amount: int, action: app_commands.Choice[str]):
    if not is_guild_admin(interaction):
        await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        return
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("서버에서만 사용 가능합니다.", ephemeral=True)
        return
    amt = abs(int(amount))
    if action.value == "차감":
        amt = -amt
    # apply change: use record_transaction_sqlite for delta (positive -> increase balance, negative -> decrease)
    await record_transaction_sqlite(guild.id, member.id, amt, ttype=("추가" if amt>0 else "차감"), note=f"관리자수정 by {interaction.user}")
    # get current
    user_info = await get_user_info_sqlite(guild.id, member.id)
    new_balance = user_info.get("balance", 0)
    # response container
    if amt > 0:
        title = "**금액추가**"
        lines = [
            f"**유저** = __{member.display_name}__",
            f"**추가 금액** = __{amt}__원",
            f"**추가 후 금액** = __{new_balance}__원"
        ]
    else:
        title = "**금액차감**"
        lines = [
            f"**유저** = __{member.display_name}__",
            f"**차감 금액** = __{abs(amt)}__원",
            f"**차감 후 금액** = __{new_balance}__원"
        ]
    view = ui.LayoutView(timeout=60)
    c = ui.Container(ui.TextDisplay(f"{title}\n\n---\n" + "\n".join(lines)))
    view.add_item(c)
    await interaction.response.send_message(view=view, ephemeral=False)

# action choices for 금액관리 param
cmd_money_manage.autocomplete = None
# but app_commands.Choice needs to be passed when invoked; to simplify, register a helper to show choices:
@app_commands.choices(name="action", choices=[app_commands.Choice(name="추가", value="추가"), app_commands.Choice(name="차감", value="차감")])
async def _dummy(): pass

@bot.tree.command(name="이용제한", description="유저의 자판기 사용을 차단하거나 허용합니다. (관리자 전용)")
@app_commands.describe(member="대상 유저", mode="사용 or 불가 선택")
async def cmd_ban_manage(interaction: discord.Interaction, member: discord.Member, mode: app_commands.Choice[str]):
    if not is_guild_admin(interaction):
        await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        return
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("서버에서만 사용 가능합니다.", ephemeral=True)
        return
    banned = 0 if mode.value == "사용" else 1
    await set_ban(guild.id, member.id, banned, reason=f"관리자:{interaction.user}")
    user_info = await get_user_info_sqlite(guild.id, member.id)
    can_use = "사용 가능" if user_info.get("can_use",1)==1 else "사용 불가"
    view = ui.LayoutView(timeout=60)
    c = ui.Container(ui.TextDisplay("**자판기 사용 여부**\n\n---\n" + f"**유저** = __{member.display_name}__\n**사용 가능 여부** = __{can_use}__"))
    view.add_item(c)
    await interaction.response.send_message(view=view, ephemeral=False)

# 제품설정: 관리자 전용 — 초기 화면 + 드롭다운(제품추가,제품삭제)
@bot.tree.command(name="제품설정", description="제품을 추가/삭제합니다. (관리자 전용)")
async def cmd_product_manage(interaction: discord.Interaction):
    if not is_guild_admin(interaction):
        await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        return
    # initial container with action select
    options = [
        ui.SelectOption(label="제품추가", value="add"),
        ui.SelectOption(label="제품삭제", value="remove")
    ]
    select = ui.Select(placeholder="작업 선택", options=options, min_values=1, max_values=1)
    async def sel_cb(sel_inter: discord.Interaction):
        choice = sel_inter.data["values"][0]
        if choice == "add":
            # show modal to add product
            class AddModal(ui.Modal):
                def __init__(self):
                    super().__init__(title="제품 추가")
                    self.emoji = ui.TextInput(label="이모지 (커스텀 또는 유니코드)", required=True)
                    self.name = ui.TextInput(label="제품 이름", required=True)
                    self.category = ui.TextInput(label="카테고리", required=True)
                    self.price = ui.TextInput(label="가격(숫자)", required=True)
                    self.stock = ui.TextInput(label="초기 재고(숫자)", required=True)
                    self.add_item(self.emoji)
                    self.add_item(self.name)
                    self.add_item(self.category)
                    self.add_item(self.price)
                    self.add_item(self.stock)
                async def on_submit(self, modal_inter: discord.Interaction):
                    try:
                        price_v = int(self.price.value)
                        stock_v = int(self.stock.value)
                    except:
                        await modal_inter.response.send_message("가격과 재고는 숫자로 입력해주세요.", ephemeral=True)
                        return
                    pid = f"{int(datetime.utcnow().timestamp()*1000)}_{self.name.value}"
                    await add_product(pid, self.emoji.value, self.name.value, self.category.value, price_v, stock_v)
                    # response container
                    view = ui.LayoutView(timeout=60)
                    c = ui.Container(ui.TextDisplay("**제품추가**\n\n---\n" + f"**이모지** = {self.emoji.value}\n**제품 이름** = {self.name.value}\n**카테고리** = {self.category.value}\n**가격** = {price_v}원"))
                    view.add_item(c)
                    await modal_inter.response.send_message(view=view, ephemeral=False)
            await sel_inter.response.send_modal(AddModal())
        else:
            # remove: show dropdown of existing products
            # fetch products
            conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
            cur = conn.cursor()
            cur.execute("SELECT product_id, name FROM products")
            rows = cur.fetchall()
            conn.close()
            if not rows:
                await sel_inter.response.send_message("등록된 제품이 없습니다.", ephemeral=True)
                return
            options2 = [ui.SelectOption(label=r[1], value=r[0]) for r in rows]
            remove_sel = ui.Select(placeholder="삭제할 제품 선택", options=options2, min_values=1, max_values=1)
            async def remove_cb(rem_inter: discord.Interaction):
                pid = rem_inter.data["values"][0]
                await remove_product(pid)
                await rem_inter.response.send_message("제품을 삭제했습니다.", ephemeral=True)
            remove_sel.callback = remove_cb
            await sel_inter.response.edit_message(view=ui.LayoutView().add_item(ui.ActionRow(remove_sel)))
    select.callback = sel_cb
    layout = ui.LayoutView(timeout=60)
    layout.add_item(ui.Container(ui.TextDisplay("**제품설정**\n\n---\n아래 드롭바를 눌러 제품 설정해주세요")))
    layout.add_item(ui.ActionRow(select))
    await interaction.response.send_message(view=layout, ephemeral=False)

# 재고추가: 관리자 전용. 카테고리에 따라 제품 선택 후 모달로 수량 입력
@bot.tree.command(name="재고추가", description="제품 재고를 추가합니다. (관리자 전용)")
async def cmd_stock_add(interaction: discord.Interaction):
    if not is_guild_admin(interaction):
        await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        return
    # show product select
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT product_id, name FROM products")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        await interaction.response.send_message("등록된 제품이 없습니다.", ephemeral=True)
        return
    options = [ui.SelectOption(label=r[1], value=r[0]) for r in rows]
    sel = ui.Select(placeholder="재고 추가할 제품 선택", options=options, min_values=1, max_values=1)
    async def sel_cb(sel_inter: discord.Interaction):
        pid = sel_inter.data["values"][0]
        class StockModal(ui.Modal):
            def __init__(self):
                super().__init__(title="재고 추가")
                self.qty = ui.TextInput(label="추가할 재고 수량", required=True)
                self.add_item(self.qty)
            async def on_submit(self, modal_inter: discord.Interaction):
                try:
                    q = int(self.qty.value)
                except:
                    await modal_inter.response.send_message("숫자만 입력해주세요.", ephemeral=True)
                    return
                new_stock = await update_stock(pid, q)
                # fetch product name
                prod = await get_product(pid)
                name_v = prod[2] if prod else "알수없음"
                view = ui.LayoutView(timeout=60)
                c = ui.Container(ui.TextDisplay("**재고추가**\n\n---\n" + f"**제품 이름** = {name_v}\n**추가된 재고 개수** = {q}개"))
                view.add_item(c)
                await modal_inter.response.send_message(view=view, ephemeral=False)
        await sel_inter.response.send_modal(StockModal())
    sel.callback = sel_cb
    await interaction.response.send_message(view=ui.LayoutView().add_item(ui.Container(ui.TextDisplay("**재고추가**\n\n---\n드롭바를 눌러 재고 추가해주세요"))).add_item(ui.ActionRow(sel)), ephemeral=False)

# ------------------ 슬래시 명령 (유지) ------------------
@bot.tree.command(name="누락패널", description="누락 보상 패널을 표시합니다")
async def button_panel_nurak(interaction: discord.Interaction):
    layout = MyLayout()
    await interaction.response.send_message(view=layout, ephemeral=False)

@bot.tree.command(name="자판기패널", description="자판기 패널을 표시합니다")
async def button_panel_vending(interaction: discord.Interaction):
    layout = MyLayoutVending()
    await interaction.response.send_message(view=layout, ephemeral=False)

# ------------------ 봇 실행 (토큰 입력 필요) ------------------
bot.run(os.getenv("DISCORD_TOKEN") or "")  # .env 에 DISCORD_TOKEN 설정 권장
