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

os.makedirs(DB_DIR, exist_ok=True)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


# ── DB 초기화 ──────────────────────────────────────────
def init_license_db():
    conn = sqlite3.connect(LICENSE_DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS licenses (
        key TEXT PRIMARY KEY, days INTEGER NOT NULL, used INTEGER DEFAULT 0,
        guild_id TEXT, guild_name TEXT, created_at TEXT, expires_at TEXT)""")
    conn.commit()
    conn.close()


def init_guild_db(guild_id: str, guild_name: str):
    safe_name = "".join(c for c in guild_name if c.isalnum() or c in (" ", "_", "-")).strip()
    path = os.path.join(DB_DIR, f"{safe_name}.db")
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS info (
        guild_id TEXT PRIMARY KEY, guild_name TEXT, license_key TEXT,
        registered_at TEXT, expires_at TEXT,
        vending_title TEXT DEFAULT "VOUT 자판기",
        vending_description TEXT DEFAULT "",
        accent_color TEXT DEFAULT "#5865F2",
        enabled_features TEXT DEFAULT "제품 구매 충전 정보")""")
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, 
        stock INTEGER, content TEXT, created_at TEXT)""")
    conn.commit()
    conn.close()
    return path


def generate_license_key() -> str:
    def rand(n): return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))
    return f"VOUT-{rand(6)}-{rand(4)}-{rand(4)}"


def is_key_duplicate(key: str) -> bool:
    conn = sqlite3.connect(LICENSE_DB)
    c = conn.cursor()
    c.execute("SELECT 1 FROM licenses WHERE key = ?", (key,))
    return c.fetchone() is not None


def create_unique_key() -> str:
    while True:
        key = generate_license_key()
        if not is_key_duplicate(key):
            return key


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


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


# ==================== 자판기 설정 Modal (색상 최대 지원) ====================
class VendingSettingModal(discord.ui.Modal, title="자판기 설정"):
    def __init__(self):
        super().__init__()

        self.add_item(discord.ui.TextInput(label="자판기 제목", placeholder="VOUT 자동 자판기", required=True, max_length=100))
        self.add_item(discord.ui.TextInput(label="자판기 설명", style=discord.TextStyle.long, placeholder="설명을 입력하세요 (선택)", required=False, max_length=500))
        self.add_item(discord.ui.TextInput(label="컨테이너 색상", placeholder="노랑, 초록, 빨강, 파랑, 흰색, 검정, 하늘색 등", required=True, max_length=30))
        
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
        title = self.children[0].value.strip() or "VOUT 자판기"
        description = self.children[1].value.strip() if self.children[1].value else ""
        color_input = self.children[2].value.strip().lower()
        enabled = [cb.label for cb in self.children[3].values if cb.selected]
        enabled_str = " ".join(enabled) if enabled else "제품 구매 충전 정보"

        # ==================== 색상 변환 (최대한 많은 색상 지원) ====================
        color_map = {
            "노랑": "#FEE75C", "노란색": "#FEE75C", "yellow": "#FEE75C", "골드": "#FEE75C",
            "초록": "#57F287", "녹색": "#57F287", "green": "#57F287", "라임": "#57F287",
            "빨강": "#ED4245", "빨간색": "#ED4245", "red": "#ED4245",
            "파랑": "#5865F2", "블루": "#5865F2", "blue": "#5865F2",
            "하늘": "#00B0F4", "하늘색": "#00B0F4", "sky": "#00B0F4",
            "흰색": "#FFFFFF", "white": "#FFFFFF",
            "검정": "#000000", "검은색": "#000000", "black": "#000000",
            "보라": "#B23AEE", "purple": "#B23AEE", "violet": "#B23AEE",
            "주황": "#FFAA00", "orange": "#FFAA00",
            "핑크": "#FF69B4", "pink": "#FF69B4",
            "회색": "#99AAB5", "gray": "#99AAB5", "grey": "#99AAB5",
            "청록": "#1ABC9C", "teal": "#1ABC9C",
        }

        try:
            if color_input.startswith("#"):
                color_str = color_input.upper()
            elif color_input in color_map:
                color_str = color_map[color_input]
            else:
                # # 없이 hex 입력 처리
                cleaned = color_input.lstrip("#")
                if len(cleaned) in (6, 8):
                    color_str = "#" + cleaned.upper()
                else:
                    color_str = "#5865F2"
            accent_color = discord.Color.from_str(color_str)
        except:
            color_str = "#5865F2"
            accent_color = discord.Color.from_str("#5865F2")

        # DB 저장
        safe_name = "".join(c for c in interaction.guild.name if c.isalnum() or c in (" ", "_", "-")).strip()
        db_path = os.path.join(DB_DIR, f"{safe_name}.db")

        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("""UPDATE info SET 
                vending_title=?, vending_description=?, accent_color=?, enabled_features=?
                WHERE guild_id=?""", 
                (title, description, color_str, enabled_str, str(interaction.guild.id)))
            conn.commit()

        await interaction.response.send_message(
            embed=discord.Embed(title="✅ 설정 저장 완료", color=accent_color), 
            ephemeral=True
        )


# ==================== 설정 명령어 ====================
@bot.tree.command(name="설정", description="자판기 설정을 관리합니다")
async def settings(interaction: discord.Interaction):
    safe_name = "".join(c for c in interaction.guild.name if c.isalnum() or c in (" ", "_", "-")).strip()
    db_path = os.path.join(DB_DIR, f"{safe_name}.db")
    
    if not os.path.exists(db_path):
        await interaction.response.send_message(
            view=SimpleLayout("## 등록 필요", "먼저 `/등록` 명령어를 사용해주세요.", discord.Color.red()), 
            ephemeral=True
        )
        return

    await interaction.response.send_modal(VendingSettingModal())


# ==================== /자판기 명령어 ====================
@bot.tree.command(name="자판기", description="자판기를 엽니다")
async def vending_machine(interaction: discord.Interaction):
    safe_name = "".join(c for c in interaction.guild.name if c.isalnum() or c in (" ", "_", "-")).strip()
    db_path = os.path.join(DB_DIR, f"{safe_name}.db")

    if not os.path.exists(db_path):
        await interaction.response.send_message(
            view=SimpleLayout("## 등록 필요", "먼저 `/등록` 명령어를 사용해주세요.", discord.Color.red()), 
            ephemeral=True
        )
        return

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT vending_title, vending_description, accent_color, enabled_features FROM info WHERE guild_id = ?", 
                  (str(interaction.guild.id),))
        row = c.fetchone()

    title = row[0] if row and row[0] else "VOUT 자판기"
    description = row[1] if row and row[1] else ""
    color_str = row[2] if row and row[2] else "#5865F2"
    enabled_features = row[3] if row and row[3] else "제품 구매 충전 정보"

    try:
        accent_color = discord.Color.from_str(color_str)
    except:
        accent_color = discord.Color.from_str("#5865F2")

    enabled = enabled_features.lower().split()

    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"## {title}"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        accent_color=accent_color,
    )

    if description:
        container.add_item(discord.ui.TextDisplay(content=description))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

    buttons = []
    if any(x in enabled for x in ["제품", "products"]):
        buttons.append(discord.ui.Button(label="제품", style=discord.ButtonStyle.primary))
    if any(x in enabled for x in ["구매", "buy"]):
        buttons.append(discord.ui.Button(label="구매", style=discord.ButtonStyle.success))
    if any(x in enabled for x in ["충전", "charge"]):
        buttons.append(discord.ui.Button(label="충전", style=discord.ButtonStyle.green))
    if any(x in enabled for x in ["정보", "info"]):
        buttons.append(discord.ui.Button(label="정보", style=discord.ButtonStyle.secondary))

    if buttons:
        container.add_item(discord.ui.ActionRow(*buttons))

    view.add_item(container)
    await interaction.response.send_message(view=view)


# ── 봇 이벤트 ──────────────────────────────────────────
@bot.event
async def on_ready():
    init_license_db()
    await bot.tree.sync()
    print(f"{bot.user} 온라인 | 명령어 동기화 완료")


bot.run(TOKEN)
