import discord
from discord import PartialEmoji, ui
from discord.ext import commands
# --- MongoDB 삭제 ---
# from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from datetime import datetime

# SQLite 관련 추가
import sqlite3
import asyncio
from functools import partial

# .env 로드 (여전히 사용 중이라면 유지)
load_dotenv()
# MONGO_URI 제거(더 이상 사용하지 않음)
# MONGO_URI = os.getenv("MONGO_URI")  # 제거됨

intents = discord.Intents.all()
command_prefix = "!"
bot = commands.Bot(command_prefix=command_prefix, intents=intents)

ROLE_ID = 1419336612956864712  # 예시: 필요하면 사용

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
    cur.execute("SELECT balance, total, tx_count FROM users WHERE guild_id=? AND user_id=?", (guild_id, user_id))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"balance": row[0], "total": row[1], "tx_count": row[2]}
    else:
        return {"balance": 0, "total": 0, "tx_count": 0}

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

        # "내 정보" 버튼에 콜백 연결 (이 클래스 내부에서 연결)
        button_3.callback = self.on_my_info_click

    # "내 정보" 버튼 콜백: 사용자 DB에서 정보 조회 후 에페메럴 컨테이너로 전송
    async def on_my_info_click(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild

        # SQLite 사용으로 변경: DB 준비 확인
        # (on_ready에서 init_db_async를 호출하므로 보통 준비되어 있음)
        # 안전 체크
        try:
            # users 정보 조회
            if guild is None:
                await interaction.response.send_message("이 명령은 서버에서만 사용할 수 있습니다.", ephemeral=True)
                return

            user_info = await get_user_info_sqlite(guild.id, member.id)
            balance = user_info.get("balance", 0)
            total = user_info.get("total", 0)
            tx_count = user_info.get("tx_count", 0)

            # 최근 거래 조회
            tx_list = await get_recent_tx_sqlite(guild.id, member.id, limit=10)

        except Exception as e:
            await interaction.response.send_message("DB 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.", ephemeral=True)
            return

        # 에페메럴 뷰(누른 사용자만 보임)
        ephemeral_view = ui.LayoutView(timeout=120)

        info_container = ui.Container(ui.TextDisplay(f"**{member.display_name}님 정보**"))
        info_container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        info_container.add_item(ui.TextDisplay(f"**보유 금액** = __{balance}__원"))
        info_container.add_item(ui.TextDisplay(f"**누적 금액** = __{total}__원"))
        info_container.add_item(ui.TextDisplay(f"**거래 횟수** = __{tx_count}__번"))
        info_container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        info_container.add_item(ui.TextDisplay("항상 이용해주셔서 감사합니다."))
        ephemeral_view.add_item(info_container)

        # 거래 목록이 하나라도 있으면 드롭다운(셀렉트) 추가
        if tx_list and len(tx_list) > 0:
            options = []
            for tx in tx_list:
                # tx는 (tx_id, amount, type, note, created_at)
                tx_id, amount, ttype, note, created_at = tx
                ts = created_at
                label = f"{ts} | {ttype or '거래'} | {amount}원"
                options.append(ui.SelectOption(label=label, value=str(tx_id)))

            select = ui.Select(placeholder="거래 내역 보기", options=options, min_values=1, max_values=1)

            async def select_callback(select_interaction: discord.Interaction):
                selected_id = select_interaction.data["values"][0]
                # 상세 조회(동기->비동기 래퍼 사용)
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

        # 응답: 에페메럴로 정보창 전송
        await interaction.response.send_message(view=ephemeral_view, ephemeral=True)

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

# ------------------ 슬래시 명령 (기존 유지) ------------------
@bot.tree.command(name="누락패널", description="누락 보상 패널을 표시합니다")
async def button_panel_nurak(interaction: discord.Interaction):
    layout = MyLayout()
    await interaction.response.send_message(view=layout, ephemeral=False)

@bot.tree.command(name="자판기패널", description="자판기 패널을 표시합니다")
async def button_panel_vending(interaction: discord.Interaction):
    layout = MyLayoutVending()
    await interaction.response.send_message(view=layout, ephemeral=False)

# ------------------ 예시: 거래 저장 함수 (다른 곳에서 호출 가능) ------------------
# 기존 MongoDB용 record_transaction 대신 SQLite용 함수 사용
# 사용 예: await record_transaction_sqlite(guild.id, user.id, 3000, ttype="구매", note="상품A")

# ------------------ 봇 실행 (토큰 빈칸으로 유지) ------------------
bot.run("")  # 여기에 봇 토큰 입력
