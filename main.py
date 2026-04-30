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
    c.execute("""
        CREATE TABLE IF NOT EXISTS info (
            guild_id TEXT PRIMARY KEY,
            guild_name TEXT,
            license_key TEXT,
            registered_at TEXT,
            expires_at TEXT,
            vending_title TEXT DEFAULT "구매하기",
            vending_description TEXT DEFAULT "아래 버튼을 눌러 이용해주세요",
            accent_color TEXT DEFAULT "#5865F2",
            enabled_features TEXT DEFAULT "제품 구매 충전 정보"
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
                    "INSERT OR REPLACE INTO info VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (str(guild.id), guild.name, self.license_key, now, self.expires, None, None, None, None)
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

        self.add_item(discord.ui.TextInput(
            label="자판기 제목",
            placeholder="예: 구매하기",
            required=True,
            max_length=100,
        ))

        self.add_item(discord.ui.TextInput(
            label="자판기 설명",
            style=discord.TextStyle.long,
            placeholder="자판기 하단에 표시될 설명을 입력하세요 (선택 사항)",
            required=False,
            max_length=500,
        ))

        self.add_item(discord.ui.TextInput(
            label="컨테이너 색상",
            placeholder="노랑, 초록, 빨강, 파랑, 흰색, 검정, 하늘색 등",
            required=True,
            max_length=30,
        ))

        self.add_item(discord.ui.CheckboxGroup(
            label="버튼 표시 선택",   # ← 요청하신 대로 변경
            custom_id="enabled_features",
            options=[
                discord.ui.Checkbox(label="제품", default=True),
                discord.ui.Checkbox(label="구매", default=True),
                discord.ui.Checkbox(label="충전", default=True),
                discord.ui.Checkbox(label="정보", default=True),
            ]
        ))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            title = self.children[0].value.strip() or "구매하기"
            description = self.children[1].value.strip() if self.children[1].value else "아래 버튼을 눌러 이용해주세요"
            color_input = self.children[2].value.strip().lower()

            # 색상 변환 강화
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

            try:
                if color_input.startswith("#"):
                    color_str = color_input.upper()
                elif color_input in color_map:
                    color_str = color_map[color_input]
                else:
                    cleaned = color_input.lstrip("#")
                    if len(cleaned) in (6, 8):
                        color_str = "#" + cleaned.upper()
                    else:
                        color_str = "#5865F2"
                accent_color = discord.Color.from_str(color_str)
            except:
                color_str = "#5865F2"
                accent_color = discord.Color.from_str("#5865F2")

            # 체크된 기능
            enabled = []
            for checkbox in self.children[3].values:
                if checkbox.selected:
                    enabled.append(checkbox.label.lower())

            enabled_str = " ".join(enabled) if enabled else "제품 구매 충전 정보"

            # 서버 DB 저장
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
                embed=discord.Embed(title="설정이 저장되었습니다", color=accent_color),
                ephemeral=True
            )

        except Exception as e:
            print(f"[Modal 오류] {e}")
            await interaction.response.send_message("설정 저장 중 오류가 발생했습니다", ephemeral=True)


# ==================== /자판기 명령어 ====================
@bot.tree.command(name="자판기", description="자판기를 전송합니다")
async def vending_machine(interaction: discord.Interaction):
    safe_name = "".join(c for c in interaction.guild.name if c.isalnum() or c in (" ", "_", "-")).strip()
    db_path = os.path.join(DB_DIR, f"{safe_name}.db")

    if not os.path.exists(db_path):
        await interaction.response.send_message(
            view=SimpleLayout("## 등록되지 않은 서버", "먼저 `/등록` 명령어로 서버를 등록해주세요", discord.Color.red()),
            ephemeral=True
        )
        return

    # 설정 불러오기
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT vending_title, vending_description, accent_color, enabled_features FROM info WHERE guild_id = ?", 
                  (str(interaction.guild.id),))
        row = c.fetchone()

    if not row:
        title = "구매하기"
        description = "아래 버튼을 눌러 이용해주세요"
        color_str = "#5865F2"
        enabled_features = "제품 구매 충전 정보"
    else:
        title, description, color_str, enabled_features = row
        title = title or "구매하기"
        description = description or "아래 버튼을 눌러 이용해주세요"
        color_str = color_str or "#5865F2"

    try:
        accent_color = discord.Color.from_str(color_str)
    except:
        accent_color = discord.Color.from_str("#5865F2")

    enabled = enabled_features.lower().split() if enabled_features else []

    # 자판기 컨테이너 생성
    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"## {title}"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        accent_color=accent_color,
    )

    if description:
        container.add_item(discord.ui.TextDisplay(content=description))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

    # 체크된 버튼만 동적으로 추가
    buttons = []
    if "products" in enabled or "제품" in enabled:
        btn = discord.ui.Button(label="제품", style=discord.ButtonStyle.primary, custom_id="vending_products")
        buttons.append(btn)
    if "buy" in enabled or "구매" in enabled:
        btn = discord.ui.Button(label="구매", style=discord.ButtonStyle.success, custom_id="vending_buy")
        buttons.append(btn)
    if "charge" in enabled or "충전" in enabled:
        btn = discord.ui.Button(label="충전", style=discord.ButtonStyle.green, custom_id="vending_charge")
        buttons.append(btn)
    if "info" in enabled or "정보" in enabled:
        btn = discord.ui.Button(label="정보", style=discord.ButtonStyle.secondary, custom_id="vending_info")
        buttons.append(btn)

    if buttons:
        action_row = discord.ui.ActionRow(*buttons)
        container.add_item(action_row)

    view.add_item(container)

    await interaction.response.send_message(view=view, ephemeral=False)


# ==================== 설정 명령어 ====================
@bot.tree.command(name="설정", description="자판기 설정을 관리합니다")
async def settings(interaction: discord.Interaction):
    safe_name = "".join(c for c in interaction.guild.name if c.isalnum() or c in (" ", "_", "-")).strip()
    db_path = os.path.join(DB_DIR, f"{safe_name}.db")
    
    if not os.path.exists(db_path):
        await interaction.response.send_message(
            view=SimpleLayout("## 등록되지 않음", "먼저 `/등록` 명령어로 서버를 등록해주세요", discord.Color.red()),
            ephemeral=True
        )
        return

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
    select.callback = lambda i: i.response.send_modal(VendingSettingModal())
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
