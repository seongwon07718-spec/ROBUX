import discord
from discord.ext import commands
from discord import app_commands
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, field_validator
import uvicorn, sqlite3, random, string, os, io, re, asyncio, secrets, hashlib, hmac
from datetime import datetime, timedelta

# ══════════════════════════════════════════════════════════════════════
# ■ 설정
# ══════════════════════════════════════════════════════════════════════
TOKEN          = ""
ADMIN_IDS      = [1454398431996018724]
DB_DIR         = "DB"
LICENSE_DB     = os.path.join(DB_DIR, "라이센스.db")
WEBHOOK_SECRET = "f1356103e6b861cb00d3c502cb27d9f66bd84880f70d3b98186fdbd5cd1d840c"
DOMAIN         = "pay.v0ut.com"
API_HOST       = "0.0.0.0"
API_PORT       = 8000

os.makedirs(DB_DIR, exist_ok=True)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
api = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# 충전 대기 인터랙션 저장 (charge_id → Interaction)
pending_charges: dict[str, discord.Interaction] = {}
_rate_store:     dict[str, list]                 = {}


# ══════════════════════════════════════════════════════════════════════
# ■ 유틸 함수
# ══════════════════════════════════════════════════════════════════════

def _safe_name(name: str) -> str:
    return ("".join(c for c in name if c.isalnum() or c in " _-").strip())[:64] or "unknown"

def _db_path(guild_name: str) -> str:
    p = os.path.abspath(os.path.join(DB_DIR, f"{_safe_name(guild_name)}.db"))
    if not p.startswith(os.path.abspath(DB_DIR)):
        raise ValueError("경로 조작 감지")
    return p

def _db_by_id(guild_id: str) -> str | None:
    for f in os.listdir(DB_DIR):
        if not f.endswith(".db") or f == "라이센스.db":
            continue
        p = os.path.join(DB_DIR, f)
        try:
            with sqlite3.connect(p) as c:
                if c.execute("SELECT 1 FROM info WHERE guild_id=?", (guild_id,)).fetchone():
                    return p
        except Exception:
            pass
    return None

def _hex(s: str) -> str:
    s = s.strip().lstrip("#")
    return f"#{s}" if re.fullmatch(r"[0-9A-Fa-f]{6}", s) else "#373842"

def _clean(s: str, n: int = 500) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", s).strip()[:n]

def _valid_key(k: str) -> bool:
    return bool(re.fullmatch(r"VOUT-[A-Z0-9]{6}-[A-Z0-9]{4}-[A-Z0-9]{4}", k.strip().upper()))

def _is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

def _rate(ip: str, lim: int = 30, win: int = 60) -> bool:
    now  = datetime.now().timestamp()
    hits = [t for t in _rate_store.get(ip, []) if now - t < win]
    if len(hits) >= lim:
        return False
    _rate_store[ip] = hits + [now]
    return True

def _hmac_ok(body: bytes, sig: str) -> bool:
    return hmac.compare_digest(
        hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest(), sig)

def _color(guild_id: str, db: str) -> discord.Color:
    try:
        with sqlite3.connect(db) as c:
            row = c.execute("SELECT accent_color FROM info WHERE guild_id=?", (guild_id,)).fetchone()
            if row and row[0]:
                return discord.Color.from_str(_hex(row[0]))
    except Exception:
        pass
    return discord.Color.from_str("#373842")

def _sep() -> discord.ui.Separator:
    return discord.ui.Separator(spacing=discord.SeparatorSpacing.small)

def _layout(title: str, body: str, color: discord.Color) -> discord.ui.LayoutView:
    v = discord.ui.LayoutView()
    v.add_item(discord.ui.Container(
        discord.ui.TextDisplay(content=title),
        _sep(),
        discord.ui.TextDisplay(content=body),
        accent_color=color,
    ))
    return v

def _err(msg: str, gc: discord.Color | None = None) -> discord.ui.LayoutView:
    return _layout("## 오류", f"-# {msg}", gc or discord.Color.red())


# ══════════════════════════════════════════════════════════════════════
# ■ DB 초기화 / 마이그레이션
# ══════════════════════════════════════════════════════════════════════

def init_license_db():
    with sqlite3.connect(LICENSE_DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS licenses(
            key TEXT PRIMARY KEY, days INTEGER NOT NULL,
            used INTEGER DEFAULT 0, guild_id TEXT, guild_name TEXT,
            created_at TEXT NOT NULL, expires_at TEXT)""")
        c.commit()

def init_guild_db(guild_id: str, guild_name: str) -> str:
    """서버 등록 진행 버튼 시에만 호출 → 서버.db 생성"""
    p = _db_path(guild_name)
    _migrate_db(p)
    return p

def _migrate_db(p: str):
    """신규 + 기존 DB 모두 누락 테이블/컬럼 자동 추가"""
    with sqlite3.connect(p) as c:
        c.execute("CREATE TABLE IF NOT EXISTS info(guild_id TEXT PRIMARY KEY, guild_name TEXT)")
        for col, typ in [
            ("license_key",         "TEXT"),
            ("registered_at",       "TEXT"),
            ("expires_at",          "TEXT"),
            ("vending_title",       "TEXT DEFAULT '구매하기'"),
            ("vending_description", "TEXT DEFAULT '아래 버튼을 눌러 이용해주세요'"),
            ("accent_color",        "TEXT DEFAULT '#373842'"),
            ("enabled_features",    "TEXT DEFAULT '제품 구매 충전 정보'"),
            ("bank_name",           "TEXT DEFAULT ''"),
            ("account_number",      "TEXT DEFAULT ''"),
            ("account_holder",      "TEXT DEFAULT ''"),
            ("min_charge",          "INTEGER DEFAULT 1000"),
            ("charge_unit",         "INTEGER DEFAULT 1000"),
            ("shortcut_token",      "TEXT"),
        ]:
            try:
                c.execute(f"ALTER TABLE info ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError:
                pass

        c.execute("""CREATE TABLE IF NOT EXISTS users(
            user_id TEXT PRIMARY KEY, username TEXT,
            points INTEGER DEFAULT 0, total_buy INTEGER DEFAULT 0, created_at TEXT)""")
        try:
            c.execute("ALTER TABLE users ADD COLUMN total_buy INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        c.execute("""CREATE TABLE IF NOT EXISTS charge_pending(
            charge_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, username TEXT,
            depositor TEXT NOT NULL, amount INTEGER NOT NULL,
            status TEXT DEFAULT 'pending', created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
            completed_at TEXT, channel_id TEXT, message_id TEXT)""")

        c.execute("""CREATE TABLE IF NOT EXISTS charge_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT,
            charge_id TEXT, user_id TEXT, username TEXT, depositor TEXT,
            amount INTEGER, status TEXT, created_at TEXT, completed_at TEXT)""")
        try:
            c.execute("ALTER TABLE charge_history ADD COLUMN guild_id TEXT")
        except sqlite3.OperationalError:
            pass

        c.execute("""CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT NOT NULL)""")

        c.execute("""CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL, category_id INTEGER NOT NULL,
            name TEXT NOT NULL, price INTEGER NOT NULL,
            stock INTEGER NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(category_id) REFERENCES categories(id))""")

        c.execute("""CREATE TABLE IF NOT EXISTS purchase_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL, username TEXT, product_id INTEGER,
            name TEXT, price INTEGER, qty INTEGER, created_at TEXT NOT NULL)""")
        c.commit()

def migrate_all():
    """봇 시작 시 모든 기존 서버.db 마이그레이션"""
    for f in os.listdir(DB_DIR):
        if f.endswith(".db") and f != "라이센스.db":
            try:
                _migrate_db(os.path.join(DB_DIR, f))
                print(f"[마이그레이션] {f}")
            except Exception as e:
                print(f"[마이그레이션 오류] {f}: {e}")


# ══════════════════════════════════════════════════════════════════════
# ■ 라이센스 키 생성
# ══════════════════════════════════════════════════════════════════════

def _new_key() -> str:
    def r(n): return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))
    return f"VOUT-{r(6)}-{r(4)}-{r(4)}"

def _make_key() -> str:
    for _ in range(1000):
        k = _new_key()
        with sqlite3.connect(LICENSE_DB) as c:
            if not c.execute("SELECT 1 FROM licenses WHERE key=?", (k,)).fetchone():
                return k
    raise RuntimeError("키 생성 실패")


# ══════════════════════════════════════════════════════════════════════
# ■ SMS 파싱 (카카오뱅크)
# ══════════════════════════════════════════════════════════════════════

def _parse_sms(sms: str) -> tuple[str, int] | None:
    """
    [Web발신]\n[카카오뱅크]\n정*원(3823)\n04/27 23:19\n입금 100원\n정성원\n잔액 300원
    """
    if "[카카오뱅크]" not in sms:
        return None
    lines = [l.strip() for l in sms.splitlines() if l.strip()]
    for idx, line in enumerate(lines):
        m = re.search(r"입금\s+([\d,]+)원", line)
        if m:
            try:
                amt = int(m.group(1).replace(",", ""))
            except ValueError:
                return None
            if idx + 1 < len(lines):
                dep = lines[idx + 1]
                if not re.search(r"잔액", dep) and re.fullmatch(r"[가-힣a-zA-Z0-9]{1,20}", dep):
                    if 0 < amt <= 10_000_000:
                        return dep, amt
    return None


# ══════════════════════════════════════════════════════════════════════
# ■ 서버별 동적 명령어 등록/해제
# ══════════════════════════════════════════════════════════════════════

async def register_guild_commands(guild: discord.Guild):
    """서버 등록 완료 후 해당 서버에만 /자판기, /설정 추가"""
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)

async def clear_guild_commands(guild: discord.Guild):
    """서버 미등록 상태에서 명령어 제거"""
    bot.tree.clear_commands(guild=guild)
    await bot.tree.sync(guild=guild)


# ══════════════════════════════════════════════════════════════════════
# ■ Persistent View (봇 재시작 후에도 버튼 작동)
# ══════════════════════════════════════════════════════════════════════

class VendingPersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="구매",  style=discord.ButtonStyle.secondary, custom_id="vend_buy")
    async def _buy(self, i: discord.Interaction, b: discord.ui.Button):
        await _handle_component(i)

    @discord.ui.button(label="제품",  style=discord.ButtonStyle.secondary, custom_id="vend_products")
    async def _products(self, i: discord.Interaction, b: discord.ui.Button):
        await _handle_component(i)

    @discord.ui.button(label="충전",  style=discord.ButtonStyle.secondary, custom_id="vend_charge")
    async def _charge(self, i: discord.Interaction, b: discord.ui.Button):
        await _handle_component(i)

    @discord.ui.button(label="정보",  style=discord.ButtonStyle.secondary, custom_id="vend_info")
    async def _info(self, i: discord.Interaction, b: discord.ui.Button):
        await _handle_component(i)

    @discord.ui.button(label="계좌이체 (account)", style=discord.ButtonStyle.secondary, custom_id="vend_transfer")
    async def _transfer(self, i: discord.Interaction, b: discord.ui.Button):
        await _handle_component(i)


class RegisterPersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="진행", style=discord.ButtonStyle.secondary, custom_id="reg_confirm")
    async def _confirm(self, i: discord.Interaction, b: discord.ui.Button):
        await _handle_component(i)

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, custom_id="reg_cancel")
    async def _cancel(self, i: discord.Interaction, b: discord.ui.Button):
        await _handle_component(i)


class TokenPersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="재발급", style=discord.ButtonStyle.danger, custom_id="token_reissue")
    async def _reissue(self, i: discord.Interaction, b: discord.ui.Button):
        await _handle_component(i)


# ══════════════════════════════════════════════════════════════════════
# ■ 모달 클래스
# ══════════════════════════════════════════════════════════════════════

class RegisterModal(discord.ui.Modal, title="서버 등록"):
    key = discord.ui.TextInput(
        label="라이센스 키",
        placeholder="VOUT-XXXXXX-XXXX-XXXX",
        required=True, max_length=25)

    async def on_submit(self, i: discord.Interaction):
        if not i.guild:
            await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
        key_in = self.key.value.strip().upper()
        if not _valid_key(key_in):
            await i.response.send_message(
                view=_err("올바른 라이센스 키 형식이 아닙니다\n-# 형식: VOUT-XXXXXX-XXXX-XXXX"),
                ephemeral=True); return
        with sqlite3.connect(LICENSE_DB) as c:
            row = c.execute("SELECT key,days,used FROM licenses WHERE key=?", (key_in,)).fetchone()
        if not row:
            await i.response.send_message(view=_err("라이센스 키를 찾을 수 없습니다"), ephemeral=True); return
        key, days, used = row
        if used:
            await i.response.send_message(view=_err("이미 다른 서버에서 사용된 키입니다"), ephemeral=True); return

        expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

        # 등록 확인 View
        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## 서버 등록 확인"),
            _sep(),
            discord.ui.TextDisplay(content=(
                f"> **라이센스:** `{key}`\n"
                f"> **서버:** {i.guild.name}\n"
                f"> **기간:** {days}일\n"
                f"> **만료일:** {expires}\n\n"
                "이 서버에 등록하시겠습니까?"
            )),
            accent_color=discord.Color.from_str("#373842"),
        )
        btn_ok = discord.ui.Button(label="진행", style=discord.ButtonStyle.secondary,
                                   custom_id=f"reg_confirm_{key}_{expires}")
        btn_ok.callback = _make_confirm_cb(key, days, expires)
        btn_no = discord.ui.Button(label="취소", style=discord.ButtonStyle.secondary,
                                   custom_id="reg_cancel_now")
        btn_no.callback = _make_cancel_cb()
        container.add_item(discord.ui.ActionRow(btn_ok, btn_no))
        view.add_item(container)
        await i.response.send_message(view=view, ephemeral=True)


def _make_confirm_cb(key: str, days: int, expires: str):
    async def cb(i: discord.Interaction):
        if not i.guild:
            await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
        await i.response.defer(ephemeral=True)
        try:
            with sqlite3.connect(LICENSE_DB) as c:
                row = c.execute("SELECT used FROM licenses WHERE key=?", (key,)).fetchone()
                if not row or row[0]:
                    await i.edit_original_response(view=_err("이미 사용된 라이센스입니다")); return
                c.execute(
                    "UPDATE licenses SET used=1,guild_id=?,guild_name=?,expires_at=? WHERE key=? AND used=0",
                    (str(i.guild.id), i.guild.name[:100], expires, key))
                if c.execute("SELECT changes()").fetchone()[0] == 0:
                    await i.edit_original_response(view=_err("이미 사용된 라이센스입니다")); return
                c.commit()

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db  = init_guild_db(str(i.guild.id), i.guild.name)
            with sqlite3.connect(db) as c:
                c.execute(
                    "INSERT OR REPLACE INTO info(guild_id,guild_name,license_key,registered_at,expires_at) VALUES(?,?,?,?,?)",
                    (str(i.guild.id), i.guild.name[:100], key, now, expires))
                c.commit()

            # 등록된 서버에만 /자판기 /설정 명령어 추가
            await register_guild_commands(i.guild)

            await i.edit_original_response(view=_layout(
                "## 서버 등록 완료",
                f"> **서버:** {i.guild.name}\n> **기간:** {days}일\n> **만료일:** {expires}\n\n`/설정`으로 자판기를 설정하세요",
                discord.Color.green()))
        except Exception as e:
            print(f"[등록 오류] {e}")
            await i.edit_original_response(view=_err("처리 중 문제가 발생했습니다"))
    return cb


def _make_cancel_cb():
    async def cb(i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        await i.edit_original_response(view=_layout(
            "## 등록 취소", "서버 등록이 취소되었습니다", discord.Color.from_str("#99AAB5")))
    return cb


class VendingSettingModal(discord.ui.Modal, title="자판기 설정"):
    t = discord.ui.TextInput(label="자판기 제목", placeholder="구매하기",  required=True,  max_length=100)
    d = discord.ui.TextInput(label="자판기 설명", style=discord.TextStyle.long, required=False, max_length=500)
    c = discord.ui.TextInput(label="색상 (HEX)", placeholder="#373842",   required=True,  max_length=7)

    async def on_submit(self, i: discord.Interaction):
        if not i.guild: return
        title = _clean(self.t.value, 100)
        desc  = _clean(self.d.value or "", 500)
        color = _hex(self.c.value)
        if not title:
            await i.response.send_message(view=_err("제목을 입력해주세요"), ephemeral=True); return
        try:
            db = _db_path(i.guild.name)
            gc = _color(str(i.guild.id), db)
            with sqlite3.connect(db) as c:
                c.execute("UPDATE info SET vending_title=?,vending_description=?,accent_color=? WHERE guild_id=?",
                          (title, desc, color, str(i.guild.id)))
                c.commit()
            await i.response.send_message(view=_layout(
                "## 설정 저장 완료",
                f"> **제목:** {title}\n> **설명:** {desc or '없음'}\n> **색상:** `{color}`",
                discord.Color.from_str(color)), ephemeral=True)
        except Exception as e:
            print(f"[자판기설정 오류] {e}")
            await i.response.send_message(view=_err("저장 중 문제가 발생했습니다"), ephemeral=True)


class BankModal(discord.ui.Modal, title="계좌 설정"):
    bn = discord.ui.TextInput(label="은행명",   placeholder="예) 카카오뱅크",    required=True, max_length=20)
    ac = discord.ui.TextInput(label="계좌번호", placeholder="예) 10-123-456789", required=True, max_length=30)
    ah = discord.ui.TextInput(label="예금주",   placeholder="예) 홍길동",         required=True, max_length=20)

    async def on_submit(self, i: discord.Interaction):
        if not i.guild: return
        bank   = _clean(self.bn.value, 20)
        number = _clean(self.ac.value, 30)
        holder = _clean(self.ah.value, 20)
        if not re.fullmatch(r"[\d\-]+", number):
            await i.response.send_message(view=_err("계좌번호는 숫자와 - 만 입력 가능합니다"), ephemeral=True); return
        try:
            db = _db_path(i.guild.name)
            gc = _color(str(i.guild.id), db)
            with sqlite3.connect(db) as c:
                c.execute("UPDATE info SET bank_name=?,account_number=?,account_holder=? WHERE guild_id=?",
                          (bank, number, holder, str(i.guild.id)))
                c.commit()
            await i.response.send_message(view=_layout(
                "## 계좌 설정 완료",
                f"> **은행명:** {bank}\n> **계좌번호:** `{number}`\n> **예금주:** {holder}",
                gc), ephemeral=True)
        except Exception as e:
            print(f"[계좌설정 오류] {e}")
            await i.response.send_message(view=_err("저장 중 문제가 발생했습니다"), ephemeral=True)


class ChargeSettingModal(discord.ui.Modal, title="충전 설정"):
    mi = discord.ui.TextInput(label="최소 충전금액 (원)", placeholder="예) 1000", required=True, max_length=10)
    un = discord.ui.TextInput(label="충전 단위 (원)",     placeholder="예) 1000", required=True, max_length=10)

    async def on_submit(self, i: discord.Interaction):
        if not i.guild: return
        try:
            mn = int(re.sub(r"[^0-9]", "", self.mi.value))
            un = int(re.sub(r"[^0-9]", "", self.un.value))
        except ValueError:
            await i.response.send_message(view=_err("숫자만 입력 가능합니다"), ephemeral=True); return
        if not (100 <= mn <= 1_000_000):
            await i.response.send_message(view=_err("최소 충전금액: 100원 ~ 1,000,000원"), ephemeral=True); return
        if not (100 <= un <= 100_000):
            await i.response.send_message(view=_err("충전 단위: 100원 ~ 100,000원"), ephemeral=True); return
        try:
            db = _db_path(i.guild.name)
            gc = _color(str(i.guild.id), db)
            with sqlite3.connect(db) as c:
                c.execute("UPDATE info SET min_charge=?,charge_unit=? WHERE guild_id=?",
                          (mn, un, str(i.guild.id)))
                c.commit()
            await i.response.send_message(view=_layout(
                "## 충전 설정 완료",
                f"> **최소 충전금액:** {mn:,}원\n> **충전 단위:** {un:,}원",
                gc), ephemeral=True)
        except Exception as e:
            print(f"[충전설정 오류] {e}")
            await i.response.send_message(view=_err("저장 중 문제가 발생했습니다"), ephemeral=True)


class AddCategoryModal(discord.ui.Modal, title="카테고리 추가"):
    name = discord.ui.TextInput(label="카테고리 이름", placeholder="예) 로블록스 아이템", required=True, max_length=30)

    def __init__(self, guild_id: str, guild_name: str):
        super().__init__()
        self.gid   = guild_id
        self.gname = guild_name

    async def on_submit(self, i: discord.Interaction):
        if not i.guild or str(i.guild.id) != self.gid:
            await i.response.send_message("잘못된 접근입니다", ephemeral=True); return
        name = _clean(self.name.value, 30)
        if not name:
            await i.response.send_message(view=_err("이름을 입력해주세요"), ephemeral=True); return
        try:
            db = _db_path(self.gname)
            gc = _color(self.gid, db)
            with sqlite3.connect(db) as c:
                if c.execute("SELECT 1 FROM categories WHERE guild_id=? AND name=?",
                             (self.gid, name)).fetchone():
                    await i.response.send_message(view=_err("이미 존재하는 카테고리 이름입니다"), ephemeral=True); return
                c.execute("INSERT INTO categories(guild_id,name,created_at) VALUES(?,?,?)",
                          (self.gid, name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                c.commit()
            await i.response.send_message(view=_layout(
                "## 카테고리 추가 완료",
                f"> **카테고리:** {name}\n-# /설정 > 상품 관리에서 제품을 추가할 수 있습니다",
                gc), ephemeral=True)
        except Exception as e:
            print(f"[카테고리추가 오류] {e}")
            await i.response.send_message(view=_err("저장 중 문제가 발생했습니다"), ephemeral=True)


class AddProductModal(discord.ui.Modal, title="제품 추가"):
    pname   = discord.ui.TextInput(label="제품명",      placeholder="예) 로블록스 100R", required=True, max_length=50)
    price   = discord.ui.TextInput(label="가격 (원)",   placeholder="예) 5000",          required=True, max_length=10)
    stock   = discord.ui.TextInput(label="재고 수량",   placeholder="예) 10",            required=True, max_length=6)
    content = discord.ui.TextInput(label="제품 내용물", style=discord.TextStyle.long,
                                   placeholder="구매 시 전달할 내용 (코드/계정 등)", required=True, max_length=1000)

    def __init__(self, guild_id: str, guild_name: str, cat_id: int):
        super().__init__()
        self.gid    = guild_id
        self.gname  = guild_name
        self.cat_id = cat_id

    async def on_submit(self, i: discord.Interaction):
        if not i.guild or str(i.guild.id) != self.gid:
            await i.response.send_message("잘못된 접근입니다", ephemeral=True); return
        name    = _clean(self.pname.value, 50)
        content = _clean(self.content.value, 1000)
        try:
            price = int(re.sub(r"[^0-9]", "", self.price.value))
            stock = int(re.sub(r"[^0-9]", "", self.stock.value))
        except ValueError:
            await i.response.send_message(view=_err("가격과 재고는 숫자만 입력 가능합니다"), ephemeral=True); return
        if not (1 <= price <= 100_000_000):
            await i.response.send_message(view=_err("가격: 1원 ~ 1억원"), ephemeral=True); return
        if not (1 <= stock <= 9999):
            await i.response.send_message(view=_err("재고: 1개 ~ 9,999개"), ephemeral=True); return
        try:
            db = _db_path(self.gname)
            gc = _color(self.gid, db)
            with sqlite3.connect(db) as c:
                if not c.execute("SELECT 1 FROM categories WHERE id=? AND guild_id=?",
                                 (self.cat_id, self.gid)).fetchone():
                    await i.response.send_message(view=_err("카테고리를 찾을 수 없습니다"), ephemeral=True); return
                c.execute(
                    "INSERT INTO products(guild_id,category_id,name,price,stock,content,created_at) VALUES(?,?,?,?,?,?,?)",
                    (self.gid, self.cat_id, name, price, stock, content,
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                c.commit()
            await i.response.send_message(view=_layout(
                "## 제품 추가 완료",
                f"> **제품명:** {name}\n> **가격:** {price:,}원\n> **재고:** {stock}개",
                gc), ephemeral=True)
        except Exception as e:
            print(f"[제품추가 오류] {e}")
            await i.response.send_message(view=_err("저장 중 문제가 발생했습니다"), ephemeral=True)


class BuyQtyModal(discord.ui.Modal, title="구매 수량"):
    qty = discord.ui.TextInput(label="수량", placeholder="예) 1", required=True, max_length=4)

    def __init__(self, guild_id: str, guild_name: str, prod_id: int):
        super().__init__()
        self.gid   = guild_id
        self.gname = guild_name
        self.pid   = prod_id

    async def on_submit(self, i: discord.Interaction):
        if not i.guild or str(i.guild.id) != self.gid:
            await i.response.send_message("잘못된 접근입니다", ephemeral=True); return
        try:
            qty = int(re.sub(r"[^0-9]", "", self.qty.value))
        except ValueError:
            await i.response.send_message(view=_err("숫자만 입력 가능합니다"), ephemeral=True); return
        if qty < 1:
            await i.response.send_message(view=_err("수량은 1개 이상이어야 합니다"), ephemeral=True); return

        try:
            db = _db_path(self.gname)
            gc = _color(self.gid, db)
            with sqlite3.connect(db) as c:
                prod = c.execute(
                    "SELECT name,price,stock,content FROM products WHERE id=? AND guild_id=?",
                    (self.pid, self.gid)).fetchone()
        except Exception as e:
            print(f"[구매 DB 오류] {e}")
            await i.response.send_message(view=_err("제품 정보를 불러올 수 없습니다"), ephemeral=True); return

        if not prod:
            await i.response.send_message(view=_err("제품을 찾을 수 없습니다"), ephemeral=True); return
        name, price, stock, content = prod

        if stock <= 0:
            await i.response.send_message(view=_err(f"**{name}** 은 품절입니다"), ephemeral=True); return
        if qty > stock:
            await i.response.send_message(view=_err(f"재고 부족\n-# 현재 재고: {stock}개"), ephemeral=True); return
        if qty > 99:
            await i.response.send_message(view=_err("1회 최대 구매 수량은 99개입니다"), ephemeral=True); return

        total = price * qty
        with sqlite3.connect(db) as c:
            pts = c.execute("SELECT points FROM users WHERE user_id=?", (str(i.user.id),)).fetchone()
        points = pts[0] if pts else 0
        if points < total:
            await i.response.send_message(view=_err(
                f"잔액 부족\n-# 필요: {total:,}원 / 보유: {points:,}원"), ephemeral=True); return

        await i.response.defer(ephemeral=True)
        try:
            with sqlite3.connect(db) as c:
                c.execute("UPDATE products SET stock=stock-? WHERE id=? AND guild_id=? AND stock>=?",
                          (qty, self.pid, self.gid, qty))
                if c.execute("SELECT changes()").fetchone()[0] == 0:
                    await i.edit_original_response(view=_err("재고가 변경되었습니다\n-# 다시 시도해주세요")); return
                c.execute("UPDATE users SET points=points-?,total_buy=total_buy+? WHERE user_id=?",
                          (total, total, str(i.user.id)))
                new_pts = c.execute("SELECT points FROM users WHERE user_id=?", (str(i.user.id),)).fetchone()[0]
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute(
                    "INSERT INTO purchase_history(guild_id,user_id,username,product_id,name,price,qty,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (self.gid, str(i.user.id), str(i.user), self.pid, name, price, qty, now))
                c.commit()

            try:
                await i.user.send(
                    f"**{name}** {qty}개 구매 완료\n결제 금액: {total:,}원\n```\n{content}\n```")
                dm_ok = True
            except Exception:
                dm_ok = False

            body_txt = (
                f"> **제품명:** {name}\n> **수량:** {qty}개\n"
                f"> **결제 금액:** {total:,}원\n> **남은 잔액:** {new_pts:,}원\n\n"
                + ("-# 제품 내용물이 DM으로 전송되었습니다"
                   if dm_ok else "-# DM 전송 실패 ─ DM을 허용한 후 관리자에게 문의하세요")
            )
            await i.edit_original_response(view=_layout("## 구매 완료", body_txt, gc))
        except Exception as e:
            print(f"[구매 오류] {e}")
            await i.edit_original_response(view=_err("구매 처리 중 문제가 발생했습니다"))


class TransferModal(discord.ui.Modal, title="계좌이체 충전"):
    dep = discord.ui.TextInput(label="입금자명",       placeholder="예) 홍길동", required=True, max_length=20)
    amt = discord.ui.TextInput(label="충전 금액 (원)", placeholder="예) 10000",  required=True, max_length=10)

    def __init__(self, guild_id: str, guild_name: str):
        super().__init__()
        self.gid   = guild_id
        self.gname = guild_name

    async def on_submit(self, i: discord.Interaction):
        if not i.guild or str(i.guild.id) != self.gid:
            await i.response.send_message("잘못된 접근입니다", ephemeral=True); return
        depositor = _clean(self.dep.value, 20)
        if not re.fullmatch(r"[가-힣a-zA-Z0-9]{1,20}", depositor):
            await i.response.send_message(view=_err("입금자명은 한글/영문/숫자만 가능합니다"), ephemeral=True); return
        try:
            amount = int(re.sub(r"[^0-9]", "", self.amt.value))
        except ValueError:
            await i.response.send_message(view=_err("금액은 숫자만 입력 가능합니다"), ephemeral=True); return

        try:
            db = _db_path(self.gname)
            gc = _color(self.gid, db)
            with sqlite3.connect(db) as c:
                row = c.execute(
                    "SELECT bank_name,account_number,account_holder,min_charge,charge_unit FROM info WHERE guild_id=?",
                    (self.gid,)).fetchone()
        except Exception as e:
            print(f"[충전 DB 오류] {e}")
            await i.response.send_message(view=_err("서버 정보를 불러올 수 없습니다"), ephemeral=True); return

        if not row:
            await i.response.send_message(view=_err("등록된 서버가 아닙니다"), ephemeral=True); return
        bank, acnum, holder, min_c, unit = row
        min_c = min_c or 1000
        unit  = unit  or 1000

        if not bank or not acnum:
            await i.response.send_message(view=_err("계좌 정보가 설정되지 않았습니다\n-# 관리자에게 문의하세요"), ephemeral=True); return
        if amount < min_c:
            await i.response.send_message(view=_err(f"최소 충전금액은 {min_c:,}원입니다"), ephemeral=True); return
        if amount % unit != 0:
            await i.response.send_message(view=_err(f"충전 단위는 {unit:,}원입니다"), ephemeral=True); return
        if amount > 10_000_000:
            await i.response.send_message(view=_err("1회 최대 충전금액은 10,000,000원입니다"), ephemeral=True); return

        with sqlite3.connect(db) as c:
            if c.execute("SELECT 1 FROM charge_pending WHERE user_id=? AND status='pending'",
                         (str(i.user.id),)).fetchone():
                await i.response.send_message(
                    view=_err("진행 중인 충전 요청이 있습니다\n-# 5분 후에 다시 신청해주세요"), ephemeral=True); return

        now     = datetime.now()
        expires = now + timedelta(minutes=5)
        cid     = secrets.token_hex(16)

        with sqlite3.connect(db) as c:
            c.execute(
                "INSERT INTO charge_pending(charge_id,user_id,username,depositor,amount,status,created_at,expires_at) VALUES(?,?,?,?,?,'pending',?,?)",
                (cid, str(i.user.id), str(i.user), depositor, amount,
                 now.strftime("%Y-%m-%d %H:%M:%S"), expires.strftime("%Y-%m-%d %H:%M:%S")))
            c.commit()

        v = discord.ui.LayoutView()
        v.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content="## 계좌 안내"),
            _sep(),
            discord.ui.TextDisplay(content=(
                f"> **은행명:** {bank}\n"
                f"> **계좌번호:** `{acnum}`\n"
                f"> **예금주:** {holder}"
            )),
            _sep(),
            discord.ui.TextDisplay(content=(
                f"> **입금금액:** {amount:,}원\n"
                f"> **입금자명:** {depositor}\n"
                f"> **만료시각:** {expires.strftime('%H:%M:%S')} (5분)"
            )),
            _sep(),
            discord.ui.TextDisplay(content=(
                "-# 입금자명을 정확히 입력 후 이체해주세요\n"
                "-# 5분 내 입금이 확인되지 않으면 취소됩니다"
            )),
            accent_color=gc,
        ))
        await i.response.send_message(view=v, ephemeral=True)
        msg = await i.original_response()

        with sqlite3.connect(db) as c:
            c.execute("UPDATE charge_pending SET channel_id=?,message_id=? WHERE charge_id=?",
                      (str(i.channel_id), str(msg.id), cid))
            c.commit()

        pending_charges[cid] = i
        asyncio.create_task(_charge_timeout(cid, db, i, gc))


# ══════════════════════════════════════════════════════════════════════
# ■ 충전 타이머 / 완료 처리
# ══════════════════════════════════════════════════════════════════════

async def _charge_timeout(cid: str, db: str, i: discord.Interaction, gc: discord.Color):
    await asyncio.sleep(300)
    try:
        with sqlite3.connect(db) as c:
            row = c.execute("SELECT status FROM charge_pending WHERE charge_id=?", (cid,)).fetchone()
            if not row or row[0] != "pending":
                return
            c.execute("UPDATE charge_pending SET status='expired' WHERE charge_id=? AND status='pending'", (cid,))
            c.commit()
        v = discord.ui.LayoutView()
        v.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content="## 충전 취소"),
            _sep(),
            discord.ui.TextDisplay(content="-# 입금이 확인되지 않아 충전이 취소되었습니다\n-# 다시 충전하려면 충전 버튼을 눌러주세요"),
            accent_color=discord.Color.red(),
        ))
        await i.edit_original_response(view=v)
    except Exception as e:
        print(f"[충전타이머 오류] {e}")
    finally:
        pending_charges.pop(cid, None)


async def _complete_charge(cid: str, depositor: str, amount: int, guild_id: str, sig: str, raw: bytes) -> bool:
    if not _hmac_ok(raw, sig):
        print(f"[웹훅보안] HMAC 실패 cid={cid}"); return False
    db = _db_by_id(guild_id)
    if not db:
        return False
    gc = _color(guild_id, db)
    with sqlite3.connect(db) as c:
        row = c.execute(
            "SELECT user_id,username,depositor,amount,status FROM charge_pending WHERE charge_id=?",
            (cid,)).fetchone()
        if not row:
            return False
        uid, uname, exp_dep, exp_amt, status = row
        if status != "pending" or depositor.strip() != exp_dep.strip() or amount != exp_amt:
            print(f"[웹훅보안] 불일치 dep={depositor}/{exp_dep} amt={amount}/{exp_amt}"); return False
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE charge_pending SET status='completed',completed_at=? WHERE charge_id=? AND status='pending'",
                  (now, cid))
        if c.execute("SELECT changes()").fetchone()[0] == 0:
            return False
        c.execute("""INSERT INTO users(user_id,username,points,total_buy,created_at) VALUES(?,?,?,0,?)
            ON CONFLICT(user_id) DO UPDATE SET points=points+?,username=excluded.username""",
            (uid, uname, amount, now, amount))
        c.execute(
            "INSERT INTO charge_history(guild_id,charge_id,user_id,username,depositor,amount,status,created_at,completed_at) VALUES(?,?,?,?,?,?,'completed',?,?)",
            (guild_id, cid, uid, uname, depositor, amount, now, now))
        new_pts = c.execute("SELECT points FROM users WHERE user_id=?", (uid,)).fetchone()[0]
        c.commit()

    orig = pending_charges.get(cid)
    if orig:
        try:
            v = discord.ui.LayoutView()
            v.add_item(discord.ui.Container(
                discord.ui.TextDisplay(content="## 충전 완료"),
                _sep(),
                discord.ui.TextDisplay(content=f"> **충전 금액:** {amount:,}원\n> **보유 잔액:** {new_pts:,}원"),
                _sep(),
                discord.ui.TextDisplay(content=f"-# 처리시각: {now}"),
                accent_color=gc,
            ))
            await orig.edit_original_response(view=v)
        except Exception as e:
            print(f"[충전완료 메시지 오류] {e}")
        finally:
            pending_charges.pop(cid, None)
    return True


# ══════════════════════════════════════════════════════════════════════
# ■ 컴포넌트 핸들러 (모든 버튼/Select 처리)
# ══════════════════════════════════════════════════════════════════════

async def _handle_component(i: discord.Interaction):
    if not i.guild:
        await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
    cid = i.data.get("custom_id", "")
    try:
        db = _db_path(i.guild.name)
        gc = _color(str(i.guild.id), db)
    except ValueError:
        await i.response.send_message(view=_err("비정상적인 접근입니다"), ephemeral=True); return

    try:
        # ── 자판기 버튼 ──────────────────────────────────────────
        if cid == "vend_products":
            await _do_vend_products(i, db, gc)

        elif cid == "vend_buy":
            await _do_vend_buy(i, db, gc)

        elif cid == "vend_info":
            await _do_vend_info(i, db, gc)

        elif cid == "vend_charge":
            with sqlite3.connect(db) as c:
                row = c.execute("SELECT bank_name,account_number FROM info WHERE guild_id=?",
                                (str(i.guild.id),)).fetchone()
            if not row or not row[0] or not row[1]:
                await i.response.send_message(
                    view=_err("계좌 정보가 설정되지 않았습니다\n-# 관리자에게 문의하세요"), ephemeral=True); return
            v = discord.ui.LayoutView()
            container = discord.ui.Container(
                discord.ui.TextDisplay(content="## 결제수단"),
                _sep(),
                discord.ui.TextDisplay(content="충전 방법을 선택하세요"),
                _sep(),
                accent_color=gc,
            )
            btn = discord.ui.Button(label="계좌이체 (account)", style=discord.ButtonStyle.secondary,
                                    custom_id="vend_transfer")
            btn.callback = lambda si: si.response.send_modal(TransferModal(str(si.guild.id), si.guild.name))
            container.add_item(discord.ui.ActionRow(btn))
            v.add_item(container)
            await i.response.send_message(view=v, ephemeral=True)

        elif cid == "vend_transfer":
            await i.response.send_modal(TransferModal(str(i.guild.id), i.guild.name))

        # ── 상품 관리 버튼 ────────────────────────────────────────
        elif cid.startswith("prod_add_cat_"):
            if str(i.guild.id) != cid[len("prod_add_cat_"):]:
                await i.response.send_message("권한이 없습니다", ephemeral=True); return
            await i.response.send_modal(AddCategoryModal(str(i.guild.id), i.guild.name))

        elif cid.startswith("prod_add_"):
            parts = cid.split("_")   # prod_add_{cat_id}_{guild_id}
            cat_id, gid_check = int(parts[2]), parts[3]
            if str(i.guild.id) != gid_check:
                await i.response.send_message("권한이 없습니다", ephemeral=True); return
            await i.response.send_modal(AddProductModal(str(i.guild.id), i.guild.name, cat_id))

        elif cid.startswith("prod_delcat_"):
            parts = cid.split("_")   # prod_delcat_{cat_id}_{guild_id}
            cat_id, gid_check = int(parts[2]), parts[3]
            if str(i.guild.id) != gid_check:
                await i.response.send_message("권한이 없습니다", ephemeral=True); return
            with sqlite3.connect(db) as c:
                cat = c.execute("SELECT name FROM categories WHERE id=? AND guild_id=?",
                                (cat_id, str(i.guild.id))).fetchone()
                if not cat:
                    await i.response.send_message(view=_err("카테고리를 찾을 수 없습니다"), ephemeral=True); return
                cnt = c.execute("SELECT COUNT(*) FROM products WHERE category_id=? AND guild_id=?",
                                (cat_id, str(i.guild.id))).fetchone()[0]
                c.execute("DELETE FROM products WHERE category_id=? AND guild_id=?", (cat_id, str(i.guild.id)))
                c.execute("DELETE FROM categories WHERE id=? AND guild_id=?", (cat_id, str(i.guild.id)))
                c.commit()
            await i.response.send_message(view=_layout(
                "## 카테고리 삭제 완료",
                f"> **카테고리:** {cat[0]}\n> **삭제된 제품:** {cnt}개\n-# 하위 제품이 모두 삭제되었습니다",
                gc), ephemeral=True)

        # ── 토큰 재발급 ──────────────────────────────────────────
        elif cid == "token_reissue":
            tok = secrets.token_hex(24)
            with sqlite3.connect(db) as c:
                c.execute("UPDATE info SET shortcut_token=? WHERE guild_id=?", (tok, str(i.guild.id)))
                c.commit()
            v = discord.ui.LayoutView()
            v.add_item(discord.ui.Container(
                discord.ui.TextDisplay(content="## IOS 자충 토큰 재발급"),
                _sep(),
                discord.ui.TextDisplay(content=f"> **새 토큰:** `{tok}`"),
                _sep(),
                discord.ui.TextDisplay(content="-# 기존 토큰은 즉시 무효화됩니다"),
                accent_color=gc,
            ))
            await i.response.edit_message(view=v)

    except Exception as e:
        print(f"[컴포넌트 오류] cid={cid} {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
        try:
            if not i.response.is_done():
                await i.response.send_message(view=_err(f"오류가 발생했습니다\n-# {type(e).__name__}"), ephemeral=True)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════
# ■ 자판기 버튼 기능 함수
# ══════════════════════════════════════════════════════════════════════

async def _do_vend_products(i: discord.Interaction, db: str, gc: discord.Color):
    """제품 버튼: 카테고리 → 제품 목록만 표시"""
    with sqlite3.connect(db) as c:
        cats = c.execute("SELECT id,name FROM categories WHERE guild_id=? ORDER BY id",
                         (str(i.guild.id),)).fetchall()
    if not cats:
        await i.response.send_message(view=_err("등록된 상품이 없습니다\n-# 관리자에게 문의하세요"), ephemeral=True); return

    v = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 제품"),
        _sep(),
        discord.ui.TextDisplay(content="확인할 카테고리를 선택하세요"),
        _sep(),
        accent_color=gc,
    )
    sel = discord.ui.Select(
        placeholder="카테고리 선택",
        options=[discord.SelectOption(label=name, value=str(cid)) for cid, name in cats[:25]])

    async def _sel(si: discord.Interaction):
        if str(si.guild.id) != str(i.guild.id):
            await si.response.send_message("권한이 없습니다", ephemeral=True); return
        cat_id = int(si.data["values"][0])
        with sqlite3.connect(db) as c:
            cat   = c.execute("SELECT name FROM categories WHERE id=? AND guild_id=?",
                              (cat_id, str(si.guild.id))).fetchone()
            prods = c.execute(
                "SELECT name,price,stock FROM products WHERE category_id=? AND guild_id=? ORDER BY id",
                (cat_id, str(si.guild.id))).fetchall()
        if not cat:
            await si.response.send_message(view=_err("카테고리를 찾을 수 없습니다"), ephemeral=True); return
        lines = "\n".join(
            f"> **{n}** ─ {p:,}원 / {'품절' if s == 0 else f'재고 {s}개'}"
            for n, p, s in prods) if prods else "등록된 제품이 없습니다"
        v2 = discord.ui.LayoutView()
        v2.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content=f"## {cat[0]}"),
            _sep(),
            discord.ui.TextDisplay(content=lines),
            accent_color=gc,
        ))
        await si.response.send_message(view=v2, ephemeral=True)

    sel.callback = _sel
    container.add_item(discord.ui.ActionRow(sel))
    v.add_item(container)
    await i.response.send_message(view=v, ephemeral=True)


async def _do_vend_buy(i: discord.Interaction, db: str, gc: discord.Color):
    """구매 버튼: 카테고리 → 제품 선택 → 수량 모달"""
    with sqlite3.connect(db) as c:
        cats = c.execute("SELECT id,name FROM categories WHERE guild_id=? ORDER BY id",
                         (str(i.guild.id),)).fetchall()
    if not cats:
        await i.response.send_message(view=_err("등록된 상품이 없습니다\n-# 관리자에게 문의하세요"), ephemeral=True); return

    v = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 구매"),
        _sep(),
        discord.ui.TextDisplay(content="구매할 카테고리를 선택하세요"),
        _sep(),
        accent_color=gc,
    )
    sel = discord.ui.Select(
        placeholder="카테고리 선택",
        options=[discord.SelectOption(label=name, value=str(cid)) for cid, name in cats[:25]])

    async def _cat_sel(si: discord.Interaction):
        if str(si.guild.id) != str(i.guild.id):
            await si.response.send_message("권한이 없습니다", ephemeral=True); return
        cat_id = int(si.data["values"][0])
        with sqlite3.connect(db) as c:
            cat   = c.execute("SELECT name FROM categories WHERE id=? AND guild_id=?",
                              (cat_id, str(si.guild.id))).fetchone()
            prods = c.execute(
                "SELECT id,name,price,stock FROM products WHERE category_id=? AND guild_id=? AND stock>0 ORDER BY id",
                (cat_id, str(si.guild.id))).fetchall()
        if not cat:
            await si.response.send_message(view=_err("카테고리를 찾을 수 없습니다"), ephemeral=True); return
        if not prods:
            await si.response.send_message(
                view=_err(f"**{cat[0]}** 카테고리의 모든 상품이 품절입니다"), ephemeral=True); return

        v2 = discord.ui.LayoutView()
        container2 = discord.ui.Container(
            discord.ui.TextDisplay(content=f"## {cat[0]}"),
            _sep(),
            discord.ui.TextDisplay(content="\n".join(
                f"> **{n}** ─ {p:,}원 / 재고 {s}개" for _, n, p, s in prods)),
            _sep(),
            discord.ui.TextDisplay(content="-# 구매할 제품을 선택하세요"),
            accent_color=gc,
        )
        sel2 = discord.ui.Select(
            placeholder="제품 선택",
            options=[discord.SelectOption(label=f"{n} ─ {p:,}원", value=str(pid))
                     for pid, n, p, s in prods[:25]])

        async def _prod_sel(si2: discord.Interaction):
            if str(si2.guild.id) != str(i.guild.id):
                await si2.response.send_message("권한이 없습니다", ephemeral=True); return
            prod_id = int(si2.data["values"][0])
            with sqlite3.connect(db) as c:
                row = c.execute("SELECT stock FROM products WHERE id=? AND guild_id=?",
                                (prod_id, str(si2.guild.id))).fetchone()
            if not row or row[0] <= 0:
                await si2.response.send_message(view=_err("품절된 상품입니다\n-# 다른 제품을 선택해주세요"), ephemeral=True); return
            await si2.response.send_modal(BuyQtyModal(str(si2.guild.id), si2.guild.name, prod_id))

        sel2.callback = _prod_sel
        container2.add_item(discord.ui.ActionRow(sel2))
        v2.add_item(container2)
        await si.response.send_message(view=v2, ephemeral=True)

    sel.callback = _cat_sel
    container.add_item(discord.ui.ActionRow(sel))
    v.add_item(container)
    await i.response.send_message(view=v, ephemeral=True)


async def _do_vend_info(i: discord.Interaction, db: str, gc: discord.Color):
    """정보 버튼: 유저 정보 + 로그 드롭바"""
    with sqlite3.connect(db) as c:
        user = c.execute("SELECT points,total_buy FROM users WHERE user_id=?",
                         (str(i.user.id),)).fetchone()
    points    = user[0] if user else 0
    total_buy = user[1] if user else 0
    discount  = 5 if total_buy >= 500_000 else (3 if total_buy >= 100_000 else 0)

    v = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 내 정보"),
        _sep(),
        discord.ui.TextDisplay(content=(
            f"> **유저:** {i.user.display_name}\n"
            f"> **잔액:** {points:,}원\n"
            f"> **누적 구매:** {total_buy:,}원\n"
            f"> **적용 할인:** {discount}%"
        )),
        _sep(),
        accent_color=gc,
    )
    sel = discord.ui.Select(placeholder="로그 조회", options=[
        discord.SelectOption(label="최근 충전 로그", value="charge_log"),
        discord.SelectOption(label="최근 구매 로그", value="buy_log"),
    ])

    async def _log_sel(si: discord.Interaction):
        if str(si.user.id) != str(i.user.id):
            await si.response.send_message("본인만 조회 가능합니다", ephemeral=True); return
        val = si.data["values"][0]
        if val == "charge_log":
            with sqlite3.connect(db) as c:
                rows = c.execute(
                    "SELECT amount,status,created_at FROM charge_history WHERE user_id=? AND guild_id=? ORDER BY id DESC LIMIT 5",
                    (str(si.user.id), str(si.guild.id))).fetchall()
            lines = "\n".join(
                f"> {amt:,}원 ─ {'완료' if st == 'completed' else '취소'} ─ {cat[:16]}"
                for amt, st, cat in rows) if rows else "-# 충전 내역이 없습니다"
            title = "## 최근 충전 로그"
        else:
            with sqlite3.connect(db) as c:
                rows = c.execute(
                    "SELECT name,price,qty,created_at FROM purchase_history WHERE user_id=? AND guild_id=? ORDER BY id DESC LIMIT 5",
                    (str(si.user.id), str(si.guild.id))).fetchall()
            lines = "\n".join(
                f"> **{n}** {q}개 ─ {p*q:,}원 ─ {cat[:16]}"
                for n, p, q, cat in rows) if rows else "-# 구매 내역이 없습니다"
            title = "## 최근 구매 로그"
        v2 = discord.ui.LayoutView()
        v2.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content=title),
            _sep(),
            discord.ui.TextDisplay(content=lines),
            accent_color=gc,
        ))
        await si.response.send_message(view=v2, ephemeral=True)

    sel.callback = _log_sel
    container.add_item(discord.ui.ActionRow(sel))
    v.add_item(container)
    await i.response.send_message(view=v, ephemeral=True)


# ══════════════════════════════════════════════════════════════════════
# ■ 설정 > 상품 관리
# ══════════════════════════════════════════════════════════════════════

async def _do_product_menu(i: discord.Interaction, db: str, gc: discord.Color):
    with sqlite3.connect(db) as c:
        cats = c.execute("SELECT id,name FROM categories WHERE guild_id=? ORDER BY id",
                         (str(i.guild.id),)).fetchall()
    v = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 상품 관리"),
        _sep(),
        accent_color=gc,
    )
    if cats:
        container.add_item(discord.ui.TextDisplay(
            content="**카테고리 목록**\n" + "\n".join(f"> **{n}**" for _, n in cats)))
        container.add_item(_sep())
        sel = discord.ui.Select(
            placeholder="카테고리를 선택하세요",
            options=[discord.SelectOption(label=n, value=str(cid)) for cid, n in cats[:25]])

        async def _cat_sel(si: discord.Interaction):
            if str(si.guild.id) != str(i.guild.id):
                await si.response.send_message("권한이 없습니다", ephemeral=True); return
            await _do_product_detail(si, db, gc, int(si.data["values"][0]))

        sel.callback = _cat_sel
        container.add_item(discord.ui.ActionRow(sel))
    else:
        container.add_item(discord.ui.TextDisplay(
            content="등록된 카테고리가 없습니다\n-# 아래 버튼으로 카테고리를 추가하세요"))
        container.add_item(_sep())

    container.add_item(discord.ui.ActionRow(
        discord.ui.Button(label="카테고리 추가", style=discord.ButtonStyle.secondary,
                          custom_id=f"prod_add_cat_{i.guild.id}")
    ))
    v.add_item(container)
    await i.response.send_message(view=v, ephemeral=True)


async def _do_product_detail(i: discord.Interaction, db: str, gc: discord.Color, cat_id: int):
    with sqlite3.connect(db) as c:
        cat   = c.execute("SELECT name FROM categories WHERE id=? AND guild_id=?",
                          (cat_id, str(i.guild.id))).fetchone()
        prods = c.execute(
            "SELECT id,name,price,stock FROM products WHERE category_id=? AND guild_id=? ORDER BY id",
            (cat_id, str(i.guild.id))).fetchall()
    if not cat:
        await i.response.send_message(view=_err("카테고리를 찾을 수 없습니다"), ephemeral=True); return

    v = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"## {cat[0]}"),
        _sep(),
        accent_color=gc,
    )
    if prods:
        container.add_item(discord.ui.TextDisplay(
            content="\n".join(f"> `#{pid}` **{n}** ─ {p:,}원 / 재고 {s}개" for pid, n, p, s in prods)))
        container.add_item(_sep())
        del_sel = discord.ui.Select(
            placeholder="삭제할 제품을 선택하세요",
            options=[discord.SelectOption(label=f"#{pid} {n}", value=str(pid)) for pid, n, *_ in prods[:25]])

        async def _del(si: discord.Interaction):
            if str(si.guild.id) != str(i.guild.id):
                await si.response.send_message("권한이 없습니다", ephemeral=True); return
            pid = int(si.data["values"][0])
            with sqlite3.connect(db) as c:
                row = c.execute("SELECT name FROM products WHERE id=? AND guild_id=?",
                                (pid, str(si.guild.id))).fetchone()
                if not row:
                    await si.response.send_message(view=_err("제품을 찾을 수 없습니다"), ephemeral=True); return
                c.execute("DELETE FROM products WHERE id=? AND guild_id=?", (pid, str(si.guild.id)))
                c.commit()
            await si.response.send_message(view=_layout(
                "## 제품 삭제 완료", f"> **제품명:** {row[0]}\n-# 삭제되었습니다", gc), ephemeral=True)

        del_sel.callback = _del
        container.add_item(discord.ui.ActionRow(del_sel))
    else:
        container.add_item(discord.ui.TextDisplay(content="등록된 제품이 없습니다"))
        container.add_item(_sep())

    container.add_item(discord.ui.ActionRow(
        discord.ui.Button(label="제품 추가", style=discord.ButtonStyle.secondary,
                          custom_id=f"prod_add_{cat_id}_{i.guild.id}"),
        discord.ui.Button(label="카테고리 삭제", style=discord.ButtonStyle.danger,
                          custom_id=f"prod_delcat_{cat_id}_{i.guild.id}"),
    ))
    v.add_item(container)
    await i.response.send_message(view=v, ephemeral=True)


async def _do_issue_token(i: discord.Interaction, db: str, gc: discord.Color):
    with sqlite3.connect(db) as c:
        row = c.execute("SELECT shortcut_token FROM info WHERE guild_id=?", (str(i.guild.id),)).fetchone()
    if not row:
        await i.response.send_message(view=_err("등록된 서버가 아닙니다"), ephemeral=True); return
    existing = row[0]
    if existing:
        v = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## IOS 자충 토큰"),
            _sep(),
            discord.ui.TextDisplay(content=f"> **토큰:** `{existing}`"),
            _sep(),
            discord.ui.TextDisplay(content="-# 재발급하면 기존 토큰은 무효화됩니다\n-# 본인 외에는 절대 공유하지 마세요"),
            accent_color=gc,
        )
        btn = discord.ui.Button(label="재발급", style=discord.ButtonStyle.danger, custom_id="token_reissue")
        container.add_item(discord.ui.ActionRow(btn))
        v.add_item(container)
        await i.response.send_message(view=v, ephemeral=True)
    else:
        tok = secrets.token_hex(24)
        with sqlite3.connect(db) as c:
            c.execute("UPDATE info SET shortcut_token=? WHERE guild_id=?", (tok, str(i.guild.id)))
            c.commit()
        v = discord.ui.LayoutView()
        v.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content="## IOS 자충 토큰"),
            _sep(),
            discord.ui.TextDisplay(content=f"> **토큰:** `{tok}`"),
            _sep(),
            discord.ui.TextDisplay(content="-# 본인 외에는 절대 공유하지 마세요"),
            accent_color=gc,
        ))
        await i.response.send_message(view=v, ephemeral=True)


# ══════════════════════════════════════════════════════════════════════
# ■ 슬래시 명령어
# ══════════════════════════════════════════════════════════════════════

# /등록 — 전역 (모든 서버에서 보임)
@bot.tree.command(name="등록", description="라이센스 키로 서버를 등록합니다")
async def cmd_register(i: discord.Interaction):
    if not i.guild:
        await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
    # 이미 등록된 서버면 안내
    db = _db_by_id(str(i.guild.id))
    if db:
        await i.response.send_message(
            view=_layout("## 이미 등록된 서버", "이 서버는 이미 등록되어 있습니다\n`/설정`으로 자판기를 설정하세요",
                         discord.Color.from_str("#373842")), ephemeral=True); return
    await i.response.send_modal(RegisterModal())


# /자판기 — 등록된 서버에만 동적으로 추가됨
@bot.tree.command(name="자판기", description="자판기를 채널에 전송합니다")
async def cmd_vending(i: discord.Interaction):
    if not i.guild:
        await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
    try:
        db = _db_path(i.guild.name)
    except ValueError:
        await i.response.send_message(view=_err("비정상적인 접근입니다"), ephemeral=True); return
    with sqlite3.connect(db) as c:
        row = c.execute(
            "SELECT vending_title,vending_description,accent_color,enabled_features FROM info WHERE guild_id=?",
            (str(i.guild.id),)).fetchone()
    if not row:
        await i.response.send_message(view=_err("먼저 /등록 명령어로 서버를 등록해주세요"), ephemeral=True); return

    title, desc, color_s, features = row
    title   = _clean(title  or "구매하기", 100)
    desc    = _clean(desc   or "아래 버튼을 눌러 이용해주세요", 500)
    gc      = discord.Color.from_str(_hex(color_s or "#373842"))
    enabled = features.split() if features else []

    await i.response.send_message(
        view=_layout("## 자판기 전송", "자판기가 채널에 전송되었습니다", gc), ephemeral=True)

    v = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"## {title}"),
        _sep(),
        accent_color=gc,
    )
    if desc:
        container.add_item(discord.ui.TextDisplay(content=desc))
        container.add_item(_sep())
    btns = []
    if "구매" in enabled:
        btns.append(discord.ui.Button(label="구매", style=discord.ButtonStyle.secondary,
                                      custom_id="vend_buy", emoji="<:emoji_48:1498298170281558058>"))
    if "제품" in enabled:
        btns.append(discord.ui.Button(label="제품", style=discord.ButtonStyle.secondary,
                                      custom_id="vend_products", emoji="<:emoji_46:1498296760483709029>"))
    if "충전" in enabled:
        btns.append(discord.ui.Button(label="충전", style=discord.ButtonStyle.secondary,
                                      custom_id="vend_charge", emoji="<:emoji_46:1498297238630305903>"))
    if "정보" in enabled:
        btns.append(discord.ui.Button(label="정보", style=discord.ButtonStyle.secondary,
                                      custom_id="vend_info", emoji="<:emoji_47:1498298137406738483>"))
    if btns:
        container.add_item(discord.ui.ActionRow(*btns))
    v.add_item(container)
    await i.channel.send(view=v)


# /설정 — 등록된 서버에만 동적으로 추가됨
@bot.tree.command(name="설정", description="자판기 설정을 관리합니다")
async def cmd_settings(i: discord.Interaction):
    if not i.guild:
        await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
    try:
        db = _db_path(i.guild.name)
    except ValueError:
        await i.response.send_message(view=_err("비정상적인 접근입니다"), ephemeral=True); return
    with sqlite3.connect(db) as c:
        if not c.execute("SELECT 1 FROM info WHERE guild_id=?", (str(i.guild.id),)).fetchone():
            await i.response.send_message(view=_err("먼저 /등록 명령어로 서버를 등록해주세요"), ephemeral=True); return

    gc = _color(str(i.guild.id), db)
    v = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 설정하기"),
        _sep(),
        discord.ui.TextDisplay(content="설정할 항목을 선택하세요"),
        _sep(),
        accent_color=gc,
    )
    sel = discord.ui.Select(placeholder="항목 선택", options=[
        discord.SelectOption(label="자판기 설정",     value="vending"),
        discord.SelectOption(label="계좌 설정",       value="bank"),
        discord.SelectOption(label="충전 설정",       value="charge"),
        discord.SelectOption(label="IOS 자충 토큰",  value="token"),
        discord.SelectOption(label="상품 관리",       value="product"),
    ])

    async def _sel(si: discord.Interaction):
        if si.guild_id != i.guild_id:
            await si.response.send_message("권한이 없습니다", ephemeral=True); return
        val = si.data["values"][0]
        try:
            if   val == "vending":  await si.response.send_modal(VendingSettingModal())
            elif val == "bank":     await si.response.send_modal(BankModal())
            elif val == "charge":   await si.response.send_modal(ChargeSettingModal())
            elif val == "token":    await _do_issue_token(si, db, gc)
            elif val == "product":  await _do_product_menu(si, db, gc)
        except Exception as e:
            print(f"[설정 select 오류] {e}")
            import traceback; traceback.print_exc()
            try:
                if not si.response.is_done():
                    await si.response.send_message(view=_err(f"오류 발생\n-# {type(e).__name__}"), ephemeral=True)
            except Exception:
                pass

    sel.callback = _sel
    container.add_item(discord.ui.ActionRow(sel))
    v.add_item(container)
    await i.response.send_message(view=v, ephemeral=True)


# ── 관리자 전용 명령어 (ADMIN_IDS에게만 표시) ─────────────────────────

@bot.tree.command(name="라이센스_생성", description="[관리자] 라이센스 키를 생성합니다")
@app_commands.describe(기간="기간 선택", 수량="수량 (최대 100)")
@app_commands.choices(기간=[
    app_commands.Choice(name="7일",  value=7),
    app_commands.Choice(name="30일", value=30),
    app_commands.Choice(name="60일", value=60),
    app_commands.Choice(name="90일", value=90),
])
async def cmd_create_license(i: discord.Interaction, 기간: app_commands.Choice[int], 수량: int):
    if not _is_admin(i.user.id):
        await i.response.send_message(view=_err("봇 관리자만 사용 가능합니다"), ephemeral=True); return
    if not 1 <= 수량 <= 100:
        await i.response.send_message(view=_err("1~100개 사이로 입력해주세요"), ephemeral=True); return
    await i.response.defer(ephemeral=True)
    try:
        keys = []
        now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(LICENSE_DB) as c:
            for _ in range(수량):
                k = _make_key()
                c.execute("INSERT INTO licenses(key,days,created_at) VALUES(?,?,?)", (k, 기간.value, now))
                keys.append(k)
            c.commit()
    except Exception as e:
        print(f"[라이센스생성 오류] {e}")
        await i.followup.send(view=_err("생성 중 문제가 발생했습니다"), ephemeral=True); return

    txt = f"VOUT 라이센스 키 목록\n생성일시: {now}\n기간: {기간.value}일 / 수량: {수량}개\n" + "="*50 + "\n\n"
    for idx, k in enumerate(keys, 1):
        txt += f"{idx:>3}. {k}\n"
    fname = f"licenses_{기간.value}일_{수량}개_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    f = discord.File(fp=io.BytesIO(txt.encode()), filename=fname)
    v = discord.ui.LayoutView()
    v.add_item(discord.ui.Container(
        discord.ui.TextDisplay(content="## 라이센스 생성 완료"),
        _sep(),
        discord.ui.TextDisplay(content=f"{수량}개가 생성되었습니다"),
        _sep(),
        discord.ui.File(f"attachment://{fname}"),
        accent_color=discord.Color.from_str("#373842"),
    ))
    await i.followup.send(view=v, file=f, ephemeral=True)


@bot.tree.command(name="라이센스_목록", description="[관리자] 라이센스 키 목록을 조회합니다")
@app_commands.choices(필터=[
    app_commands.Choice(name="전체",   value="all"),
    app_commands.Choice(name="미사용", value="unused"),
    app_commands.Choice(name="사용됨", value="used"),
])
async def cmd_list_license(i: discord.Interaction, 필터: app_commands.Choice[str] = None):
    if not _is_admin(i.user.id):
        await i.response.send_message(view=_err("봇 관리자만 사용 가능합니다"), ephemeral=True); return
    await i.response.defer(ephemeral=True)
    fv = 필터.value if 필터 else "all"
    with sqlite3.connect(LICENSE_DB) as c:
        if fv == "unused": rows = c.execute("SELECT key,days,used,guild_name,created_at FROM licenses WHERE used=0").fetchall()
        elif fv == "used": rows = c.execute("SELECT key,days,used,guild_name,created_at FROM licenses WHERE used=1").fetchall()
        else:              rows = c.execute("SELECT key,days,used,guild_name,created_at FROM licenses").fetchall()
    fl = {"all":"전체","unused":"미사용","used":"사용됨"}.get(fv,"전체")
    if not rows:
        await i.followup.send(view=_layout(
            f"## 라이센스 목록 [{fl}]", "조회된 라이센스가 없습니다",
            discord.Color.from_str("#373842")), ephemeral=True); return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txt = f"VOUT 라이센스 목록 [{fl}]\n조회일시: {now} / 총 {len(rows)}개\n" + "="*60 + "\n\n"
    for idx, (key, days, used, gname, cat) in enumerate(rows, 1):
        st = f"사용됨({gname})" if used else "미사용"
        txt += f"{idx:>3}. {key}  |  {days}일  |  {st}  |  {cat}\n"
    fname = f"licenses_{fv}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    f = discord.File(fp=io.BytesIO(txt.encode()), filename=fname)
    v = discord.ui.LayoutView()
    v.add_item(discord.ui.Container(
        discord.ui.TextDisplay(content=f"## 라이센스 목록 [{fl}]"),
        _sep(),
        discord.ui.TextDisplay(content=f"총 {len(rows)}개 조회되었습니다"),
        _sep(),
        discord.ui.File(f"attachment://{fname}"),
        accent_color=discord.Color.from_str("#373842"),
    ))
    await i.followup.send(view=v, file=f, ephemeral=True)


@bot.tree.command(name="라이센스_삭제", description="[관리자] 라이센스 키를 삭제합니다")
@app_commands.describe(키="삭제할 키")
async def cmd_del_license(i: discord.Interaction, 키: str):
    if not _is_admin(i.user.id):
        await i.response.send_message(view=_err("봇 관리자만 사용 가능합니다"), ephemeral=True); return
    if not _valid_key(키):
        await i.response.send_message(view=_err("올바른 라이센스 키 형식이 아닙니다"), ephemeral=True); return
    with sqlite3.connect(LICENSE_DB) as c:
        row = c.execute("SELECT key,days,used,guild_name FROM licenses WHERE key=?",
                        (키.strip().upper(),)).fetchone()
        if not row:
            await i.response.send_message(view=_err("키를 찾을 수 없습니다"), ephemeral=True); return
        key, days, used, gname = row
        c.execute("DELETE FROM licenses WHERE key=?", (key,))
        c.commit()
    st = f"사용됨 (서버: {gname})" if used else "미사용"
    await i.response.send_message(view=_layout(
        "## 라이센스 삭제 완료",
        f"> **키:** `{key}`\n> **기간:** {days}일\n> **상태:** {st}",
        discord.Color.from_str("#373842")), ephemeral=True)


# ══════════════════════════════════════════════════════════════════════
# ■ FastAPI 엔드포인트
# ══════════════════════════════════════════════════════════════════════

class SmsPayload(BaseModel):
    token:    str
    guild_id: str
    sms_body: str

    @field_validator("guild_id")
    @classmethod
    def _vgid(cls, v):
        if not re.fullmatch(r"\d{17,20}", v): raise ValueError("잘못된 guild_id")
        return v

    @field_validator("sms_body")
    @classmethod
    def _vsms(cls, v):
        if len(v) > 1000: raise ValueError("문자 내용이 너무 깁니다")
        return v

    @field_validator("token")
    @classmethod
    def _vtok(cls, v):
        v = v.strip()
        if not 8 <= len(v) <= 128: raise ValueError("잘못된 토큰")
        return v


@api.post("/webhook/sms")
async def webhook_sms(payload: SmsPayload, req: Request):
    if not _rate(req.client.host):
        raise HTTPException(429, "Too Many Requests")
    print(f"[웹훅] IP={req.client.host} guild={payload.guild_id}")
    db = _db_by_id(payload.guild_id)
    if not db:
        raise HTTPException(404, "서버를 찾을 수 없습니다")
    stored = None
    try:
        with sqlite3.connect(db) as c:
            row = c.execute("SELECT shortcut_token FROM info WHERE guild_id=?", (payload.guild_id,)).fetchone()
            stored = row[0] if row and row[0] else None
    except Exception:
        pass
    if not stored or not hmac.compare_digest(stored, payload.token):
        raise HTTPException(401, "Unauthorized")
    parsed = _parse_sms(payload.sms_body)
    if not parsed:
        raise HTTPException(400, "카카오뱅크 입금 알림 형식이 아닙니다")
    depositor, amount = parsed
    with sqlite3.connect(db) as c:
        row = c.execute(
            "SELECT charge_id FROM charge_pending WHERE status='pending' AND depositor=? AND amount=? ORDER BY created_at LIMIT 1",
            (depositor, amount)).fetchone()
    if not row:
        raise HTTPException(404, "일치하는 충전 대기가 없습니다")
    cid  = row[0]
    body = f"{cid}:{depositor}:{amount}:{payload.guild_id}".encode()
    sig  = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    ok   = await _complete_charge(cid, depositor, amount, payload.guild_id, sig, body)
    if not ok:
        raise HTTPException(400, "충전 처리 실패")
    return {"status": "ok", "charge_id": cid, "amount": amount}


@api.get("/shortcut/guide")
async def shortcut_guide(token: str, guild_id: str, req: Request):
    if not _rate(req.client.host, lim=10):
        raise HTTPException(429, "Too Many Requests")
    if not re.fullmatch(r"\d{17,20}", guild_id):
        raise HTTPException(400, "잘못된 guild_id")
    db = _db_by_id(guild_id)
    if not db:
        raise HTTPException(404, "서버를 찾을 수 없습니다")
    with sqlite3.connect(db) as c:
        row = c.execute("SELECT shortcut_token FROM info WHERE guild_id=?", (guild_id,)).fetchone()
    stored = row[0] if row and row[0] else None
    if not stored or not hmac.compare_digest(stored, token):
        raise HTTPException(401, "Unauthorized")
    return {"steps": [
        "1. iPhone 단축어 앱 > 자동화 > 새 자동화",
        "2. 메시지 수신 > 보낸 사람: 카카오뱅크",
        "3. 동작 추가: URL 가져오기",
        f"4. URL: https://{DOMAIN}/webhook/sms",
        "5. 방법: POST  /  Content-Type: application/json",
        f'6. 본문: {{"token":"{token}","guild_id":"{guild_id}","sms_body":"[수신된 메시지 내용]"}}',
    ]}


@api.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


# ══════════════════════════════════════════════════════════════════════
# ■ 봇 이벤트 + 실행
# ══════════════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    init_license_db()
    migrate_all()

    # Persistent View 등록 (봇 재시작 후에도 버튼 작동)
    bot.add_view(VendingPersistentView())
    bot.add_view(RegisterPersistentView())
    bot.add_view(TokenPersistentView())

    # /등록, 라이센스 명령어만 전역 등록
    await bot.tree.sync()

    # 이미 등록된 서버에는 /자판기 /설정 복원
    for f in os.listdir(DB_DIR):
        if not f.endswith(".db") or f == "라이센스.db":
            continue
        p = os.path.join(DB_DIR, f)
        try:
            with sqlite3.connect(p) as c:
                row = c.execute("SELECT guild_id FROM info LIMIT 1").fetchone()
            if row:
                guild = bot.get_guild(int(row[0]))
                if guild:
                    bot.tree.copy_global_to(guild=guild)
                    await bot.tree.sync(guild=guild)
                    print(f"[명령어 복원] {guild.name}")
        except Exception as e:
            print(f"[명령어 복원 오류] {f}: {e}")

    print(f"{bot.user} 온라인")


async def main():
    config = uvicorn.Config(api, host=API_HOST, port=API_PORT, log_level="info")
    server = uvicorn.Server(config)
    await asyncio.gather(bot.start(TOKEN), server.serve())


if __name__ == "__main__":
    asyncio.run(main())
