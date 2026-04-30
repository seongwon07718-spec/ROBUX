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
TOKEN = "YOUR_BOT_TOKEN"
ADMIN_IDS = [123456789]  # 봇 운영자 디스코드 ID 목록
DB_DIR = "DB"
LICENSE_DB = os.path.join(DB_DIR, "라이센스.db")
# ──────────────────────────────────────────────────────

os.makedirs(DB_DIR, exist_ok=True)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


# ── DB 초기화 ──────────────────────────────────────────
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS info (
            guild_id TEXT PRIMARY KEY,
            guild_name TEXT,
            license_key TEXT,
            registered_at TEXT,
            expires_at TEXT
        )
    """)
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
# Components V2 LayoutView 클래스들
# ══════════════════════════════════════════════════════

class SimpleLayout(discord.ui.LayoutView):
    """텍스트 2블록 단순 메시지"""
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
    """등록 확인 - 버튼 포함"""
    def __init__(self, key: str, days: int, expires: str, guild_name: str):
        super().__init__()
        self.license_key = key
        self.days = days
        self.expires = expires

        self.container = discord.ui.Container(
            discord.ui.TextDisplay(content="## 서버 등록 확인"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(
                content=(
                    f"> **라이센스:** `{key}`\n"
                    f"> **서버:** {guild_name}\n"
                    f"> **기간:** {days}일\n"
                    f"> **만료일:** {expires}\n\n"
                    "**이 서버에 등록하시겠습니까?**"
                )
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(
                discord.ui.Button(label="진행", style=discord.ButtonStyle.primary,   custom_id="reg_confirm"),
                discord.ui.Button(label="취소", style=discord.ButtonStyle.secondary, custom_id="reg_cancel"),
            ),
            accent_color=discord.Color.from_str("#5865F2"),
        )
        self.add_item(self.container)

    @discord.ui.button(label="진행", style=discord.ButtonStyle.primary, custom_id="reg_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = sqlite3.connect(LICENSE_DB)
        c = conn.cursor()
        c.execute("SELECT used FROM licenses WHERE key = ?", (self.license_key,))
        row = c.fetchone()

        if not row or row[0]:
            conn.close()
            await interaction.response.edit_message(
                view=SimpleLayout("## 등록 실패", "이미 사용된 라이센스이거나 유효하지 않습니다.", discord.Color.red())
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
        guild_conn = sqlite3.connect(db_path)
        gc = guild_conn.cursor()
        gc.execute(
            "INSERT OR REPLACE INTO info VALUES (?, ?, ?, ?, ?)",
            (str(guild.id), guild.name, self.license_key, now, self.expires)
        )
        guild_conn.commit()
        guild_conn.close()

        await interaction.response.edit_message(
            view=SimpleLayout(
                "## 등록 완료",
                (
                    f"> **서버:** {guild.name}\n"
                    f"> **기간:** {self.days}일\n"
                    f"> **만료일:** {self.expires}\n\n"
                    "자판기 봇이 이 서버에 정상적으로 등록되었습니다."
                ),
                discord.Color.green()
            )
        )

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, custom_id="reg_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            view=SimpleLayout(
                "## 등록 취소",
                "등록이 취소되었습니다.\n다시 등록하려면 `/등록` 명령어를 사용하세요.",
                discord.Color.from_str("#99AAB5")
            )
        )


# ══════════════════════════════════════════════════════
# 슬래시 명령어
# ══════════════════════════════════════════════════════

@bot.tree.command(name="라이센스생성", description="[관리자] 라이센스 키를 생성합니다.")
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
            view=SimpleLayout("## 권한 없음", "이 명령어는 봇 관리자만 사용할 수 있습니다.", discord.Color.red()),
            ephemeral=True
        )
        return

    if 수량 < 1 or 수량 > 100:
        await interaction.response.send_message(
            view=SimpleLayout("## 잘못된 수량", "수량은 1개 이상 100개 이하로 입력해주세요.", discord.Color.red()),
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

    txt = "VOUT 라이센스 키 목록\n"
    txt += f"생성일시: {now}\n"
    txt += f"기간: {기간.value}일 / 수량: {수량}개\n"
    txt += "=" * 40 + "\n\n"
    for i, key in enumerate(keys, 1):
        txt += f"{i:>3}. {key}\n"

    fname = f"licenses_{기간.value}일_{수량}개_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    file = discord.File(fp=io.BytesIO(txt.encode("utf-8")), filename=fname)

    await interaction.followup.send(file=file, ephemeral=True)


@bot.tree.command(name="라이센스삭제", description="[관리자] 라이센스 키를 삭제합니다.")
@app_commands.describe(키="삭제할 라이센스 키")
async def delete_license(interaction: discord.Interaction, 키: str):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message(
            view=SimpleLayout("## 권한 없음", "이 명령어는 봇 관리자만 사용할 수 있습니다.", discord.Color.red()),
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


@bot.tree.command(name="라이센스목록", description="[관리자] 발급된 라이센스 키 목록을 조회합니다.")
@app_commands.describe(필터="조회할 상태 필터")
@app_commands.choices(필터=[
    app_commands.Choice(name="전체",   value="all"),
    app_commands.Choice(name="미사용", value="unused"),
    app_commands.Choice(name="사용됨", value="used"),
])
async def list_licenses(interaction: discord.Interaction, 필터: app_commands.Choice[str] = None):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message(
            view=SimpleLayout("## 권한 없음", "이 명령어는 봇 관리자만 사용할 수 있습니다.", discord.Color.red()),
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
            view=SimpleLayout(
                f"## 라이센스 목록 [{filter_label}]",
                "조회된 라이센스가 없습니다.",
                discord.Color.from_str("#5865F2")
            ),
            ephemeral=True
        )
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txt = f"VOUT 라이센스 목록 [{filter_label}]\n"
    txt += f"조회일시: {now} / 총 {len(rows)}개\n"
    txt += "=" * 60 + "\n\n"
    for i, (key, days, used, guild_name, created_at) in enumerate(rows, 1):
        status = f"사용됨 ({guild_name})" if used else "미사용"
        txt += f"{i:>3}. {key}  |  {days}일  |  {status}  |  생성: {created_at}\n"

    fname = f"license_list_{filter_val}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    file = discord.File(fp=io.BytesIO(txt.encode("utf-8")), filename=fname)

    await interaction.followup.send(file=file, ephemeral=True)


@bot.tree.command(name="등록", description="라이센스 키를 입력해 이 서버에 봇을 등록합니다.")
@app_commands.describe(라이센스="발급받은 라이센스 키를 입력하세요 (예: VOUT-XXXXXX-XXXX-XXXX)")
async def register(interaction: discord.Interaction, 라이센스: str):
    conn = sqlite3.connect(LICENSE_DB)
    c = conn.cursor()
    c.execute("SELECT key, days, used FROM licenses WHERE key = ?", (라이센스,))
    row = c.fetchone()
    conn.close()

    if not row:
        await interaction.response.send_message(
            view=SimpleLayout(
                "## 유효하지 않은 라이센스",
                "입력하신 라이센스 키를 찾을 수 없습니다.\n키를 다시 확인해주세요.",
                discord.Color.red()
            ),
            ephemeral=True
        )
        return

    key, days, used = row

    if used:
        await interaction.response.send_message(
            view=SimpleLayout(
                "## 이미 사용된 라이센스",
                "이 라이센스 키는 이미 다른 서버에서 사용되었습니다.",
                discord.Color.red()
            ),
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
    await bot.tree.sync()
    print(f"{bot.user} 온라인 | 슬래시 명령어 동기화 완료")


bot.run(TOKEN)
