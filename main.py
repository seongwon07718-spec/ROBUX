import discord
from discord.ext import commands, tasks
from discord import app_commands
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, field_validator
import uvicorn, sqlite3, random, string, os, io, re, asyncio, secrets, hashlib, hmac
from datetime import datetime, timedelta

# ══════════════════════════════════════════════════════════════════════
# 설정
# ══════════════════════════════════════════════════════════════════════
TOKEN          = ""
ADMIN_IDS: list[int] = [1454398431996018724]
DB_DIR         = "DB"
LICENSE_DB     = os.path.join(DB_DIR, "라이센스.db")
WEBHOOK_SECRET = "f1356103e6b861cb00d3c502cb27d9f66bd84880f70d3b98186fdbd5cd1d840c"
DOMAIN         = "pay.v0ut.com"
API_HOST       = "0.0.0.0"
API_PORT       = 8000

os.makedirs(DB_DIR, exist_ok=True)

pending_charges: dict[str, discord.Interaction] = {}
_rate_store:     dict[str, list]                 = {}

# ══════════════════════════════════════════════════════════════════════
# 유틸
# ══════════════════════════════════════════════════════════════════════

def _safe_name(name: str) -> str:
    return ("".join(c for c in name if c.isalnum() or c in " _-").strip())[:50] or "unknown"

def _db_path(guild_id: str, guild_name: str) -> str:
    fname = f"{guild_id}_{_safe_name(guild_name)}.db"
    p = os.path.abspath(os.path.join(DB_DIR, fname))
    if not p.startswith(os.path.abspath(DB_DIR)):
        raise ValueError("경로 조작 감지")
    return p

def _db_by_id(guild_id: str) -> str | None:
    for f in os.listdir(DB_DIR):
        if f.startswith(f"{guild_id}_") and f.endswith(".db"):
            return os.path.join(DB_DIR, f)
    return None

def _ensure_db_name(guild_id: str, guild_name: str) -> str:
    correct  = _db_path(guild_id, guild_name)
    existing = _db_by_id(guild_id)
    if existing and existing != correct and os.path.exists(existing):
        os.rename(existing, correct)
        print(f"[DB 이름 변경] {os.path.basename(existing)} -> {os.path.basename(correct)}")
    return correct

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

def _color(guild_id: str, db: str) -> discord.Color:
    try:
        with sqlite3.connect(db) as c:
            row = c.execute("SELECT accent_color FROM info WHERE guild_id=?", (guild_id,)).fetchone()
            if row and row[0]:
                return discord.Color.from_str(_hex(row[0]))
    except Exception:
        pass
    return discord.Color.from_str("#373842")

# 컴포넌트 v2 헬퍼
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
    return _layout("## 오류", msg, gc or discord.Color.red())

# ══════════════════════════════════════════════════════════════════════
# DB
# ══════════════════════════════════════════════════════════════════════

def init_license_db():
    with sqlite3.connect(LICENSE_DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS licenses(
            key TEXT PRIMARY KEY, days INTEGER NOT NULL,
            used INTEGER DEFAULT 0, guild_id TEXT, guild_name TEXT,
            created_at TEXT NOT NULL, expires_at TEXT)""")
        c.commit()

def _migrate(p: str):
    with sqlite3.connect(p) as c:
        c.execute("CREATE TABLE IF NOT EXISTS info(guild_id TEXT PRIMARY KEY, guild_name TEXT)")
        for col, typ in [
            ("license_key","TEXT"), ("registered_at","TEXT"), ("expires_at","TEXT"),
            ("vending_title","TEXT DEFAULT '구매하기'"),
            ("vending_description","TEXT DEFAULT '아래 버튼을 눌러 이용해주세요'"),
            ("accent_color","TEXT DEFAULT '#373842'"),
            ("enabled_features","TEXT DEFAULT '제품 구매 충전 정보'"),
            ("bank_name","TEXT DEFAULT ''"), ("account_number","TEXT DEFAULT ''"),
            ("account_holder","TEXT DEFAULT ''"),
            ("min_charge","INTEGER DEFAULT 1000"), ("charge_unit","INTEGER DEFAULT 1000"),
            ("shortcut_token","TEXT"),
        ]:
            try: c.execute(f"ALTER TABLE info ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError: pass

        # 자판기 메시지 저장 테이블 (봇 재시작 시 View 재연결용)
        c.execute("""CREATE TABLE IF NOT EXISTS vending_messages(
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id   TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            message_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL)""")

        c.execute("""CREATE TABLE IF NOT EXISTS users(
            user_id TEXT PRIMARY KEY, username TEXT,
            points INTEGER DEFAULT 0, total_buy INTEGER DEFAULT 0, created_at TEXT)""")
        try: c.execute("ALTER TABLE users ADD COLUMN total_buy INTEGER DEFAULT 0")
        except sqlite3.OperationalError: pass

        c.execute("""CREATE TABLE IF NOT EXISTS charge_pending(
            charge_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, username TEXT,
            depositor TEXT NOT NULL, amount INTEGER NOT NULL,
            status TEXT DEFAULT 'pending', created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL, completed_at TEXT,
            channel_id TEXT, message_id TEXT)""")

        c.execute("""CREATE TABLE IF NOT EXISTS charge_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT,
            charge_id TEXT, user_id TEXT, username TEXT, depositor TEXT,
            amount INTEGER, status TEXT, created_at TEXT, completed_at TEXT)""")
        try: c.execute("ALTER TABLE charge_history ADD COLUMN guild_id TEXT")
        except sqlite3.OperationalError: pass

        c.execute("""CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT NOT NULL)""")

        c.execute("""CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL, category_id INTEGER NOT NULL,
            name TEXT NOT NULL, price INTEGER NOT NULL, stock INTEGER NOT NULL,
            content TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(category_id) REFERENCES categories(id))""")

        c.execute("""CREATE TABLE IF NOT EXISTS purchase_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL, username TEXT, product_id INTEGER,
            name TEXT, price INTEGER, qty INTEGER, created_at TEXT NOT NULL)""")
        c.commit()

def _init_guild_db(guild_id: str, guild_name: str) -> str:
    """등록 단계를 거쳐야만 DB 생성"""
    p = _db_path(guild_id, guild_name)
    _migrate(p)
    return p

def _migrate_all():
    for f in os.listdir(DB_DIR):
        if f.endswith(".db") and f != "라이센스.db":
            try: _migrate(os.path.join(DB_DIR, f))
            except Exception as e: print(f"[마이그레이션 오류] {f}: {e}")

def _cleanup_expired():
    """만료된 서버 DB 삭제"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(LICENSE_DB) as lc:
        rows = lc.execute(
            "SELECT guild_id FROM licenses WHERE used=1 AND expires_at IS NOT NULL AND expires_at < ?",
            (now,)).fetchall()
    for (gid,) in rows:
        if not gid: continue
        p = _db_by_id(gid)
        if p and os.path.exists(p):
            try:
                os.remove(p)
                print(f"[DB 삭제] 만료 서버 {gid}")
            except Exception as e:
                print(f"[DB 삭제 오류] {gid}: {e}")

def _save_vending_message(guild_id: str, channel_id: str, message_id: str, db: str):
    with sqlite3.connect(db) as c:
        c.execute(
            "INSERT OR IGNORE INTO vending_messages(guild_id,channel_id,message_id,created_at) "
            "VALUES(?,?,?,?)",
            (guild_id, channel_id, message_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        c.commit()

def _get_vending_messages(db: str) -> list[tuple[str, str, str]]:
    """(guild_id, channel_id, message_id) 목록 반환"""
    with sqlite3.connect(db) as c:
        return c.execute("SELECT guild_id, channel_id, message_id FROM vending_messages").fetchall()

def _delete_vending_message(message_id: str, db: str):
    with sqlite3.connect(db) as c:
        c.execute("DELETE FROM vending_messages WHERE message_id=?", (message_id,))
        c.commit()

# ══════════════════════════════════════════════════════════════════════
# 라이센스 키 생성
# ══════════════════════════════════════════════════════════════════════

def _make_key() -> str:
    def r(n): return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))
    for _ in range(1000):
        k = f"VOUT-{r(6)}-{r(4)}-{r(4)}"
        with sqlite3.connect(LICENSE_DB) as c:
            if not c.execute("SELECT 1 FROM licenses WHERE key=?", (k,)).fetchone():
                return k
    raise RuntimeError("키 생성 실패")

# ══════════════════════════════════════════════════════════════════════
# SMS 파싱
# ══════════════════════════════════════════════════════════════════════

def _parse_sms(sms: str) -> tuple[str, int] | None:
    if "[카카오뱅크]" not in sms:
        return None
    lines = [l.strip() for l in sms.splitlines() if l.strip()]
    for idx, line in enumerate(lines):
        m = re.search(r"입금\s+([\d,]+)원", line)
        if m:
            try: amt = int(m.group(1).replace(",", ""))
            except ValueError: return None
            if idx + 1 < len(lines):
                dep = lines[idx + 1]
                if not re.search(r"잔액", dep) and re.fullmatch(r"[가-힣a-zA-Z0-9]{1,20}", dep):
                    if 0 < amt <= 10_000_000:
                        return dep, amt
    return None

# ══════════════════════════════════════════════════════════════════════
# 봇
# ══════════════════════════════════════════════════════════════════════

class VoutBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 글로벌 명령어 sync
        await self.tree.sync()
        print("[명령어 sync 완료]")

    async def on_ready(self):
        init_license_db()
        _migrate_all()
        # 봇 재시작 시 DB에 저장된 자판기 메시지에 View 재연결
        await _reconnect_vending_views(self)
        expire_task.start()
        print(f"[온라인] {self.user}")

bot = VoutBot()
api = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

@tasks.loop(hours=1)
async def expire_task():
    try: _cleanup_expired()
    except Exception as e: print(f"[만료 정리 오류] {e}")

# ══════════════════════════════════════════════════════════════════════
# 자판기 View 생성 / 재연결
# ══════════════════════════════════════════════════════════════════════

def _make_vending_view(enabled: list[str], guild_id: str, db: str) -> discord.ui.View:
    """
    활성화된 버튼만 포함한 자판기 View.
    custom_id에 guild_id 포함 -> 서버별 고유 ID.
    timeout=None (영구).
    """
    view = discord.ui.View(timeout=None)

    if "구매" in enabled:
        btn = discord.ui.Button(
            label="구매", style=discord.ButtonStyle.secondary,
            custom_id=f"vend_buy_{guild_id}")
        async def _buy(i: discord.Interaction):
            if not i.guild: return
            d = _ensure_db_name(str(i.guild.id), i.guild.name)
            gc = _color(str(i.guild.id), d)
            await _do_buy(i, d, gc)
        btn.callback = _buy
        view.add_item(btn)

    if "제품" in enabled:
        btn = discord.ui.Button(
            label="제품", style=discord.ButtonStyle.secondary,
            custom_id=f"vend_products_{guild_id}")
        async def _products(i: discord.Interaction):
            if not i.guild: return
            d = _ensure_db_name(str(i.guild.id), i.guild.name)
            gc = _color(str(i.guild.id), d)
            await _do_products(i, d, gc)
        btn.callback = _products
        view.add_item(btn)

    if "충전" in enabled:
        btn = discord.ui.Button(
            label="충전", style=discord.ButtonStyle.secondary,
            custom_id=f"vend_charge_{guild_id}")
        async def _charge(i: discord.Interaction):
            if not i.guild: return
            d = _ensure_db_name(str(i.guild.id), i.guild.name)
            gc = _color(str(i.guild.id), d)
            with sqlite3.connect(d) as c:
                row = c.execute("SELECT bank_name,account_number FROM info WHERE guild_id=?",
                                (str(i.guild.id),)).fetchone()
            if not row or not row[0] or not row[1]:
                await i.response.send_message(
                    view=_err("계좌 정보가 설정되지 않았습니다\n-# 관리자에게 문의하세요"), ephemeral=True); return
            await _do_charge_menu(i, d, gc)
        btn.callback = _charge
        view.add_item(btn)

    if "정보" in enabled:
        btn = discord.ui.Button(
            label="정보", style=discord.ButtonStyle.secondary,
            custom_id=f"vend_info_{guild_id}")
        async def _info(i: discord.Interaction):
            if not i.guild: return
            d = _ensure_db_name(str(i.guild.id), i.guild.name)
            gc = _color(str(i.guild.id), d)
            await _do_info(i, d, gc)
        btn.callback = _info
        view.add_item(btn)

    return view


async def _reconnect_vending_views(bot_instance: commands.Bot):
    """
    봇 재시작 시 DB에 저장된 모든 자판기 메시지를 찾아 View 재연결.
    메시지가 삭제됐거나 채널이 없으면 DB 기록도 삭제.
    """
    count = 0
    for fname in os.listdir(DB_DIR):
        if not fname.endswith(".db") or fname == "라이센스.db":
            continue
        db = os.path.join(DB_DIR, fname)
        try:
            rows = _get_vending_messages(db)
        except Exception:
            continue

        for guild_id_str, channel_id_str, message_id_str in rows:
            try:
                channel = bot_instance.get_channel(int(channel_id_str))
                if channel is None:
                    channel = await bot_instance.fetch_channel(int(channel_id_str))

                msg = await channel.fetch_message(int(message_id_str))

                with sqlite3.connect(db) as c:
                    row = c.execute(
                        "SELECT enabled_features FROM info WHERE guild_id=?",
                        (guild_id_str,)).fetchone()
                enabled = (row[0] if row and row[0] else "제품 구매 충전 정보").split()

                view = _make_vending_view(enabled, guild_id_str, db)
                # bot에 View 등록 (재시작 후 상호작용 수신 가능하게)
                bot_instance.add_view(view, message_id=int(message_id_str))
                await msg.edit(view=view)
                count += 1

            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                # 메시지 또는 채널이 없으면 DB 기록 삭제
                _delete_vending_message(message_id_str, db)
            except Exception as e:
                print(f"[자판기 재연결 오류] msg={message_id_str}: {e}")

    print(f"[자판기 재연결] {count}개 복구 완료")

# ══════════════════════════════════════════════════════════════════════
# 모달
# ══════════════════════════════════════════════════════════════════════

class RegisterModal(discord.ui.Modal, title="서버 등록"):
    key = discord.ui.TextInput(
        label="라이센스 키", placeholder="VOUT-XXXXXX-XXXX-XXXX",
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

        v = discord.ui.LayoutView()
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

        async def _confirm(si: discord.Interaction):
            await si.response.defer(ephemeral=True)
            try:
                with sqlite3.connect(LICENSE_DB) as c:
                    r = c.execute("SELECT used FROM licenses WHERE key=?", (key,)).fetchone()
                    if not r or r[0]:
                        await si.edit_original_response(view=_err("이미 사용된 라이센스입니다")); return
                    c.execute(
                        "UPDATE licenses SET used=1,guild_id=?,guild_name=?,expires_at=? WHERE key=? AND used=0",
                        (str(si.guild.id), si.guild.name[:100], expires, key))
                    if c.execute("SELECT changes()").fetchone()[0] == 0:
                        await si.edit_original_response(view=_err("이미 사용된 라이센스입니다")); return
                    c.commit()
                now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                db = _init_guild_db(str(si.guild.id), si.guild.name)   # 등록 후에만 DB 생성
                with sqlite3.connect(db) as c:
                    c.execute(
                        "INSERT OR REPLACE INTO info(guild_id,guild_name,license_key,registered_at,expires_at) "
                        "VALUES(?,?,?,?,?)",
                        (str(si.guild.id), si.guild.name[:100], key, now_s, expires))
                    c.commit()
                await si.edit_original_response(view=_layout(
                    "## 서버 등록 완료",
                    f"> **서버:** {si.guild.name}\n> **기간:** {days}일\n"
                    f"> **만료일:** {expires}\n\n`/설정`으로 자판기를 설정하세요",
                    discord.Color.green()))
            except Exception as e:
                print(f"[등록 오류] {e}")
                await si.edit_original_response(view=_err("처리 중 오류가 발생했습니다"))

        async def _cancel(si: discord.Interaction):
            await si.response.defer(ephemeral=True)
            await si.edit_original_response(
                view=_layout("## 등록 취소", "서버 등록이 취소되었습니다",
                             discord.Color.from_str("#99AAB5")))

        btn_ok = discord.ui.Button(label="진행", style=discord.ButtonStyle.success)
        btn_ok.callback = _confirm
        btn_no = discord.ui.Button(label="취소", style=discord.ButtonStyle.secondary)
        btn_no.callback = _cancel
        container.add_item(discord.ui.ActionRow(btn_ok, btn_no))
        v.add_item(container)
        await i.response.send_message(view=v, ephemeral=True)


class VendingSettingModal(discord.ui.Modal, title="자판기 설정"):
    t = discord.ui.TextInput(label="자판기 제목", placeholder="구매하기",  required=True,  max_length=100)
    d = discord.ui.TextInput(label="자판기 설명", style=discord.TextStyle.long, required=False, max_length=500)
    c = discord.ui.TextInput(label="색상 (HEX)",  placeholder="#373842", required=True,  max_length=7)

    async def on_submit(self, i: discord.Interaction):
        if not i.guild: return
        title = _clean(self.t.value, 100)
        desc  = _clean(self.d.value or "", 500)
        color = _hex(self.c.value)
        if not title:
            await i.response.send_message(view=_err("제목을 입력해주세요"), ephemeral=True); return
        db = _ensure_db_name(str(i.guild.id), i.guild.name)
        with sqlite3.connect(db) as c:
            c.execute("UPDATE info SET vending_title=?,vending_description=?,accent_color=? WHERE guild_id=?",
                      (title, desc, color, str(i.guild.id)))
            c.commit()
        await i.response.send_message(view=_layout(
            "## 설정 저장 완료",
            f"> **제목:** {title}\n> **설명:** {desc or '없음'}\n> **색상:** `{color}`",
            discord.Color.from_str(color)), ephemeral=True)


class BankModal(discord.ui.Modal, title="계좌 설정"):
    bn = discord.ui.TextInput(label="은행명",   placeholder="카카오뱅크",    required=True, max_length=20)
    ac = discord.ui.TextInput(label="계좌번호", placeholder="10-123-456789", required=True, max_length=30)
    ah = discord.ui.TextInput(label="예금주",   placeholder="홍길동",         required=True, max_length=20)

    async def on_submit(self, i: discord.Interaction):
        if not i.guild: return
        bank   = _clean(self.bn.value, 20)
        number = _clean(self.ac.value, 30)
        holder = _clean(self.ah.value, 20)
        if not re.fullmatch(r"[\d\-]+", number):
            await i.response.send_message(view=_err("계좌번호는 숫자와 - 만 입력 가능합니다"), ephemeral=True); return
        db = _ensure_db_name(str(i.guild.id), i.guild.name)
        gc = _color(str(i.guild.id), db)
        with sqlite3.connect(db) as c:
            c.execute("UPDATE info SET bank_name=?,account_number=?,account_holder=? WHERE guild_id=?",
                      (bank, number, holder, str(i.guild.id)))
            c.commit()
        await i.response.send_message(view=_layout(
            "## 계좌 설정 완료",
            f"> **은행명:** {bank}\n> **계좌번호:** `{number}`\n> **예금주:** {holder}",
            gc), ephemeral=True)


class ChargeSettingModal(discord.ui.Modal, title="충전 설정"):
    mi = discord.ui.TextInput(label="최소 충전금액 (원)", placeholder="1000", required=True, max_length=10)
    un = discord.ui.TextInput(label="충전 단위 (원)",     placeholder="1000", required=True, max_length=10)

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
        db = _ensure_db_name(str(i.guild.id), i.guild.name)
        gc = _color(str(i.guild.id), db)
        with sqlite3.connect(db) as c:
            c.execute("UPDATE info SET min_charge=?,charge_unit=? WHERE guild_id=?",
                      (mn, un, str(i.guild.id)))
            c.commit()
        await i.response.send_message(view=_layout(
            "## 충전 설정 완료",
            f"> **최소 충전금액:** {mn:,}원\n> **충전 단위:** {un:,}원",
            gc), ephemeral=True)


class AddCategoryModal(discord.ui.Modal, title="카테고리 추가"):
    name = discord.ui.TextInput(label="카테고리 이름", placeholder="로블록스 아이템", required=True, max_length=30)

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
        db = _ensure_db_name(self.gid, self.gname)
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
            f"> **카테고리:** {name}\n-# `/설정` > 상품 관리에서 제품을 추가할 수 있습니다",
            gc), ephemeral=True)


class AddProductModal(discord.ui.Modal, title="제품 추가"):
    pname   = discord.ui.TextInput(label="제품명",      placeholder="로블록스 100R", required=True,  max_length=50)
    price   = discord.ui.TextInput(label="가격 (원)",   placeholder="5000",          required=True,  max_length=10)
    stock   = discord.ui.TextInput(label="재고 수량",   placeholder="10",            required=True,  max_length=6)
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
        db = _ensure_db_name(self.gid, self.gname)
        gc = _color(self.gid, db)
        with sqlite3.connect(db) as c:
            if not c.execute("SELECT 1 FROM categories WHERE id=? AND guild_id=?",
                             (self.cat_id, self.gid)).fetchone():
                await i.response.send_message(view=_err("카테고리를 찾을 수 없습니다"), ephemeral=True); return
            c.execute(
                "INSERT INTO products(guild_id,category_id,name,price,stock,content,created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (self.gid, self.cat_id, name, price, stock, content,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            c.commit()
        await i.response.send_message(view=_layout(
            "## 제품 추가 완료",
            f"> **제품명:** {name}\n> **가격:** {price:,}원\n> **재고:** {stock}개",
            gc), ephemeral=True)


class BuyQtyModal(discord.ui.Modal, title="구매 수량"):
    qty = discord.ui.TextInput(label="수량", placeholder="1", required=True, max_length=4)

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
        if qty > 99:
            await i.response.send_message(view=_err("1회 최대 구매 수량은 99개입니다"), ephemeral=True); return

        db = _ensure_db_name(self.gid, self.gname)
        gc = _color(self.gid, db)
        with sqlite3.connect(db) as c:
            prod = c.execute("SELECT name,price,stock,content FROM products WHERE id=? AND guild_id=?",
                             (self.pid, self.gid)).fetchone()
        if not prod:
            await i.response.send_message(view=_err("제품을 찾을 수 없습니다"), ephemeral=True); return
        name, price, stock, content = prod

        if stock <= 0:
            await i.response.send_message(view=_err(f"**{name}** 은 품절입니다"), ephemeral=True); return
        if qty > stock:
            await i.response.send_message(view=_err(f"재고 부족\n-# 현재 재고: {stock}개"), ephemeral=True); return

        total = price * qty
        with sqlite3.connect(db) as c:
            pts = c.execute("SELECT points FROM users WHERE user_id=?", (str(i.user.id),)).fetchone()
        points = pts[0] if pts else 0
        if points < total:
            await i.response.send_message(
                view=_err(f"잔액 부족\n-# 필요: {total:,}원 / 보유: {points:,}원"), ephemeral=True); return

        await i.response.defer(ephemeral=True)
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
                "INSERT INTO purchase_history(guild_id,user_id,username,product_id,name,price,qty,created_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (self.gid, str(i.user.id), str(i.user), self.pid, name, price, qty, now))
            c.commit()

        try:
            await i.user.send(f"**{name}** {qty}개 구매 완료\n결제 금액: {total:,}원\n```\n{content}\n```")
            dm_ok = True
        except Exception:
            dm_ok = False

        await i.edit_original_response(view=_layout(
            "## 구매 완료",
            f"> **제품명:** {name}\n> **수량:** {qty}개\n"
            f"> **결제 금액:** {total:,}원\n> **남은 잔액:** {new_pts:,}원\n\n"
            + ("-# 제품 내용물이 DM으로 전송되었습니다" if dm_ok
               else "-# DM 전송 실패 — DM 허용 후 관리자에게 문의하세요"),
            gc))


class TransferModal(discord.ui.Modal, title="계좌이체 충전"):
    dep = discord.ui.TextInput(label="입금자명",       placeholder="홍길동", required=True, max_length=20)
    amt = discord.ui.TextInput(label="충전 금액 (원)", placeholder="10000",  required=True, max_length=10)

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

        db = _ensure_db_name(self.gid, self.gname)
        gc = _color(self.gid, db)
        with sqlite3.connect(db) as c:
            row = c.execute(
                "SELECT bank_name,account_number,account_holder,min_charge,charge_unit "
                "FROM info WHERE guild_id=?", (self.gid,)).fetchone()
        if not row:
            await i.response.send_message(view=_err("등록된 서버가 아닙니다"), ephemeral=True); return
        bank, acnum, holder, min_c, unit = row
        min_c = min_c or 1000
        unit  = unit  or 1000

        if not bank or not acnum:
            await i.response.send_message(
                view=_err("계좌 정보가 설정되지 않았습니다\n-# 관리자에게 문의하세요"), ephemeral=True); return
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
                "INSERT INTO charge_pending(charge_id,user_id,username,depositor,amount,status,created_at,expires_at) "
                "VALUES(?,?,?,?,?,'pending',?,?)",
                (cid, str(i.user.id), str(i.user), depositor, amount,
                 now.strftime("%Y-%m-%d %H:%M:%S"), expires.strftime("%Y-%m-%d %H:%M:%S")))
            c.commit()

        v = discord.ui.LayoutView()
        v.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content="## 계좌 안내"),
            _sep(),
            discord.ui.TextDisplay(content=f"> **은행명:** {bank}\n> **계좌번호:** `{acnum}`\n> **예금주:** {holder}"),
            _sep(),
            discord.ui.TextDisplay(content=f"> **입금금액:** {amount:,}원\n> **입금자명:** {depositor}\n"
                                           f"> **만료시각:** {expires.strftime('%H:%M:%S')} (5분)"),
            _sep(),
            discord.ui.TextDisplay(content="-# 입금자명을 정확히 입력 후 이체해주세요\n"
                                           "-# 5분 내 입금이 확인되지 않으면 자동 취소됩니다"),
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
# 충전 타이머 / 완료
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
        await i.edit_original_response(view=_layout(
            "## 충전 취소",
            "-# 입금이 확인되지 않아 충전이 취소되었습니다\n-# 다시 충전하려면 충전 버튼을 눌러주세요",
            discord.Color.red()))
    except Exception as e:
        print(f"[충전타이머 오류] {e}")
    finally:
        pending_charges.pop(cid, None)


async def _complete_charge(cid: str, depositor: str, amount: int, guild_id: str) -> bool:
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
            return False
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "UPDATE charge_pending SET status='completed',completed_at=? WHERE charge_id=? AND status='pending'",
            (now, cid))
        if c.execute("SELECT changes()").fetchone()[0] == 0:
            return False
        c.execute(
            """INSERT INTO users(user_id,username,points,total_buy,created_at) VALUES(?,?,?,0,?)
               ON CONFLICT(user_id) DO UPDATE SET points=points+?,username=excluded.username""",
            (uid, uname, amount, now, amount))
        c.execute(
            "INSERT INTO charge_history(guild_id,charge_id,user_id,username,depositor,amount,status,created_at,completed_at) "
            "VALUES(?,?,?,?,?,?,'completed',?,?)",
            (guild_id, cid, uid, uname, depositor, amount, now, now))
        new_pts = c.execute("SELECT points FROM users WHERE user_id=?", (uid,)).fetchone()[0]
        c.commit()

    orig = pending_charges.pop(cid, None)
    if orig:
        try:
            await orig.edit_original_response(view=_layout(
                "## 충전 완료",
                f"> **충전 금액:** {amount:,}원\n> **보유 잔액:** {new_pts:,}원\n\n-# 처리시각: {now}",
                gc))
        except Exception:
            pass
    return True

# ══════════════════════════════════════════════════════════════════════
# 자판기 기능 함수
# ══════════════════════════════════════════════════════════════════════

async def _do_charge_menu(i: discord.Interaction, db: str, gc: discord.Color):
    v = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 결제수단"),
        _sep(),
        discord.ui.TextDisplay(content="충전 방법을 선택하세요"),
        _sep(),
        accent_color=gc,
    )
    btn = discord.ui.Button(label="계좌이체", style=discord.ButtonStyle.secondary)
    async def _cb(si: discord.Interaction):
        await si.response.send_modal(TransferModal(str(si.guild.id), si.guild.name))
    btn.callback = _cb
    container.add_item(discord.ui.ActionRow(btn))
    v.add_item(container)
    await i.response.send_message(view=v, ephemeral=True)


async def _do_products(i: discord.Interaction, db: str, gc: discord.Color):
    with sqlite3.connect(db) as c:
        cats = c.execute("SELECT id,name FROM categories WHERE guild_id=? ORDER BY id",
                         (str(i.guild.id),)).fetchall()
    if not cats:
        await i.response.send_message(view=_err("등록된 상품이 없습니다\n-# 관리자에게 문의하세요"), ephemeral=True); return

    sel = discord.ui.Select(
        placeholder="카테고리 선택",
        options=[discord.SelectOption(label=n, value=str(cid)) for cid, n in cats[:25]])

    async def _on_cat(si: discord.Interaction):
        cat_id = int(si.data["values"][0])
        with sqlite3.connect(db) as c:
            cat   = c.execute("SELECT name FROM categories WHERE id=? AND guild_id=?",
                              (cat_id, str(si.guild.id))).fetchone()
            prods = c.execute("SELECT name,price,stock FROM products WHERE category_id=? AND guild_id=? ORDER BY id",
                              (cat_id, str(si.guild.id))).fetchall()
        if not cat:
            await si.response.send_message(view=_err("카테고리를 찾을 수 없습니다"), ephemeral=True); return
        lines = "\n".join(
            f"> **{n}** — {p:,}원 / {'품절' if s == 0 else f'재고 {s}개'}"
            for n, p, s in prods) if prods else "등록된 제품이 없습니다"
        v2 = discord.ui.LayoutView()
        v2.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content=f"## {cat[0]}"),
            _sep(),
            discord.ui.TextDisplay(content=lines),
            accent_color=gc,
        ))
        await si.response.send_message(view=v2, ephemeral=True)

    sel.callback = _on_cat
    v = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 제품"),
        _sep(),
        discord.ui.TextDisplay(content="확인할 카테고리를 선택하세요"),
        _sep(),
        accent_color=gc,
    )
    container.add_item(discord.ui.ActionRow(sel))
    v.add_item(container)
    await i.response.send_message(view=v, ephemeral=True)


async def _do_buy(i: discord.Interaction, db: str, gc: discord.Color):
    with sqlite3.connect(db) as c:
        cats = c.execute("SELECT id,name FROM categories WHERE guild_id=? ORDER BY id",
                         (str(i.guild.id),)).fetchall()
    if not cats:
        await i.response.send_message(view=_err("등록된 상품이 없습니다\n-# 관리자에게 문의하세요"), ephemeral=True); return

    sel = discord.ui.Select(
        placeholder="카테고리 선택",
        options=[discord.SelectOption(label=n, value=str(cid)) for cid, n in cats[:25]])

    async def _on_cat(si: discord.Interaction):
        cat_id = int(si.data["values"][0])
        with sqlite3.connect(db) as c:
            cat   = c.execute("SELECT name FROM categories WHERE id=? AND guild_id=?",
                              (cat_id, str(si.guild.id))).fetchone()
            prods = c.execute(
                "SELECT id,name,price,stock FROM products "
                "WHERE category_id=? AND guild_id=? AND stock>0 ORDER BY id",
                (cat_id, str(si.guild.id))).fetchall()
        if not cat:
            await si.response.send_message(view=_err("카테고리를 찾을 수 없습니다"), ephemeral=True); return
        if not prods:
            await si.response.send_message(
                view=_err(f"**{cat[0]}** 카테고리의 모든 상품이 품절입니다"), ephemeral=True); return

        sel2 = discord.ui.Select(
            placeholder="제품 선택",
            options=[discord.SelectOption(label=f"{n} — {p:,}원", value=str(pid))
                     for pid, n, p, s in prods[:25]])

        async def _on_prod(si2: discord.Interaction):
            prod_id = int(si2.data["values"][0])
            with sqlite3.connect(db) as c:
                row = c.execute("SELECT stock FROM products WHERE id=? AND guild_id=?",
                                (prod_id, str(si2.guild.id))).fetchone()
            if not row or row[0] <= 0:
                await si2.response.send_message(
                    view=_err("품절된 상품입니다\n-# 다른 제품을 선택해주세요"), ephemeral=True); return
            await si2.response.send_modal(BuyQtyModal(str(si2.guild.id), si2.guild.name, prod_id))

        sel2.callback = _on_prod
        v2 = discord.ui.LayoutView()
        container2 = discord.ui.Container(
            discord.ui.TextDisplay(content=f"## {cat[0]}"),
            _sep(),
            discord.ui.TextDisplay(content="\n".join(
                f"> **{n}** — {p:,}원 / 재고 {s}개" for _, n, p, s in prods)),
            _sep(),
            discord.ui.TextDisplay(content="-# 구매할 제품을 선택하세요"),
            accent_color=gc,
        )
        container2.add_item(discord.ui.ActionRow(sel2))
        v2.add_item(container2)
        await si.response.send_message(view=v2, ephemeral=True)

    sel.callback = _on_cat
    v = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 구매"),
        _sep(),
        discord.ui.TextDisplay(content="구매할 카테고리를 선택하세요"),
        _sep(),
        accent_color=gc,
    )
    container.add_item(discord.ui.ActionRow(sel))
    v.add_item(container)
    await i.response.send_message(view=v, ephemeral=True)


async def _do_info(i: discord.Interaction, db: str, gc: discord.Color):
    with sqlite3.connect(db) as c:
        user = c.execute("SELECT points,total_buy FROM users WHERE user_id=?", (str(i.user.id),)).fetchone()
    points    = user[0] if user else 0
    total_buy = user[1] if user else 0
    discount  = 5 if total_buy >= 500_000 else (3 if total_buy >= 100_000 else 0)

    sel = discord.ui.Select(placeholder="로그 조회", options=[
        discord.SelectOption(label="최근 충전 로그", value="charge_log"),
        discord.SelectOption(label="최근 구매 로그", value="buy_log"),
    ])

    async def _on_log(si: discord.Interaction):
        if str(si.user.id) != str(i.user.id):
            await si.response.send_message("본인만 조회 가능합니다", ephemeral=True); return
        val = si.data["values"][0]
        if val == "charge_log":
            with sqlite3.connect(db) as c:
                rows = c.execute(
                    "SELECT amount,status,created_at FROM charge_history "
                    "WHERE user_id=? AND guild_id=? ORDER BY id DESC LIMIT 5",
                    (str(si.user.id), str(si.guild.id))).fetchall()
            lines = "\n".join(
                f"> {a:,}원 — {'완료' if s == 'completed' else '취소'} — {t[:16]}"
                for a, s, t in rows) if rows else "-# 충전 내역이 없습니다"
            title = "## 최근 충전 로그"
        else:
            with sqlite3.connect(db) as c:
                rows = c.execute(
                    "SELECT name,price,qty,created_at FROM purchase_history "
                    "WHERE user_id=? AND guild_id=? ORDER BY id DESC LIMIT 5",
                    (str(si.user.id), str(si.guild.id))).fetchall()
            lines = "\n".join(
                f"> **{n}** {q}개 — {p*q:,}원 — {t[:16]}"
                for n, p, q, t in rows) if rows else "-# 구매 내역이 없습니다"
            title = "## 최근 구매 로그"
        v2 = discord.ui.LayoutView()
        v2.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content=title),
            _sep(),
            discord.ui.TextDisplay(content=lines),
            accent_color=gc,
        ))
        await si.response.send_message(view=v2, ephemeral=True)

    sel.callback = _on_log
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
    container.add_item(discord.ui.ActionRow(sel))
    v.add_item(container)
    await i.response.send_message(view=v, ephemeral=True)


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
        async def _on_cat(si: discord.Interaction):
            await _do_product_detail(si, db, gc, int(si.data["values"][0]))
        sel.callback = _on_cat
        container.add_item(discord.ui.ActionRow(sel))
    else:
        container.add_item(discord.ui.TextDisplay(content="등록된 카테고리가 없습니다\n-# 아래 버튼으로 추가하세요"))
        container.add_item(_sep())

    btn_add = discord.ui.Button(label="카테고리 추가", style=discord.ButtonStyle.secondary)
    async def _add_cat(si: discord.Interaction):
        await si.response.send_modal(AddCategoryModal(str(si.guild.id), si.guild.name))
    btn_add.callback = _add_cat
    container.add_item(discord.ui.ActionRow(btn_add))
    v.add_item(container)
    await i.response.send_message(view=v, ephemeral=True)


async def _do_product_detail(i: discord.Interaction, db: str, gc: discord.Color, cat_id: int):
    with sqlite3.connect(db) as c:
        cat   = c.execute("SELECT name FROM categories WHERE id=? AND guild_id=?",
                          (cat_id, str(i.guild.id))).fetchone()
        prods = c.execute("SELECT id,name,price,stock FROM products WHERE category_id=? AND guild_id=? ORDER BY id",
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
            content="\n".join(f"> `#{pid}` **{n}** — {p:,}원 / 재고 {s}개" for pid, n, p, s in prods)))
        container.add_item(_sep())
        del_sel = discord.ui.Select(
            placeholder="삭제할 제품을 선택하세요",
            options=[discord.SelectOption(label=f"#{pid} {n}", value=str(pid)) for pid, n, *_ in prods[:25]])
        async def _del(si: discord.Interaction):
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

    btn_add = discord.ui.Button(label="제품 추가", style=discord.ButtonStyle.secondary)
    btn_del_cat = discord.ui.Button(label="카테고리 삭제", style=discord.ButtonStyle.danger)

    async def _add_prod(si: discord.Interaction):
        await si.response.send_modal(AddProductModal(str(si.guild.id), si.guild.name, cat_id))

    async def _del_cat(si: discord.Interaction):
        with sqlite3.connect(db) as c:
            cat_row = c.execute("SELECT name FROM categories WHERE id=? AND guild_id=?",
                                (cat_id, str(si.guild.id))).fetchone()
            if not cat_row:
                await si.response.send_message(view=_err("카테고리를 찾을 수 없습니다"), ephemeral=True); return
            cnt = c.execute("SELECT COUNT(*) FROM products WHERE category_id=? AND guild_id=?",
                            (cat_id, str(si.guild.id))).fetchone()[0]
            c.execute("DELETE FROM products WHERE category_id=? AND guild_id=?", (cat_id, str(si.guild.id)))
            c.execute("DELETE FROM categories WHERE id=? AND guild_id=?", (cat_id, str(si.guild.id)))
            c.commit()
        await si.response.send_message(view=_layout(
            "## 카테고리 삭제 완료",
            f"> **카테고리:** {cat_row[0]}\n> **삭제된 제품:** {cnt}개\n-# 하위 제품이 모두 삭제되었습니다",
            gc), ephemeral=True)

    btn_add.callback     = _add_prod
    btn_del_cat.callback = _del_cat
    container.add_item(discord.ui.ActionRow(btn_add, btn_del_cat))
    v.add_item(container)
    await i.response.send_message(view=v, ephemeral=True)


async def _do_token(i: discord.Interaction, db: str, gc: discord.Color):
    with sqlite3.connect(db) as c:
        row = c.execute("SELECT shortcut_token FROM info WHERE guild_id=?", (str(i.guild.id),)).fetchone()
    if not row:
        await i.response.send_message(view=_err("등록된 서버가 아닙니다"), ephemeral=True); return

    existing = row[0]
    if not existing:
        existing = secrets.token_hex(24)
        with sqlite3.connect(db) as c:
            c.execute("UPDATE info SET shortcut_token=? WHERE guild_id=?", (existing, str(i.guild.id)))
            c.commit()

    btn_reissue = discord.ui.Button(label="재발급", style=discord.ButtonStyle.danger)

    async def _reissue(si: discord.Interaction):
        tok = secrets.token_hex(24)
        with sqlite3.connect(db) as c:
            c.execute("UPDATE info SET shortcut_token=? WHERE guild_id=?", (tok, str(si.guild.id)))
            c.commit()
        v2 = discord.ui.LayoutView()
        v2.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content="## IOS 자충 토큰 재발급"),
            _sep(),
            discord.ui.TextDisplay(content=f"> **새 토큰:** `{tok}`"),
            _sep(),
            discord.ui.TextDisplay(content="-# 기존 토큰은 즉시 무효화됩니다"),
            accent_color=gc,
        ))
        await si.response.edit_message(view=v2)

    btn_reissue.callback = _reissue
    v = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## IOS 자충 토큰"),
        _sep(),
        discord.ui.TextDisplay(content=f"> **토큰:** `{existing}`"),
        _sep(),
        discord.ui.TextDisplay(content="-# 재발급하면 기존 토큰은 무효화됩니다\n-# 본인 외에는 절대 공유하지 마세요"),
        accent_color=gc,
    )
    container.add_item(discord.ui.ActionRow(btn_reissue))
    v.add_item(container)
    await i.response.send_message(view=v, ephemeral=True)

# ══════════════════════════════════════════════════════════════════════
# 슬래시 명령어 (글로벌, guild_only 없음)
# ══════════════════════════════════════════════════════════════════════

@bot.tree.command(name="등록", description="라이센스 키로 서버를 등록합니다")
async def cmd_register(i: discord.Interaction):
    if not i.guild:
        await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
    if _db_by_id(str(i.guild.id)):
        await i.response.send_message(
            view=_layout("## 이미 등록된 서버",
                         "이 서버는 이미 등록되어 있습니다\n`/설정`으로 자판기를 설정하세요",
                         discord.Color.from_str("#373842")), ephemeral=True); return
    await i.response.send_modal(RegisterModal())


@bot.tree.command(name="자판기", description="자판기를 채널에 전송합니다")
async def cmd_vending(i: discord.Interaction):
    if not i.guild:
        await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
    db = _ensure_db_name(str(i.guild.id), i.guild.name)
    with sqlite3.connect(db) as c:
        row = c.execute(
            "SELECT vending_title,vending_description,accent_color,enabled_features "
            "FROM info WHERE guild_id=?", (str(i.guild.id),)).fetchone()
    if not row:
        await i.response.send_message(view=_err("먼저 `/등록` 명령어로 서버를 등록해주세요"), ephemeral=True); return

    title, desc, color_s, features = row
    title   = _clean(title  or "구매하기", 100)
    desc    = _clean(desc   or "아래 버튼을 눌러 이용해주세요", 500)
    gc      = discord.Color.from_str(_hex(color_s or "#373842"))
    enabled = (features or "").split()

    # 상호작용 먼저 응답 (3초 내 필수)
    await i.response.send_message(
        view=_layout("## 자판기 전송", "자판기가 채널에 전송되었습니다", gc), ephemeral=True)

    # 자판기 컨테이너 메시지
    v_container = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"## {title}"),
        _sep(),
        accent_color=gc,
    )
    if desc:
        container.add_item(discord.ui.TextDisplay(content=desc))
        container.add_item(_sep())
    v_container.add_item(container)
    await i.channel.send(view=v_container)

    # 버튼 메시지 (별도 전송 후 메시지 ID 저장)
    vend_view = _make_vending_view(enabled, str(i.guild.id), db)
    sent = await i.channel.send(view=vend_view)

    # 봇 재시작 시 재연결을 위해 메시지 ID DB 저장
    _save_vending_message(str(i.guild.id), str(i.channel.id), str(sent.id), db)
    # 현재 실행 중인 봇에도 View 등록
    bot.add_view(vend_view, message_id=sent.id)


@bot.tree.command(name="설정", description="자판기 설정을 관리합니다")
async def cmd_settings(i: discord.Interaction):
    if not i.guild:
        await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
    db = _ensure_db_name(str(i.guild.id), i.guild.name)
    with sqlite3.connect(db) as c:
        if not c.execute("SELECT 1 FROM info WHERE guild_id=?", (str(i.guild.id),)).fetchone():
            await i.response.send_message(view=_err("먼저 `/등록` 명령어로 서버를 등록해주세요"), ephemeral=True); return
    gc = _color(str(i.guild.id), db)

    sel = discord.ui.Select(placeholder="항목 선택", options=[
        discord.SelectOption(label="자판기 설정",    value="vending"),
        discord.SelectOption(label="계좌 설정",      value="bank"),
        discord.SelectOption(label="충전 설정",      value="charge"),
        discord.SelectOption(label="IOS 자충 토큰", value="token"),
        discord.SelectOption(label="상품 관리",      value="product"),
    ])

    async def _on_sel(si: discord.Interaction):
        val = si.data["values"][0]
        if   val == "vending":  await si.response.send_modal(VendingSettingModal())
        elif val == "bank":     await si.response.send_modal(BankModal())
        elif val == "charge":   await si.response.send_modal(ChargeSettingModal())
        elif val == "token":    await _do_token(si, db, gc)
        elif val == "product":  await _do_product_menu(si, db, gc)

    sel.callback = _on_sel
    v = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 설정하기"),
        _sep(),
        discord.ui.TextDisplay(content="설정할 항목을 선택하세요"),
        _sep(),
        accent_color=gc,
    )
    container.add_item(discord.ui.ActionRow(sel))
    v.add_item(container)
    await i.response.send_message(view=v, ephemeral=True)


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
    keys = []
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(LICENSE_DB) as c:
        for _ in range(수량):
            k = _make_key()
            c.execute("INSERT INTO licenses(key,days,created_at) VALUES(?,?,?)", (k, 기간.value, now))
            keys.append(k)
        c.commit()
    txt = (f"VOUT 라이센스 키 목록\n생성일시: {now}\n기간: {기간.value}일 / 수량: {수량}개\n"
           + "="*50 + "\n\n")
    for idx, k in enumerate(keys, 1):
        txt += f"{idx:>3}. {k}\n"
    fname = f"licenses_{기간.value}일_{수량}개_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    f = discord.File(fp=io.BytesIO(txt.encode()), filename=fname)
    v = discord.ui.LayoutView()
    v.add_item(discord.ui.Container(
        discord.ui.TextDisplay(content="## 라이센스 생성 완료"),
        _sep(),
        discord.ui.TextDisplay(content=f"{수량}개가 생성되었습니다"),
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
        if   fv == "unused": rows = c.execute("SELECT key,days,used,guild_name,created_at FROM licenses WHERE used=0").fetchall()
        elif fv == "used":   rows = c.execute("SELECT key,days,used,guild_name,created_at FROM licenses WHERE used=1").fetchall()
        else:                rows = c.execute("SELECT key,days,used,guild_name,created_at FROM licenses").fetchall()
    fl = {"all":"전체","unused":"미사용","used":"사용됨"}.get(fv,"전체")
    if not rows:
        await i.followup.send(view=_layout(f"## 라이센스 목록 [{fl}]", "조회된 라이센스가 없습니다",
                                           discord.Color.from_str("#373842")), ephemeral=True); return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txt = (f"VOUT 라이센스 목록 [{fl}]\n조회일시: {now} / 총 {len(rows)}개\n"
           + "="*60 + "\n\n")
    for idx, (key, days, used, gname, cat) in enumerate(rows, 1):
        status = f"사용됨({gname})" if used else "미사용"
        txt += f"{idx:>3}. {key}  |  {days}일  |  {status}  |  {cat}\n"
    fname = f"licenses_{fv}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    f = discord.File(fp=io.BytesIO(txt.encode()), filename=fname)
    v = discord.ui.LayoutView()
    v.add_item(discord.ui.Container(
        discord.ui.TextDisplay(content=f"## 라이센스 목록 [{fl}]"),
        _sep(),
        discord.ui.TextDisplay(content=f"총 {len(rows)}개 조회되었습니다"),
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
    await i.response.send_message(view=_layout(
        "## 라이센스 삭제 완료",
        f"> **키:** `{key}`\n> **기간:** {days}일\n"
        f"> **상태:** {'사용됨 (' + gname + ')' if used else '미사용'}",
        discord.Color.from_str("#373842")), ephemeral=True)

# ══════════════════════════════════════════════════════════════════════
# FastAPI
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
    db = _db_by_id(payload.guild_id)
    if not db:
        raise HTTPException(404, "서버를 찾을 수 없습니다")
    with sqlite3.connect(db) as c:
        row = c.execute("SELECT shortcut_token FROM info WHERE guild_id=?", (payload.guild_id,)).fetchone()
    stored = row[0] if row and row[0] else None
    if not stored or not hmac.compare_digest(stored, payload.token):
        raise HTTPException(401, "Unauthorized")
    parsed = _parse_sms(payload.sms_body)
    if not parsed:
        raise HTTPException(400, "카카오뱅크 입금 알림 형식이 아닙니다")
    depositor, amount = parsed
    with sqlite3.connect(db) as c:
        row = c.execute(
            "SELECT charge_id FROM charge_pending "
            "WHERE status='pending' AND depositor=? AND amount=? ORDER BY created_at LIMIT 1",
            (depositor, amount)).fetchone()
    if not row:
        raise HTTPException(404, "일치하는 충전 대기가 없습니다")
    if not await _complete_charge(row[0], depositor, amount, payload.guild_id):
        raise HTTPException(400, "충전 처리 실패")
    return {"status": "ok", "charge_id": row[0], "amount": amount}


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
# 실행
# ══════════════════════════════════════════════════════════════════════

async def main():
    config = uvicorn.Config(api, host=API_HOST, port=API_PORT, log_level="warning")
    server = uvicorn.Server(config)
    await asyncio.gather(bot.start(TOKEN), server.serve())

if __name__ == "__main__":
    asyncio.run(main())
