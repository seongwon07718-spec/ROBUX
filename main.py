import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
import string
import os
import io
from datetime import datetime, timedelta

# ── 설정 ──────────────────────────────────────────────
TOKEN = ""
ADMIN_IDS = [1454398431996018724]  # 봇 운영자 디스코드 ID 목록
DB_DIR = "DB"
LICENSE_DB = os.path.join(DB_DIR, "라이센스.db")
# ──────────────────────────────────────────────────────

os.makedirs(DB_DIR, exist_ok=True)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


def init_license_db():
    conn = sqlite3.connect(LICENSE_DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            key TEXT PRIMARY KEY,
            days INTEGER NOT NULL,
            used INTEGER DEFAULT 0,
            guild_id TEXT DEFAULT NULL,
            guild_name TEXT DEFAULT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()


def init_guild_db(guild_id: str, guild_name: str):
    safe_name = "".join(c for c in guild_name if c.isalnum() or c in (" ", "_", "-")).strip()
    path = os.path.join(DB_DIR, f"{safe_name}.db")
    conn = sqlite3.connect(path)
    c = conn.cursor()
    
    # 기본 테이블 생성
    c.execute("""
        CREATE TABLE IF NOT EXISTS info (
            guild_id TEXT PRIMARY KEY,
            guild_name TEXT
        )
    """)
    
    # 에러 방지: 기존 DB에 누락된 컬럼이 있다면 강제로 추가 (no such column 해결)
    columns = [
        ("license_key", "TEXT"),
        ("registered_at", "TEXT"),
        ("expires_at", "TEXT"),
        ("vending_title", "TEXT DEFAULT '구매하기'"),
        ("vending_description", "TEXT DEFAULT '아래 버튼을 눌러 이용해주세요'"),
        ("accent_color", "TEXT DEFAULT '#5865F2'"),
        ("enabled_features", "TEXT DEFAULT '제품 구매 충전 정보'")
    ]
    
    for col_name, col_type in columns:
        try:
            c.execute(f"ALTER TABLE info ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass # 이미 컬럼이 존재하면 무시

    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            stock INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    return path


# ── 라이센스 키 생성 ────────────────────────────────────
def generate_license_key() -> str:
    def rand(n):
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))
    return f"VOUT-{rand(6)}-{rand(4)}-{rand(4)}"


def is_key_duplicate(key: str) -> bool:
    conn = sqlite3.connect(LICENSE_DB)
    c = conn.cursor()
    c.execute("SELECT 1 FROM licenses WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result is not None


def create_unique_key() -> str:
    while True:
        key = generate_license_key()
        if not is_key_duplicate(key):
            return key


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ══════════════════════════════════════════════════════
# Simple Layout
# ══════════════════════════════════════════════════════

class SimpleLayout(discord.ui.LayoutView):
    def __init__(self, title: str, body: str, color: discord.Color):
        super().__init__()
        self.container = discord.ui.Container(
            discord.ui.TextDisplay(content=title),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=body),
            accent_color=color,
        )
        self.add_item(self.container)


class RegisterConfirmLayout(discord.ui.LayoutView):
    def __init__(self, key: str, days: int, expires: str, guild_name: str):
        super().__init__(timeout=None)
        self.license_key = key
        self.days = days
        self.expires = expires
        self.guild_name = guild_name

        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## 서버 등록 확인"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(
                content=(
                    f"> **라이센스:** `{key}`\n"
                    f"> **서버:** {guild_name}\n"
                    f"> **기간:** {days}일\n"
                    f"> **만료일:** {expires}\n"
                    "이 서버에 등록하시겠습니까?"
                )
            ),
            accent_color=discord.Color.from_str("#5865F2"),
        )

        btn_confirm = discord.ui.Button(label="진행", style=discord.ButtonStyle.primary)
        btn_confirm.callback = self.confirm_callback

        btn_cancel = discord.ui.Button(label="취소", style=discord.ButtonStyle.secondary)
        btn_cancel.callback = self.cancel_callback

        action_row = discord.ui.ActionRow(btn_confirm, btn_cancel)
        container.add_item(action_row)
        self.add_item(container)

    async def confirm_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            conn = sqlite3.connect(LICENSE_DB)
            c = conn.cursor()
            c.execute("SELECT used FROM licenses WHERE key = ?", (self.license_key,))
            row = c.fetchone()

            if not row or row[0] == 1:
                conn.close()
                await interaction.edit_original_response(
                    view=SimpleLayout("## 등록 실패", "이미 사용된 라이센스이거나 유효하지 않습니다", discord.Color.red())
                )
                return

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            guild = interaction.guild

            c.execute(
                "UPDATE licenses SET used = 1, guild_id = ?, guild_name = ?, expires_at = ? WHERE key = ?",
                (str(guild.id), guild.name, self.expires, self.license_key)
            )
            conn.commit()
            conn.close()

            db_path = init_guild_db(str(guild.id), guild.name)
            with sqlite3.connect(db_path) as guild_conn:
                gc = guild_conn.cursor()
                gc.execute(
                    "INSERT OR REPLACE INTO info (guild_id, guild_name, license_key, registered_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                    (str(guild.id), guild.name, self.license_key, now, self.expires)
                )

            await interaction.edit_original_response(
                view=SimpleLayout(
                    "## 서버 등록 완료",
                    f"> **서버:** {guild.name}\n> **기간:** {self.days}일\n> **만료일:** {self.expires}\n`/설정`으로 자판기를 커스터마이징하세요",
                    discord.Color.green()
                )
            )

        except Exception as e:
            print(f"[등록 진행 오류] {e}")
            await interaction.edit_original_response(
                view=SimpleLayout("## 오류 발생", "처리 중 문제가 발생했습니다", discord.Color.red())
            )

    async def cancel_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.edit_original_response(
            view=SimpleLayout(
                "## 서버 등록 취소",
                "서버 등록이 취소되었습니다.\n다시 등록하려면 `/등록` 명령어를 사용하세요",
                discord.Color.from_str("#99AAB5")
            )
        )

class VendingSettingModal(discord.ui.Modal, title="자판기 설정"):
    title_input = discord.ui.TextInput(
        label="자판기 제목",
        placeholder="예: 구매하기",
        required=True,
        max_length=100,
    )
    desc_input = discord.ui.TextInput(
        label="자판기 설명",
        style=discord.TextStyle.long,
        placeholder="설명을 입력하세요",
        required=False,
        max_length=500,
    )
    color_input = discord.ui.TextInput(
        label="컨테이너 색상 (HEX 코드)",
        placeholder="예: #FFFFFF 또는 FFFFFF",
        required=True,
        max_length=7,
    )
    feature_select = discord.ui.Select(
        placeholder="활성화할 버튼들을 선택하세요",
        min_values=1,
        max_values=4,
        required=True,   # Modal 전용, discord.py 2.6+
        options=[
            discord.SelectOption(label="제품", value="제품"),
            discord.SelectOption(label="구매", value="구매"),
            discord.SelectOption(label="충전", value="충전"),
            discord.SelectOption(label="정보", value="정보"),
        ]
    )

    async def on_submit(self, interaction: discord.Interaction):
        hex_color = self.color_input.value.strip().replace(" ", "")
        if not hex_color.startswith("#"):
            hex_color = f"#{hex_color}"
        try:
            final_color = discord.Color.from_str(hex_color)
        except:
            hex_color = "#5865F2"
            final_color = discord.Color.from_str(hex_color)

        selected_values = self.feature_select.values
        enabled_str = " ".join(selected_values)

        safe_name = "".join(c for c in interaction.guild.name if c.isalnum() or c in (" ", "_", "-")).strip()
        db_path = os.path.join(DB_DIR, f"{safe_name}.db")

        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE info 
                SET vending_title = ?, vending_description = ?, accent_color = ?, enabled_features = ?
                WHERE guild_id = ?
            """, (self.title_input.value, self.desc_input.value, hex_color, enabled_str, str(interaction.guild.id)))

        await interaction.response.send_message(
            view=SimpleLayout(
                "## 설정 저장 완료",
                f"> **색상:** `{hex_color}`\n> **활성 버튼:** `{enabled_str}`",
                final_color
            ),
            ephemeral=True
        )

# ==================== /자판기 명령어 ====================
@bot.tree.command(name="자판기", description="자판기를 전송합니다")
async def vending_machine(interaction: discord.Interaction):
    # 길드 DB 초기화 체크 (컬럼 자동 추가 포함)
    init_guild_db(str(interaction.guild.id), interaction.guild.name)
    
    safe_name = "".join(c for c in interaction.guild.name if c.isalnum() or c in (" ", "_", "-")).strip()
    db_path = os.path.join(DB_DIR, f"{safe_name}.db")

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT vending_title, vending_description, accent_color, enabled_features FROM info WHERE guild_id = ?", 
                  (str(interaction.guild.id),))
        row = c.fetchone()

    if not row:
        await interaction.response.send_message(
            view=SimpleLayout("## 등록되지 않은 서버", "먼저 `/등록` 명령어로 서버를 등록해주세요", discord.Color.red()),
            ephemeral=True
        )
        return

    title, description, color_str, enabled_features = row
    title = title or "구매하기"
    description = description or "아래 버튼을 눌러 이용해주세요"
    color_str = color_str or "#5865F2"
    enabled = enabled_features.split() if enabled_features else []

    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"## {title}"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        accent_color=discord.Color.from_str(color_str),
    )

    if description:
        container.add_item(discord.ui.TextDisplay(content=description))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

    buttons = []
    if "구매" in enabled:
        buttons.append(discord.ui.Button(label="구매", style=discord.ButtonStyle.secondary, custom_id="vending_buy", emoji="<:emoji_48:1498298170281558058>"))
    if "제품" in enabled:
        buttons.append(discord.ui.Button(label="제품", style=discord.ButtonStyle.secondary, custom_id="vending_products", emoji="<:emoji_46:1498296760483709029>"))
    if "충전" in enabled:
        buttons.append(discord.ui.Button(label="충전", style=discord.ButtonStyle.secondary, custom_id="vending_charge", emoji="<:emoji_46:1498297238630305903>"))
    if "정보" in enabled:
        buttons.append(discord.ui.Button(label="정보", style=discord.ButtonStyle.secondary, custom_id="vending_info", emoji="<:emoji_47:1498298137406738483>"))

    if buttons:
        container.add_item(discord.ui.ActionRow(*buttons))

    view.add_item(container)
    await interaction.response.send_message(view=view, ephemeral=False)


# ==================== 설정 명령어 ====================
@bot.tree.command(name="설정", description="자판기 설정을 관리합니다")
async def settings(interaction: discord.Interaction):
    init_guild_db(str(interaction.guild.id), interaction.guild.name)
    
    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 설정하기"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="아래 드롭바를 선택하여 설정을 진행해주세요"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        accent_color=discord.Color.from_str("#5865F2"),
    )

    select = discord.ui.Select(
        placeholder="설정할 항목을 선택하세요",
        options=[
            discord.SelectOption(label="자판기 설정", value="vending_setting", description="자판기 제목, 설명, 색상, 버튼 기능을 설정합니다"),
        ]
    )
    
    async def select_callback(i: discord.Interaction):
        await i.response.send_modal(VendingSettingModal())
        
    select.callback = select_callback
    container.add_item(discord.ui.ActionRow(select))
    view.add_item(container)

    await interaction.response.send_message(view=view, ephemeral=True)

@bot.tree.command(name="라이센스_생성", description="라이센스 키를 생성합니다")
@app_commands.describe(기간="라이센스 기간 선택", 수량="생성할 수량 (최대 100개)")
@app_commands.choices(기간=[
    app_commands.Choice(name="7일",  value=7),
    app_commands.Choice(name="30일", value=30),
    app_commands.Choice(name="60일", value=60),
    app_commands.Choice(name="90일", value=90),
])
async def create_license(interaction: discord.Interaction, 기간: app_commands.Choice[int], 수량: int):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message(
            view=SimpleLayout("## 권한 없음", "이 명령어는 봇 관리자만 사용할 수 있습니다", discord.Color.red()),
            ephemeral=True
        )
        return

    if not 1 <= 수량 <= 100:
        await interaction.response.send_message(
            view=SimpleLayout("## 잘못된 수량", "수량은 1개 이상 100개 이하로 입력해주세요", discord.Color.red()),
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    conn = sqlite3.connect(LICENSE_DB)
    c = conn.cursor()
    keys = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for _ in range(수량):
        key = create_unique_key()
        c.execute("INSERT INTO licenses (key, days, created_at) VALUES (?, ?, ?)", (key, 기간.value, now))
        keys.append(key)

    conn.commit()
    conn.close()

    txt = f"VOUT 라이센스 키 목록\n생성일시: {now}\n기간: {기간.value}일 / 수량: {수량}개\n"
    txt += "=" * 50 + "\n\n"
    for i, key in enumerate(keys, 1):
        txt += f"{i:>3}. {key}\n"

    fname = f"licenses_{기간.value}일_{수량}개_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    file_bytes = io.BytesIO(txt.encode("utf-8"))
    discord_file = discord.File(fp=file_bytes, filename=fname)

    # Components V2 올바른 방식
    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 라이센스 생성 완료"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"{수량}개의 라이센스가 생성되었습니다\n아래 파일을 내려받아 확인하세요"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.File(f"attachment://{fname}"),   # ← 핵심 수정
        accent_color=discord.Color.green()
    )
    view.add_item(container)

    await interaction.followup.send(view=view, file=discord_file, ephemeral=True)


@bot.tree.command(name="라이센스_목록", description="발급된 라이센스 키 목록을 조회합니다")
@app_commands.describe(필터="조회할 상태 필터")
@app_commands.choices(필터=[
    app_commands.Choice(name="전체",   value="all"),
    app_commands.Choice(name="미사용", value="unused"),
    app_commands.Choice(name="사용됨", value="used"),
])
async def list_licenses(interaction: discord.Interaction, 필터: app_commands.Choice[str] = None):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message(
            view=SimpleLayout("## 권한 없음", "이 명령어는 봇 관리자만 사용할 수 있습니다", discord.Color.red()),
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    conn = sqlite3.connect(LICENSE_DB)
    c = conn.cursor()

    filter_val = 필터.value if 필터 else "all"
    if filter_val == "unused":
        c.execute("SELECT key, days, used, guild_name, created_at FROM licenses WHERE used = 0")
    elif filter_val == "used":
        c.execute("SELECT key, days, used, guild_name, created_at FROM licenses WHERE used = 1")
    else:
        c.execute("SELECT key, days, used, guild_name, created_at FROM licenses")

    rows = c.fetchall()
    conn.close()

    filter_label = {"all": "전체", "unused": "미사용", "used": "사용됨"}.get(filter_val, "전체")

    if not rows:
        await interaction.followup.send(
            view=SimpleLayout(f"## 라이센스 목록 [{filter_label}]", "조회된 라이센스가 없습니다", discord.Color.from_str("#5865F2")),
            ephemeral=True
        )
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txt = f"VOUT 라이센스 목록 [{filter_label}]\n조회일시: {now} / 총 {len(rows)}개\n"
    txt += "=" * 60 + "\n\n"
    for i, (key, days, used, guild_name, created_at) in enumerate(rows, 1):
        status = f"사용됨 ({guild_name})" if used else "미사용"
        txt += f"{i:>3}. {key}  |  {days}일  |  {status}  |  생성: {created_at}\n"

    fname = f"license_list_{filter_val}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    file_bytes = io.BytesIO(txt.encode("utf-8"))
    discord_file = discord.File(fp=file_bytes, filename=fname)

    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"## 라이센스 목록 ({filter_label})"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"현재 저장된 {len(rows)}개의 라이센스 목록입니다"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.File(f"attachment://{fname}"),   # ← 핵심 수정
        accent_color=discord.Color.from_str("#5865F2")
    )
    view.add_item(container)

    await interaction.followup.send(view=view, file=discord_file, ephemeral=True)


@bot.tree.command(name="라이센스_삭제", description="라이센스 키를 삭제합니다")
@app_commands.describe(키="삭제할 라이센스 키")
async def delete_license(interaction: discord.Interaction, 키: str):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message(
            view=SimpleLayout("## 권한 없음", "이 명령어는 봇 관리자만 사용할 수 있습니다", discord.Color.red()),
            ephemeral=True
        )
        return

    conn = sqlite3.connect(LICENSE_DB)
    c = conn.cursor()
    c.execute("SELECT key, days, used, guild_name FROM licenses WHERE key = ?", (키,))
    row = c.fetchone()

    if not row:
        conn.close()
        await interaction.response.send_message(
            view=SimpleLayout("## 삭제 실패", f"키 `{키}` 를 찾을 수 없습니다.", discord.Color.red()),
            ephemeral=True
        )
        return

    key, days, used, guild_name = row
    c.execute("DELETE FROM licenses WHERE key = ?", (키,))
    conn.commit()
    conn.close()

    status = f"사용됨 (서버: {guild_name})" if used else "미사용"
    await interaction.response.send_message(
        view=SimpleLayout(
            "## 라이센스 삭제 완료",
            f"> **키:** `{key}`\n> **기간:** {days}일\n> **상태:** {status}",
            discord.Color.from_str("#5865F2")
        ),
        ephemeral=True
    )


@bot.tree.command(name="등록", description="서버를 등록합니다")
@app_commands.describe(라이센스="발급받은 라이센스 키를 입력하세요")
async def register(interaction: discord.Interaction, 라이센스: str):
    conn = sqlite3.connect(LICENSE_DB)
    c = conn.cursor()
    c.execute("SELECT key, days, used FROM licenses WHERE key = ?", (라이센스,))
    row = c.fetchone()
    conn.close()

    if not row:
        await interaction.response.send_message(
            view=SimpleLayout("## 유효하지 않은 라이센스", "입력하신 라이센스 키를 찾을 수 없습니다", discord.Color.red()),
            ephemeral=True
        )
        return

    key, days, used = row

    if used:
        await interaction.response.send_message(
            view=SimpleLayout("## 이미 사용된 라이센스", "이 라이센스 키는 이미 다른 서버에서 사용되었습니다", discord.Color.red()),
            ephemeral=True
        )
        return

    expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    await interaction.response.send_message(
        view=RegisterConfirmLayout(
            key=라이센스,
            days=days,
            expires=expires,
            guild_name=interaction.guild.name
        ),
        ephemeral=True
    )


# ── 봇 이벤트 ──────────────────────────────────────────
@bot.event
async def on_ready():
    init_license_db()
    bot.add_view(RegisterConfirmLayout("", 0, "", "")) 
    await bot.tree.sync()
    print(f"{bot.user} 온라인")

bot.run(TOKEN)
