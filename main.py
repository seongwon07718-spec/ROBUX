import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
import string
import os
import io
import re
import asyncio
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta

# ── 설정 ──────────────────────────────────────────────
TOKEN        = ""
ADMIN_IDS    = [1454398431996018724]
DB_DIR       = "DB"
LICENSE_DB   = os.path.join(DB_DIR, "라이센스.db")
FASTAPI_URL    = "https://여기에_도메인_입력"  # 본인 도메인으로 교체
WEBHOOK_SECRET = "f1356103e6b861cb00d3c502cb27d9f66bd84880f70d3b98186fdbd5cd1d840c"
# ──────────────────────────────────────────────────────

os.makedirs(DB_DIR, exist_ok=True)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 충전 대기 메시지 추적: charge_id → (message, channel_id, guild_id)
pending_charge_messages: dict[str, tuple] = {}


# ══════════════════════════════════════════════════════
# 보안 헬퍼
# ══════════════════════════════════════════════════════

def safe_guild_name(name: str) -> str:
    result = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
    return result[:64] or "unknown"

def get_guild_db_path(guild_name: str) -> str:
    safe = safe_guild_name(guild_name)
    path = os.path.abspath(os.path.join(DB_DIR, f"{safe}.db"))
    if not path.startswith(os.path.abspath(DB_DIR)):
        raise ValueError("잘못된 경로 접근 시도")
    return path

def get_guild_db_path_by_id(guild_id: str) -> str | None:
    """guild_id로 DB 경로 탐색"""
    for fname in os.listdir(DB_DIR):
        if not fname.endswith(".db") or fname == "라이센스.db":
            continue
        path = os.path.join(DB_DIR, fname)
        try:
            with sqlite3.connect(path) as conn:
                c = conn.cursor()
                c.execute("SELECT 1 FROM info WHERE guild_id = ?", (guild_id,))
                if c.fetchone():
                    return path
        except Exception:
            continue
    return None

def validate_hex_color(hex_str: str) -> str:
    hex_str = hex_str.strip().replace(" ", "")
    if not hex_str.startswith("#"):
        hex_str = f"#{hex_str}"
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", hex_str):
        return hex_str
    return "#5865F2"

def sanitize_text(text: str, max_len: int = 500) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()[:max_len]

def validate_license_key_format(key: str) -> bool:
    return bool(re.fullmatch(r"VOUT-[A-Z0-9]{6}-[A-Z0-9]{4}-[A-Z0-9]{4}", key.strip().upper()))

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def generate_charge_id() -> str:
    """충전 고유 ID 생성 (예측 불가 랜덤)"""
    return secrets.token_hex(16)

def verify_webhook_hmac(body: bytes, signature: str) -> bool:
    """FastAPI 웹훅 HMAC 서명 검증"""
    expected = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ══════════════════════════════════════════════════════
# DB 초기화
# ══════════════════════════════════════════════════════

def init_license_db():
    with sqlite3.connect(LICENSE_DB) as conn:
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


def init_guild_db(guild_id: str, guild_name: str) -> str:
    path = get_guild_db_path(guild_name)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS info (
                guild_id TEXT PRIMARY KEY,
                guild_name TEXT
            )
        """)
        columns = [
            ("license_key",         "TEXT"),
            ("registered_at",       "TEXT"),
            ("expires_at",          "TEXT"),
            ("vending_title",       "TEXT DEFAULT '구매하기'"),
            ("vending_description", "TEXT DEFAULT '아래 버튼을 눌러 이용해주세요'"),
            ("accent_color",        "TEXT DEFAULT '#5865F2'"),
            ("enabled_features",    "TEXT DEFAULT '제품 구매 충전 정보'"),
            # 계좌 설정
            ("bank_name",           "TEXT DEFAULT ''"),
            ("account_number",      "TEXT DEFAULT ''"),
            ("account_holder",      "TEXT DEFAULT ''"),
            # 충전 설정
            ("min_charge",          "INTEGER DEFAULT 1000"),
            ("charge_unit",         "INTEGER DEFAULT 1000"),
            ("shortcut_token",      "TEXT DEFAULT NULL"),
        ]
        for col_name, col_type in columns:
            try:
                c.execute(f"ALTER TABLE info ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass

        # 유저 포인트 테이블
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                points INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)

        # 충전 대기 테이블
        c.execute("""
            CREATE TABLE IF NOT EXISTS charge_pending (
                charge_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                username TEXT,
                depositor TEXT NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                completed_at TEXT DEFAULT NULL,
                channel_id TEXT DEFAULT NULL,
                message_id TEXT DEFAULT NULL
            )
        """)

        # 충전 내역 테이블
        c.execute("""
            CREATE TABLE IF NOT EXISTS charge_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                charge_id TEXT,
                user_id TEXT,
                username TEXT,
                depositor TEXT,
                amount INTEGER,
                status TEXT,
                created_at TEXT,
                completed_at TEXT
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
    return path


# ══════════════════════════════════════════════════════
# 라이센스 키 생성
# ══════════════════════════════════════════════════════

def generate_license_key() -> str:
    def rand(n):
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))
    return f"VOUT-{rand(6)}-{rand(4)}-{rand(4)}"

def is_key_duplicate(key: str) -> bool:
    with sqlite3.connect(LICENSE_DB) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM licenses WHERE key = ?", (key,))
        return c.fetchone() is not None

def create_unique_key() -> str:
    for _ in range(1000):
        key = generate_license_key()
        if not is_key_duplicate(key):
            return key
    raise RuntimeError("라이센스 키 생성 실패")


# ══════════════════════════════════════════════════════
# Components V2 클래스
# ══════════════════════════════════════════════════════

class SimpleLayout(discord.ui.LayoutView):
    def __init__(self, title: str, body: str, color: discord.Color):
        super().__init__()
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content=title),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=body),
            accent_color=color,
        ))


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
            discord.ui.TextDisplay(content=(
                f"> **라이센스:** `{key}`\n"
                f"> **서버:** {guild_name}\n"
                f"> **기간:** {days}일\n"
                f"> **만료일:** {expires}\n"
                "이 서버에 등록하시겠습니까?"
            )),
            accent_color=discord.Color.from_str("#5865F2"),
        )
        btn_confirm = discord.ui.Button(label="진행", style=discord.ButtonStyle.primary)
        btn_confirm.callback = self.confirm_callback
        btn_cancel = discord.ui.Button(label="취소", style=discord.ButtonStyle.secondary)
        btn_cancel.callback = self.cancel_callback
        container.add_item(discord.ui.ActionRow(btn_confirm, btn_cancel))
        self.add_item(container)

    async def confirm_callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("서버에서만 사용 가능합니다", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            with sqlite3.connect(LICENSE_DB) as conn:
                c = conn.cursor()
                c.execute("SELECT used FROM licenses WHERE key = ?", (self.license_key,))
                row = c.fetchone()
                if not row or row[0] == 1:
                    await interaction.edit_original_response(
                        view=SimpleLayout("## 등록 실패", "이미 사용된 라이센스이거나 유효하지 않습니다", discord.Color.red())
                    )
                    return
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                guild = interaction.guild
                c.execute(
                    "UPDATE licenses SET used = 1, guild_id = ?, guild_name = ?, expires_at = ? WHERE key = ? AND used = 0",
                    (str(guild.id), guild.name[:100], self.expires, self.license_key)
                )
                if c.rowcount == 0:
                    await interaction.edit_original_response(
                        view=SimpleLayout("## 등록 실패", "이미 사용된 라이센스입니다", discord.Color.red())
                    )
                    return
                conn.commit()

            db_path = init_guild_db(str(guild.id), guild.name)
            with sqlite3.connect(db_path) as gconn:
                gc = gconn.cursor()
                gc.execute(
                    "INSERT OR REPLACE INTO info (guild_id, guild_name, license_key, registered_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                    (str(guild.id), guild.name[:100], self.license_key, now, self.expires)
                )
                gconn.commit()

            await interaction.edit_original_response(
                view=SimpleLayout(
                    "## 서버 등록 완료",
                    f"> **서버:** {guild.name}\n> **기간:** {self.days}일\n> **만료일:** {self.expires}\n`/설정`으로 자판기를 커스터마이징하세요",
                    discord.Color.green()
                )
            )
        except ValueError as e:
            print(f"[보안 오류] {e}")
            await interaction.edit_original_response(
                view=SimpleLayout("## 오류", "비정상적인 접근이 감지되었습니다", discord.Color.red())
            )
        except Exception as e:
            print(f"[등록 오류] {e}")
            await interaction.edit_original_response(
                view=SimpleLayout("## 오류", "처리 중 문제가 발생했습니다", discord.Color.red())
            )

    async def cancel_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.edit_original_response(
            view=SimpleLayout("## 등록 취소", "서버 등록이 취소되었습니다", discord.Color.from_str("#99AAB5"))
        )


# ══════════════════════════════════════════════════════
# 자판기 설정 Modal
# ══════════════════════════════════════════════════════

class VendingSettingModal(discord.ui.Modal, title="자판기 설정"):
    title_input = discord.ui.TextInput(label="자판기 제목", placeholder="예: 구매하기", required=True, max_length=100)
    desc_input  = discord.ui.TextInput(label="자판기 설명", style=discord.TextStyle.long, placeholder="설명을 입력하세요", required=False, max_length=500)
    color_input = discord.ui.TextInput(label="컨테이너 색상 (HEX)", placeholder="예: #5865F2", required=True, max_length=7)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("서버에서만 사용 가능합니다", ephemeral=True)
            return
        title     = sanitize_text(self.title_input.value, 100)
        desc      = sanitize_text(self.desc_input.value or "", 500)
        hex_color = validate_hex_color(self.color_input.value)
        if not title:
            await interaction.response.send_message(view=SimpleLayout("## 오류", "제목을 입력해주세요", discord.Color.red()), ephemeral=True)
            return
        try:
            db_path = get_guild_db_path(interaction.guild.name)
            with sqlite3.connect(db_path) as conn:
                c = conn.cursor()
                c.execute("UPDATE info SET vending_title=?, vending_description=?, accent_color=? WHERE guild_id=?",
                          (title, desc, hex_color, str(interaction.guild.id)))
                if c.rowcount == 0:
                    await interaction.response.send_message(view=SimpleLayout("## 오류", "등록된 서버가 아닙니다. `/등록` 먼저 진행해주세요", discord.Color.red()), ephemeral=True)
                    return
                conn.commit()
            await interaction.response.send_message(
                view=SimpleLayout("## 설정 저장 완료", f"> **제목:** {title}\n> **색상:** `{hex_color}`", discord.Color.from_str(hex_color)),
                ephemeral=True
            )
        except Exception as e:
            print(f"[설정 오류] {e}")
            await interaction.response.send_message(view=SimpleLayout("## 오류", "설정 저장 중 문제가 발생했습니다", discord.Color.red()), ephemeral=True)


# ══════════════════════════════════════════════════════
# 계좌 설정 Modal
# ══════════════════════════════════════════════════════

class BankSettingModal(discord.ui.Modal, title="계좌 설정"):
    bank_input   = discord.ui.TextInput(label="은행명", placeholder="예: 카카오뱅크", required=True, max_length=20)
    number_input = discord.ui.TextInput(label="계좌번호", placeholder="예: 3333-01-1234567", required=True, max_length=30)
    holder_input = discord.ui.TextInput(label="예금주", placeholder="예: 홍길동", required=True, max_length=20)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("서버에서만 사용 가능합니다", ephemeral=True)
            return
        bank   = sanitize_text(self.bank_input.value, 20)
        number = sanitize_text(self.number_input.value, 30)
        holder = sanitize_text(self.holder_input.value, 20)
        # 계좌번호 형식 검증 (숫자와 하이픈만)
        if not re.fullmatch(r"[\d\-]+", number):
            await interaction.response.send_message(view=SimpleLayout("## 오류", "계좌번호는 숫자와 하이픈(-)만 입력 가능합니다", discord.Color.red()), ephemeral=True)
            return
        try:
            db_path = get_guild_db_path(interaction.guild.name)
            with sqlite3.connect(db_path) as conn:
                c = conn.cursor()
                c.execute("UPDATE info SET bank_name=?, account_number=?, account_holder=? WHERE guild_id=?",
                          (bank, number, holder, str(interaction.guild.id)))
                conn.commit()
            await interaction.response.send_message(
                view=SimpleLayout("## 계좌 설정 완료", f"> **은행:** {bank}\n> **계좌번호:** `{number}`\n> **예금주:** {holder}", discord.Color.green()),
                ephemeral=True
            )
        except Exception as e:
            print(f"[계좌 설정 오류] {e}")
            await interaction.response.send_message(view=SimpleLayout("## 오류", "계좌 설정 중 문제가 발생했습니다", discord.Color.red()), ephemeral=True)


# ══════════════════════════════════════════════════════
# 충전 설정 Modal
# ══════════════════════════════════════════════════════

class ChargeSettingModal(discord.ui.Modal, title="충전 설정"):
    min_input  = discord.ui.TextInput(label="최소 충전금액 (원)", placeholder="예: 1000", required=True, max_length=10)
    unit_input = discord.ui.TextInput(label="충전 단위 (원)", placeholder="예: 1000", required=True, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("서버에서만 사용 가능합니다", ephemeral=True)
            return
        try:
            min_charge  = int(re.sub(r"[^0-9]", "", self.min_input.value))
            charge_unit = int(re.sub(r"[^0-9]", "", self.unit_input.value))
        except ValueError:
            await interaction.response.send_message(view=SimpleLayout("## 오류", "숫자만 입력 가능합니다", discord.Color.red()), ephemeral=True)
            return
        if min_charge < 100 or min_charge > 1_000_000:
            await interaction.response.send_message(view=SimpleLayout("## 오류", "최소 충전금액은 100원 이상 1,000,000원 이하여야 합니다", discord.Color.red()), ephemeral=True)
            return
        if charge_unit < 100 or charge_unit > 100_000:
            await interaction.response.send_message(view=SimpleLayout("## 오류", "충전 단위는 100원 이상 100,000원 이하여야 합니다", discord.Color.red()), ephemeral=True)
            return
        try:
            db_path = get_guild_db_path(interaction.guild.name)
            with sqlite3.connect(db_path) as conn:
                c = conn.cursor()
                c.execute("UPDATE info SET min_charge=?, charge_unit=? WHERE guild_id=?",
                          (min_charge, charge_unit, str(interaction.guild.id)))
                conn.commit()
            await interaction.response.send_message(
                view=SimpleLayout("## 충전 설정 완료", f"> **최소 충전금액:** {min_charge:,}원\n> **충전 단위:** {charge_unit:,}원", discord.Color.green()),
                ephemeral=True
            )
        except Exception as e:
            print(f"[충전 설정 오류] {e}")
            await interaction.response.send_message(view=SimpleLayout("## 오류", "설정 저장 중 문제가 발생했습니다", discord.Color.red()), ephemeral=True)


# ══════════════════════════════════════════════════════
# 계좌이체 Modal
# ══════════════════════════════════════════════════════

class TransferModal(discord.ui.Modal, title="계좌이체 충전"):
    depositor_input = discord.ui.TextInput(label="입금자명", placeholder="입금 시 사용할 이름", required=True, max_length=20)
    amount_input    = discord.ui.TextInput(label="충전 금액 (원)", placeholder="예: 10000", required=True, max_length=10)

    def __init__(self, guild_id: str, guild_name: str):
        super().__init__()
        self.guild_id   = guild_id
        self.guild_name = guild_name

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None or str(interaction.guild.id) != self.guild_id:
            await interaction.response.send_message("잘못된 접근입니다", ephemeral=True)
            return

        depositor = sanitize_text(self.depositor_input.value, 20)
        # 입금자명 한글/영문/숫자만
        if not re.fullmatch(r"[가-힣a-zA-Z0-9]{1,20}", depositor):
            await interaction.response.send_message(view=SimpleLayout("## 오류", "입금자명은 한글/영문/숫자만 입력 가능합니다", discord.Color.red()), ephemeral=True)
            return

        try:
            amount = int(re.sub(r"[^0-9]", "", self.amount_input.value))
        except ValueError:
            await interaction.response.send_message(view=SimpleLayout("## 오류", "금액은 숫자만 입력 가능합니다", discord.Color.red()), ephemeral=True)
            return

        try:
            db_path = get_guild_db_path(self.guild_name)
            with sqlite3.connect(db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT bank_name, account_number, account_holder, min_charge, charge_unit FROM info WHERE guild_id=?",
                          (self.guild_id,))
                row = c.fetchone()
        except Exception as e:
            print(f"[충전 Modal DB 오류] {e}")
            await interaction.response.send_message(view=SimpleLayout("## 오류", "서버 정보를 불러올 수 없습니다", discord.Color.red()), ephemeral=True)
            return

        if not row:
            await interaction.response.send_message(view=SimpleLayout("## 오류", "등록된 서버가 아닙니다", discord.Color.red()), ephemeral=True)
            return

        bank, account_number, account_holder, min_charge, charge_unit = row
        min_charge  = min_charge  or 1000
        charge_unit = charge_unit or 1000

        if not bank or not account_number:
            await interaction.response.send_message(view=SimpleLayout("## 오류", "계좌 정보가 설정되지 않았습니다\n관리자에게 문의하세요", discord.Color.red()), ephemeral=True)
            return

        if amount < min_charge:
            await interaction.response.send_message(view=SimpleLayout("## 오류", f"최소 충전금액은 {min_charge:,}원입니다", discord.Color.red()), ephemeral=True)
            return

        if amount % charge_unit != 0:
            await interaction.response.send_message(view=SimpleLayout("## 오류", f"충전 단위는 {charge_unit:,}원입니다", discord.Color.red()), ephemeral=True)
            return

        if amount > 10_000_000:
            await interaction.response.send_message(view=SimpleLayout("## 오류", "1회 최대 충전금액은 10,000,000원입니다", discord.Color.red()), ephemeral=True)
            return

        # 동일 유저 중복 대기 방지
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT charge_id FROM charge_pending WHERE user_id=? AND status='pending'", (str(interaction.user.id),))
            if c.fetchone():
                await interaction.response.send_message(view=SimpleLayout("## 오류", "이미 진행 중인 충전 요청이 있습니다\n5분 후 자동 취소됩니다", discord.Color.red()), ephemeral=True)
                return

        now     = datetime.now()
        expires = now + timedelta(minutes=5)
        charge_id = generate_charge_id()

        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO charge_pending (charge_id, user_id, username, depositor, amount, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
            """, (charge_id, str(interaction.user.id), str(interaction.user), depositor, amount,
                  now.strftime("%Y-%m-%d %H:%M:%S"), expires.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()

        # 계좌 안내 컨테이너
        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## 계좌 안내"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=(
                f"> **은행:** {bank}\n"
                f"> **계좌번호:** `{account_number}`\n"
                f"> **예금주:** {account_holder}\n"
                f"> **입금금액:** {amount:,}원\n"
                f"> **입금자명:** {depositor}\n"
                f"> **만료시각:** {expires.strftime('%H:%M:%S')} (5분)\n\n"
                "입금자명을 정확히 입력 후 이체해주세요\n"
                "5분 내 입금이 확인되지 않으면 자동 취소됩니다"
            )),
            accent_color=discord.Color.from_str("#5865F2"),
        )
        view.add_item(container)

        await interaction.response.send_message(view=view, ephemeral=True)
        msg = await interaction.original_response()

        # message_id, channel_id 저장
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("UPDATE charge_pending SET channel_id=?, message_id=? WHERE charge_id=?",
                      (str(interaction.channel_id), str(msg.id), charge_id))
            conn.commit()

        pending_charge_messages[charge_id] = (interaction, str(interaction.channel_id), self.guild_id, db_path)

        # 5분 타이머
        asyncio.create_task(charge_timeout_task(charge_id, db_path, interaction))


# ══════════════════════════════════════════════════════
# 충전 5분 타이머
# ══════════════════════════════════════════════════════

async def charge_timeout_task(charge_id: str, db_path: str, interaction: discord.Interaction):
    await asyncio.sleep(300)  # 5분
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT status FROM charge_pending WHERE charge_id=?", (charge_id,))
            row = c.fetchone()
            if not row or row[0] != "pending":
                return  # 이미 완료/취소됨
            c.execute("UPDATE charge_pending SET status='expired' WHERE charge_id=? AND status='pending'", (charge_id,))
            conn.commit()

        # 메시지 수정 - 취소 컨테이너
        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## 충전 취소"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="5분 내 입금이 확인되지 않아 충전이 취소되었습니다\n다시 충전하려면 충전 버튼을 눌러주세요"),
            accent_color=discord.Color.red(),
        )
        view.add_item(container)
        await interaction.edit_original_response(view=view)

    except Exception as e:
        print(f"[충전 타이머 오류] {e}")
    finally:
        pending_charge_messages.pop(charge_id, None)


# ══════════════════════════════════════════════════════
# FastAPI 웹훅 수신 (봇 내부 HTTP 서버)
# ══════════════════════════════════════════════════════

async def handle_charge_webhook(charge_id: str, depositor: str, amount: int, guild_id: str, signature: str, raw_body: bytes):
    """FastAPI에서 호출 - 입금 확인 시 포인트 지급"""
    # HMAC 서명 검증
    if not verify_webhook_hmac(raw_body, signature):
        print(f"[웹훅 보안] HMAC 검증 실패 - charge_id={charge_id}")
        return False

    db_path = get_guild_db_path_by_id(guild_id)
    if not db_path:
        print(f"[웹훅 오류] guild_id={guild_id} DB 없음")
        return False

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, username, depositor, amount, status FROM charge_pending WHERE charge_id=?", (charge_id,))
        row = c.fetchone()

        if not row:
            print(f"[웹훅 오류] charge_id={charge_id} 없음")
            return False

        user_id, username, expected_depositor, expected_amount, status = row

        if status != "pending":
            print(f"[웹훅 오류] charge_id={charge_id} 이미 처리됨 status={status}")
            return False

        # 입금자명, 금액 일치 검증
        if depositor.strip() != expected_depositor.strip():
            print(f"[웹훅 보안] 입금자명 불일치: expected={expected_depositor}, got={depositor}")
            return False

        if amount != expected_amount:
            print(f"[웹훅 보안] 금액 불일치: expected={expected_amount}, got={amount}")
            return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 상태 업데이트 (atomic)
        c.execute("UPDATE charge_pending SET status='completed', completed_at=? WHERE charge_id=? AND status='pending'",
                  (now, charge_id))
        if c.rowcount == 0:
            return False  # 동시 처리 방지

        # 포인트 지급
        c.execute("""
            INSERT INTO users (user_id, username, points, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET points = points + ?, username = excluded.username
        """, (user_id, username, amount, now, amount))

        # 히스토리 저장
        c.execute("""
            INSERT INTO charge_history (charge_id, user_id, username, depositor, amount, status, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, 'completed', ?, ?)
        """, (charge_id, user_id, username, depositor, amount, now, now))

        c.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
        new_points = c.fetchone()[0]
        conn.commit()

    # 메시지 수정 - 완료 컨테이너
    entry = pending_charge_messages.get(charge_id)
    if entry:
        original_interaction, channel_id, _, _ = entry
        try:
            view = discord.ui.LayoutView()
            container = discord.ui.Container(
                discord.ui.TextDisplay(content="## 충전 완료"),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(content=(
                    f"> **충전금액:** {amount:,}원\n"
                    f"> **보유 포인트:** {new_points:,}원\n"
                    f"> **처리시각:** {now}"
                )),
                accent_color=discord.Color.green(),
            )
            view.add_item(container)
            await original_interaction.edit_original_response(view=view)
        except Exception as e:
            print(f"[웹훅 메시지 수정 오류] {e}")
        finally:
            pending_charge_messages.pop(charge_id, None)

    return True

# 봇에 웹훅 핸들러 등록 (FastAPI에서 직접 호출)
bot.handle_charge_webhook = handle_charge_webhook


# ══════════════════════════════════════════════════════
# /자판기 명령어
# ══════════════════════════════════════════════════════

@bot.tree.command(name="자판기", description="자판기를 전송합니다")
async def vending_machine(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("서버에서만 사용 가능합니다", ephemeral=True)
        return

    init_guild_db(str(interaction.guild.id), interaction.guild.name)

    try:
        db_path = get_guild_db_path(interaction.guild.name)
    except ValueError:
        await interaction.response.send_message(view=SimpleLayout("## 오류", "비정상적인 접근입니다", discord.Color.red()), ephemeral=True)
        return

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT vending_title, vending_description, accent_color, enabled_features FROM info WHERE guild_id=?",
                  (str(interaction.guild.id),))
        row = c.fetchone()

    if not row:
        await interaction.response.send_message(
            view=SimpleLayout("## 등록되지 않은 서버", "먼저 `/등록` 명령어로 서버를 등록해주세요", discord.Color.red()),
            ephemeral=True
        )
        return

    title, description, color_str, enabled_features = row
    title       = sanitize_text(title or "구매하기", 100)
    description = sanitize_text(description or "아래 버튼을 눌러 이용해주세요", 500)
    color_str   = validate_hex_color(color_str or "#5865F2")
    enabled     = enabled_features.split() if enabled_features else []

    # 자판기 전송 안내 (본인에게만)
    await interaction.response.send_message(
        view=SimpleLayout("## 자판기 전송", "자판기가 전송되었습니다", discord.Color.from_str("#5865F2")),
        ephemeral=True
    )

    # 자판기 공개 전송
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
        buttons.append(discord.ui.Button(label="구매", style=discord.ButtonStyle.secondary, custom_id="vending_buy",      emoji="<:emoji_48:1498298170281558058>"))
    if "제품" in enabled:
        buttons.append(discord.ui.Button(label="제품", style=discord.ButtonStyle.secondary, custom_id="vending_products", emoji="<:emoji_46:1498296760483709029>"))
    if "충전" in enabled:
        buttons.append(discord.ui.Button(label="충전", style=discord.ButtonStyle.secondary, custom_id="vending_charge",   emoji="<:emoji_46:1498297238630305903>"))
    if "정보" in enabled:
        buttons.append(discord.ui.Button(label="정보", style=discord.ButtonStyle.secondary, custom_id="vending_info",     emoji="<:emoji_47:1498298137406738483>"))

    if buttons:
        container.add_item(discord.ui.ActionRow(*buttons))
    view.add_item(container)
    await interaction.channel.send(view=view)


# ══════════════════════════════════════════════════════
# 버튼 인터랙션 처리
# ══════════════════════════════════════════════════════

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    if interaction.guild is None:
        return

    cid = interaction.data.get("custom_id", "")

    if cid == "vending_charge":
        try:
            db_path = get_guild_db_path(interaction.guild.name)
        except ValueError:
            await interaction.response.send_message(view=SimpleLayout("## 오류", "비정상적인 접근입니다", discord.Color.red()), ephemeral=True)
            return

        # 계좌이체 버튼 컨테이너
        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## 충전"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="아래 버튼을 눌러 충전 방법을 선택하세요"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            accent_color=discord.Color.from_str("#5865F2"),
        )
        btn_transfer = discord.ui.Button(label="계좌이체", style=discord.ButtonStyle.primary, custom_id="charge_transfer")
        container.add_item(discord.ui.ActionRow(btn_transfer))
        view.add_item(container)
        await interaction.response.send_message(view=view, ephemeral=True)

    elif cid == "charge_transfer":
        try:
            db_path = get_guild_db_path(interaction.guild.name)
        except ValueError:
            await interaction.response.send_message(view=SimpleLayout("## 오류", "비정상적인 접근입니다", discord.Color.red()), ephemeral=True)
            return

        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT bank_name, account_number FROM info WHERE guild_id=?", (str(interaction.guild.id),))
            row = c.fetchone()

        if not row or not row[0] or not row[1]:
            await interaction.response.send_message(view=SimpleLayout("## 오류", "계좌 정보가 설정되지 않았습니다\n관리자에게 문의하세요", discord.Color.red()), ephemeral=True)
            return

        await interaction.response.send_modal(TransferModal(str(interaction.guild.id), interaction.guild.name))

    elif cid.startswith("token_reissue_"):
        req_guild_id = cid.replace("token_reissue_", "")
        if str(interaction.guild.id) != req_guild_id:
            await interaction.response.send_message("권한이 없습니다", ephemeral=True)
            return
        try:
            db_path = get_guild_db_path(interaction.guild.name)
        except ValueError:
            await interaction.response.send_message(view=SimpleLayout("## 오류", "비정상적인 접근입니다", discord.Color.red()), ephemeral=True)
            return
        new_token = secrets.token_hex(24)
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("UPDATE info SET shortcut_token=? WHERE guild_id=?", (new_token, str(interaction.guild.id)))
            conn.commit()
        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## 토큰 재발급 완료"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=(
                f"> **새 토큰:** `{new_token}`\n\n"
                "기존 토큰은 더 이상 사용할 수 없습니다\n"
                "iOS 단축어 설정을 새 토큰으로 업데이트하세요"
            )),
            accent_color=discord.Color.green(),
        )
        view.add_item(container)
        await interaction.response.edit_message(view=view)


# ══════════════════════════════════════════════════════
# 단축어 토큰 발급 핸들러
# ══════════════════════════════════════════════════════

async def handle_token_issue(interaction: discord.Interaction):
    """서버당 1개 단축어 토큰 발급 - 이미 있으면 기존 토큰 표시"""
    if interaction.guild is None:
        await interaction.response.send_message("서버에서만 사용 가능합니다", ephemeral=True)
        return

    try:
        db_path = get_guild_db_path(interaction.guild.name)
    except ValueError:
        await interaction.response.send_message(view=SimpleLayout("## 오류", "비정상적인 접근입니다", discord.Color.red()), ephemeral=True)
        return

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT shortcut_token FROM info WHERE guild_id=?", (str(interaction.guild.id),))
        row = c.fetchone()

    if not row:
        await interaction.response.send_message(view=SimpleLayout("## 오류", "등록된 서버가 아닙니다", discord.Color.red()), ephemeral=True)
        return

    existing_token = row[0]

    if existing_token:
        # 이미 발급된 토큰 표시
        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## 단축어 토큰"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=(
                "이미 발급된 토큰이 있습니다\n\n"
                f"> **토큰:** `{existing_token}`\n\n"
                "이 토큰을 iOS 단축어에 입력하세요\n"
                "토큰을 재발급하려면 관리자에게 문의하세요"
            )),
            accent_color=discord.Color.from_str("#5865F2"),
        )

        # 재발급 버튼
        btn_reissue = discord.ui.Button(label="토큰 재발급", style=discord.ButtonStyle.danger, custom_id=f"token_reissue_{interaction.guild.id}")
        container.add_item(discord.ui.ActionRow(btn_reissue))
        view.add_item(container)
        await interaction.response.send_message(view=view, ephemeral=True)
    else:
        # 신규 발급
        new_token = secrets.token_hex(24)
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("UPDATE info SET shortcut_token=? WHERE guild_id=?", (new_token, str(interaction.guild.id)))
            conn.commit()

        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## 단축어 토큰 발급 완료"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=(
                f"> **토큰:** `{new_token}`\n\n"
                "이 토큰을 iOS 단축어 설정에 입력하세요\n"
                "토큰은 절대 외부에 공유하지 마세요"
            )),
            accent_color=discord.Color.green(),
        )
        view.add_item(container)
        await interaction.response.send_message(view=view, ephemeral=True)


# ══════════════════════════════════════════════════════
# /설정 명령어
# ══════════════════════════════════════════════════════

@bot.tree.command(name="설정", description="자판기 설정을 관리합니다")
async def settings(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("서버에서만 사용 가능합니다", ephemeral=True)
        return

    init_guild_db(str(interaction.guild.id), interaction.guild.name)
    try:
        db_path = get_guild_db_path(interaction.guild.name)
    except ValueError:
        await interaction.response.send_message(view=SimpleLayout("## 오류", "비정상적인 접근입니다", discord.Color.red()), ephemeral=True)
        return

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM info WHERE guild_id=?", (str(interaction.guild.id),))
        if not c.fetchone():
            await interaction.response.send_message(view=SimpleLayout("## 오류", "먼저 `/등록` 명령어로 서버를 등록해주세요", discord.Color.red()), ephemeral=True)
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
            discord.SelectOption(label="자판기 설정",    value="vending",  description="자판기 제목, 설명, 색상 설정"),
            discord.SelectOption(label="계좌 설정",      value="bank",     description="은행명, 계좌번호, 예금주 설정"),
            discord.SelectOption(label="충전 설정",      value="charge",   description="최소 충전금액, 충전 단위 설정"),
            discord.SelectOption(label="단축어 토큰 발급", value="token",  description="카카오뱅크 단축어용 토큰 발급 (서버당 1개)"),
        ]
    )

    async def select_callback(i: discord.Interaction):
        if i.guild_id != interaction.guild_id:
            await i.response.send_message("권한이 없습니다", ephemeral=True)
            return
        val = i.data["values"][0]
        if val == "vending":
            await i.response.send_modal(VendingSettingModal())
        elif val == "bank":
            await i.response.send_modal(BankSettingModal())
        elif val == "charge":
            await i.response.send_modal(ChargeSettingModal())
        elif val == "token":
            await handle_token_issue(i)

    select.callback = select_callback
    container.add_item(discord.ui.ActionRow(select))
    view.add_item(container)
    await interaction.response.send_message(view=view, ephemeral=True)


# ══════════════════════════════════════════════════════
# 라이센스 명령어
# ══════════════════════════════════════════════════════

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
        await interaction.response.send_message(view=SimpleLayout("## 권한 없음", "봇 관리자만 사용 가능합니다", discord.Color.red()), ephemeral=True)
        return
    if not 1 <= 수량 <= 100:
        await interaction.response.send_message(view=SimpleLayout("## 잘못된 수량", "1~100개 사이로 입력해주세요", discord.Color.red()), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        with sqlite3.connect(LICENSE_DB) as conn:
            c = conn.cursor()
            keys = []
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for _ in range(수량):
                key = create_unique_key()
                c.execute("INSERT INTO licenses (key, days, created_at) VALUES (?, ?, ?)", (key, 기간.value, now))
                keys.append(key)
            conn.commit()
    except Exception as e:
        print(f"[라이센스 생성 오류] {e}")
        await interaction.followup.send(view=SimpleLayout("## 오류", "생성 중 문제가 발생했습니다", discord.Color.red()), ephemeral=True)
        return

    txt = f"VOUT 라이센스 키 목록\n생성일시: {now}\n기간: {기간.value}일 / 수량: {수량}개\n" + "=" * 50 + "\n\n"
    for i, key in enumerate(keys, 1):
        txt += f"{i:>3}. {key}\n"

    fname = f"licenses_{기간.value}일_{수량}개_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    discord_file = discord.File(fp=io.BytesIO(txt.encode("utf-8")), filename=fname)

    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 라이센스 생성 완료"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"{수량}개의 라이센스가 생성되었습니다"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.File(f"attachment://{fname}"),
        accent_color=discord.Color.green()
    )
    view.add_item(container)
    await interaction.followup.send(view=view, file=discord_file, ephemeral=True)


@bot.tree.command(name="라이센스_목록", description="발급된 라이센스 키 목록을 조회합니다")
@app_commands.choices(필터=[
    app_commands.Choice(name="전체",   value="all"),
    app_commands.Choice(name="미사용", value="unused"),
    app_commands.Choice(name="사용됨", value="used"),
])
async def list_licenses(interaction: discord.Interaction, 필터: app_commands.Choice[str] = None):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message(view=SimpleLayout("## 권한 없음", "봇 관리자만 사용 가능합니다", discord.Color.red()), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    with sqlite3.connect(LICENSE_DB) as conn:
        c = conn.cursor()
        filter_val = 필터.value if 필터 else "all"
        if filter_val == "unused":
            c.execute("SELECT key, days, used, guild_name, created_at FROM licenses WHERE used=0")
        elif filter_val == "used":
            c.execute("SELECT key, days, used, guild_name, created_at FROM licenses WHERE used=1")
        else:
            c.execute("SELECT key, days, used, guild_name, created_at FROM licenses")
        rows = c.fetchall()
    filter_label = {"all": "전체", "unused": "미사용", "used": "사용됨"}.get(filter_val, "전체")
    if not rows:
        await interaction.followup.send(view=SimpleLayout(f"## 라이센스 목록 [{filter_label}]", "조회된 라이센스가 없습니다", discord.Color.from_str("#5865F2")), ephemeral=True)
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txt = f"VOUT 라이센스 목록 [{filter_label}]\n조회일시: {now} / 총 {len(rows)}개\n" + "=" * 60 + "\n\n"
    for i, (key, days, used, guild_name, created_at) in enumerate(rows, 1):
        status = f"사용됨 ({guild_name})" if used else "미사용"
        txt += f"{i:>3}. {key}  |  {days}일  |  {status}  |  생성: {created_at}\n"
    fname = f"license_list_{filter_val}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    discord_file = discord.File(fp=io.BytesIO(txt.encode("utf-8")), filename=fname)
    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"## 라이센스 목록 ({filter_label})"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"총 {len(rows)}개"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.File(f"attachment://{fname}"),
        accent_color=discord.Color.from_str("#5865F2")
    )
    view.add_item(container)
    await interaction.followup.send(view=view, file=discord_file, ephemeral=True)


@bot.tree.command(name="라이센스_삭제", description="라이센스 키를 삭제합니다")
@app_commands.describe(키="삭제할 라이센스 키")
async def delete_license(interaction: discord.Interaction, 키: str):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message(view=SimpleLayout("## 권한 없음", "봇 관리자만 사용 가능합니다", discord.Color.red()), ephemeral=True)
        return
    if not validate_license_key_format(키):
        await interaction.response.send_message(view=SimpleLayout("## 잘못된 형식", "올바른 라이센스 키 형식이 아닙니다", discord.Color.red()), ephemeral=True)
        return
    with sqlite3.connect(LICENSE_DB) as conn:
        c = conn.cursor()
        c.execute("SELECT key, days, used, guild_name FROM licenses WHERE key=?", (키.strip().upper(),))
        row = c.fetchone()
        if not row:
            await interaction.response.send_message(view=SimpleLayout("## 삭제 실패", "키를 찾을 수 없습니다", discord.Color.red()), ephemeral=True)
            return
        key, days, used, guild_name = row
        c.execute("DELETE FROM licenses WHERE key=?", (key,))
        conn.commit()
    status = f"사용됨 (서버: {guild_name})" if used else "미사용"
    await interaction.response.send_message(
        view=SimpleLayout("## 라이센스 삭제 완료", f"> **키:** `{key}`\n> **기간:** {days}일\n> **상태:** {status}", discord.Color.from_str("#5865F2")),
        ephemeral=True
    )


@bot.tree.command(name="등록", description="서버를 등록합니다")
@app_commands.describe(라이센스="발급받은 라이센스 키를 입력하세요")
async def register(interaction: discord.Interaction, 라이센스: str):
    if interaction.guild is None:
        await interaction.response.send_message("서버에서만 사용 가능합니다", ephemeral=True)
        return
    key_input = 라이센스.strip().upper()
    if not validate_license_key_format(key_input):
        await interaction.response.send_message(view=SimpleLayout("## 잘못된 형식", "올바른 라이센스 키 형식이 아닙니다", discord.Color.red()), ephemeral=True)
        return
    with sqlite3.connect(LICENSE_DB) as conn:
        c = conn.cursor()
        c.execute("SELECT key, days, used FROM licenses WHERE key=?", (key_input,))
        row = c.fetchone()
    if not row:
        await interaction.response.send_message(view=SimpleLayout("## 유효하지 않은 라이센스", "라이센스 키를 찾을 수 없습니다", discord.Color.red()), ephemeral=True)
        return
    key, days, used = row
    if used:
        await interaction.response.send_message(view=SimpleLayout("## 이미 사용된 라이센스", "이미 다른 서버에서 사용된 키입니다", discord.Color.red()), ephemeral=True)
        return
    expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    await interaction.response.send_message(
        view=RegisterConfirmLayout(key=key, days=days, expires=expires, guild_name=interaction.guild.name),
        ephemeral=True
    )


@bot.event
async def on_ready():
    init_license_db()
    bot.add_view(RegisterConfirmLayout("", 0, "", ""))
    await bot.tree.sync()
    print(f"{bot.user} 온라인")


bot.run(TOKEN)
