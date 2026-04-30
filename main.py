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


# ==================== 자판기 설정 Modal ====================
class VendingSettingModal(discord.ui.Modal, title="자판기 설정"):
    def __init__(self):
        super().__init__()

        # 텍스트 입력 아이템들
        self.title_input = discord.ui.TextInput(
            label="자판기 제목",
            placeholder="예: 구매하기",
            required=True,
            max_length=100,
        )
        self.desc_input = discord.ui.TextInput(
            label="자판기 설명",
            style=discord.TextStyle.long,
            placeholder="자판기 하단에 표시될 설명을 입력하세요 (선택 사항)",
            required=False,
            max_length=500,
        )
        self.color_input = discord.ui.TextInput(
            label="컨테이너 색상",
            placeholder="노랑, 초록, 빨강, 파랑, 흰색, 검정, 하늘색 등",
            required=True,
            max_length=30,
        )

        # 이미지에서 요청하신 CheckboxGroup 방식 (V2 전용)
        self.checkbox_group = discord.ui.CheckboxGroup(
            label="버튼 표시 선택",
            custom_id="enabled_features",
            options=[
                discord.ui.CheckboxGroupOption(label="제품", value="제품", default=True),
                discord.ui.CheckboxGroupOption(label="구매", value="구매", default=True),
                discord.ui.CheckboxGroupOption(label="충전", value="충전", default=True),
                discord.ui.CheckboxGroupOption(label="정보", value="정보", default=True),
            ]
        )

        self.add_item(self.title_input)
        self.add_item(self.desc_input)
        self.add_item(self.color_input)
        self.add_item(self.checkbox_group)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            title = self.title_input.value.strip() or "구매하기"
            description = self.desc_input.value.strip() if self.desc_input.value else "아래 버튼을 눌러 이용해주세요"
            color_in = self.color_input.value.strip().lower()

            color_map = {
                "노랑": "#FEE75C", "노란색": "#FEE75C", "yellow": "#FEE75C",
                "초록": "#57F287", "녹색": "#57F287", "green": "#57F287",
                "빨강": "#ED4245", "빨간색": "#ED4245", "red": "#ED4245",
                "파랑": "#5865F2", "블루": "#5865F2", "blue": "#5865F2",
                "하늘": "#00B0F4", "하늘색": "#00B0F4", "sky": "#00B0F4",
                "흰색": "#FFFFFF", "white": "#FFFFFF",
                "검정": "#000000", "검은색": "#000000", "black": "#000000",
                "보라": "#B23AEE", "purple": "#B23AEE",
                "주황": "#FFAA00", "orange": "#FFAA00",
                "핑크": "#FF69B4", "pink": "#FF69B4",
                "회색": "#99AAB5", "gray": "#99AAB5",
            }

            color_str = color_map.get(color_in, color_in if color_in.startswith("#") else "#5865F2")
            
            # 체크된 기능 가져오기
            enabled_str = " ".join(self.checkbox_group.values) if self.checkbox_group.values else "제품 구매 충전 정보"

            safe_name = "".join(c for c in interaction.guild.name if c.isalnum() or c in (" ", "_", "-")).strip()
            db_path = os.path.join(DB_DIR, f"{safe_name}.db")

            with sqlite3.connect(db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE info 
                    SET vending_title = ?, vending_description = ?, accent_color = ?, enabled_features = ?
                    WHERE guild_id = ?
                """, (title, description, color_str, enabled_str, str(interaction.guild.id)))
                conn.commit()

            await interaction.response.send_message(
                embed=discord.Embed(title="설정이 저장되었습니다", color=discord.Color.from_str(color_str)),
                ephemeral=True
            )

        except Exception as e:
            print(f"[Modal 오류] {e}")
            await interaction.response.send_message("설정 저장 중 오류가 발생했습니다", ephemeral=True)


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
    if "제품" in enabled:
        buttons.append(discord.ui.Button(label="제품", style=discord.ButtonStyle.primary, custom_id="vending_products"))
    if "구매" in enabled:
        buttons.append(discord.ui.Button(label="구매", style=discord.ButtonStyle.success, custom_id="vending_buy"))
    if "충전" in enabled:
        buttons.append(discord.ui.Button(label="충전", style=discord.ButtonStyle.green, custom_id="vending_charge"))
    if "정보" in enabled:
        buttons.append(discord.ui.Button(label="정보", style=discord.ButtonStyle.secondary, custom_id="vending_info"))

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

# ── 라이센스 관리 명령어들 (유지) ────────────────────────
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
        await interaction.response.send_message(view=SimpleLayout("## 권한 없음", "봇 관리자 전용", discord.Color.red()), ephemeral=True)
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

    txt = f"VOUT 키 목록\n기간: {기간.value}일\n" + "\n".join(keys)
    file_bytes = io.BytesIO(txt.encode("utf-8"))
    discord_file = discord.File(fp=file_bytes, filename="licenses.txt")

    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 생성 완료"),
        discord.ui.File("attachment://licenses.txt"),
        accent_color=discord.Color.green()
    )
    view.add_item(container)
    await interaction.followup.send(view=view, file=discord_file, ephemeral=True)

@bot.tree.command(name="등록", description="서버를 등록합니다")
async def register(interaction: discord.Interaction, 라이센스: str):
    conn = sqlite3.connect(LICENSE_DB)
    c = conn.cursor()
    c.execute("SELECT key, days, used FROM licenses WHERE key = ?", (라이센스,))
    row = c.fetchone()
    conn.close()

    if not row or row[2]:
        await interaction.response.send_message("유효하지 않거나 이미 사용된 키입니다.", ephemeral=True)
        return

    expires = (datetime.now() + timedelta(days=row[1])).strftime("%Y-%m-%d %H:%M:%S")
    await interaction.response.send_message(
        view=RegisterConfirmLayout(라이센스, row[1], expires, interaction.guild.name),
        ephemeral=True
    )

@bot.event
async def on_ready():
    init_license_db()
    await bot.tree.sync()
    print(f"{bot.user} 온라인")

bot.run(TOKEN)
