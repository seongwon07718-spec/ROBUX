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
ADMIN_IDS = [1454398431996018724]
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
            expires_at TEXT,
            vending_title TEXT DEFAULT "VOUT 자판기",
            vending_description TEXT DEFAULT "",
            accent_color TEXT DEFAULT "#5865F2",
            enabled_features TEXT DEFAULT "products buy charge info"
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
                    f"> **만료일:** {expires}\n\n"
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
                    f"> **서버:** {guild.name}\n> **기간:** {self.days}일\n> **만료일:** {self.expires}\n\n`/설정` 명령어로 자판기를 커스터마이징 할 수 있습니다.",
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
                "서버 등록이 취소되었습니다.\n다시 등록하려면 `/등록` 명령어를 사용하세요.",
                discord.Color.from_str("#99AAB5")
            )
        )


# ==================== 자판기 설정 Modal ====================
class VendingSettingModal(discord.ui.Modal, title="자판기 설정"):
    def __init__(self):
        super().__init__()

        self.add_item(discord.ui.TextInput(
            label="자판기 제목",
            placeholder="예: VOUT 자동 자판기",
            required=True,
            max_length=100,
            custom_id="title"
        ))

        self.add_item(discord.ui.TextInput(
            label="자판기 설명",
            style=discord.TextStyle.long,
            placeholder="자판기 하단에 표시될 설명을 입력하세요.",
            required=False,
            max_length=500,
            custom_id="description"
        ))

        self.add_item(discord.ui.TextInput(
            label="컨테이너 색상",
            placeholder="#5865F2 또는 ffffff 또는 흰색",
            required=True,
            max_length=20,
            custom_id="color"
        ))

        # Checkbox Group (Discord 최신 기능)
        self.add_item(discord.ui.CheckboxGroup(
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
            title = self.children[0].value.strip()
            description = self.children[1].value.strip() if self.children[1].value else ""
            color_input = self.children[2].value.strip()

            # 색상 파싱
            try:
                if color_input.startswith("#"):
                    accent_color = discord.Color.from_str(color_input)
                    color_str = color_input
                else:
                    color_map = {"흰색": "#ffffff", "white": "#ffffff", "검정": "#000000", "black": "#000000"}
                    hex_color = color_map.get(color_input.lower(), color_input)
                    if not hex_color.startswith("#"):
                        hex_color = "#" + hex_color
                    accent_color = discord.Color.from_str(hex_color)
                    color_str = hex_color
            except:
                accent_color = discord.Color.from_str("#5865F2")
                color_str = "#5865F2"

            # 체크된 기능 가져오기
            enabled = []
            for checkbox in self.children[3].values:
                if checkbox.selected:
                    enabled.append(checkbox.label.lower())

            enabled_str = " ".join(enabled) if enabled else "products buy charge info"

            # 서버 DB에 저장
            safe_name = "".join(c for c in interaction.guild.name if c.isalnum() or c in (" ", "_", "-")).strip()
            db_path = os.path.join(DB_DIR, f"{safe_name}.db")

            with sqlite3.connect(db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE info SET 
                        vending_title = ?,
                        vending_description = ?,
                        accent_color = ?,
                        enabled_features = ?
                    WHERE guild_id = ?
                """, (title, description, color_str, enabled_str, str(interaction.guild.id)))
                conn.commit()

            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ 자판기 설정 저장 완료",
                    description=f"**제목:** {title}\n**색상:** {color_str}\n**표시 기능:** {', '.join([e.capitalize() for e in enabled]) or '기본값'}",
                    color=accent_color
                ),
                ephemeral=True
            )

        except Exception as e:
            print(f"[Modal 저장 오류] {e}")
            await interaction.response.send_message("설정 저장 중 오류가 발생했습니다.", ephemeral=True)


# ── 설정 명령어 ──────────────────────────────────────────
@bot.tree.command(name="설정", description="자판기 설정을 관리합니다")
async def settings(interaction: discord.Interaction):
    safe_name = "".join(c for c in interaction.guild.name if c.isalnum() or c in (" ", "_", "-")).strip()
    db_path = os.path.join(DB_DIR, f"{safe_name}.db")
    
    if not os.path.exists(db_path):
        await interaction.response.send_message(
            view=SimpleLayout("## 등록되지 않음", "먼저 `/등록` 명령어로 서버를 등록해주세요.", discord.Color.red()),
            ephemeral=True
        )
        return

    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 자판기 설정"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="자판기 제목, 설명, 색상, 표시 기능을 설정합니다."),
        accent_color=discord.Color.from_str("#5865F2"),
    )

    select = discord.ui.Select(
        placeholder="설정할 항목을 선택하세요...",
        options=[
            discord.SelectOption(label="자판기 설정", value="vending_setting", description="제목, 설명, 색상, 버튼 설정"),
        ]
    )
    select.callback = lambda i: i.response.send_modal(VendingSettingModal())
    container.add_item(discord.ui.ActionRow(select))
    view.add_item(container)

    await interaction.response.send_message(view=view, ephemeral=True)


# ── 기타 명령어들 (기존 유지) ─────────────────────────────────
# (라이센스_생성, 라이센스_목록, 라이센스_삭제, 등록 명령어는 그대로 유지)


# ── 봇 이벤트 ──────────────────────────────────────────
@bot.event
async def on_ready():
    init_license_db()
    bot.add_view(RegisterConfirmLayout("", 0, "", ""))
    await bot.tree.sync()
    print(f"{bot.user} 온라인 | 슬래시 명령어 동기화 완료")


bot.run(TOKEN)
