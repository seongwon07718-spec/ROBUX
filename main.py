import discord
from discord.ext import commands
from discord import app_commands
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, field_validator
import uvicorn, sqlite3, random, string, os, io, re, asyncio, secrets, hashlib, hmac
from datetime import datetime, timedelta

# ══════════════════════════════════════════════════════
# 설정
# ══════════════════════════════════════════════════════
TOKEN          = ""
ADMIN_IDS      = [1454398431996018724]
DB_DIR         = "DB"
LICENSE_DB     = os.path.join(DB_DIR, "라이센스.db")
WEBHOOK_SECRET = "f1356103e6b861cb00d3c502cb27d9f66bd84880f70d3b98186fdbd5cd1d840c"
DOMAIN         = "pay.v0ut.com"
API_HOST       = "0.0.0.0"
API_PORT       = 8000
# ──────────────────────────────────────────────────────

os.makedirs(DB_DIR, exist_ok=True)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
api = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

pending_charges: dict[str, discord.Interaction] = {}
_rate_store:     dict[str, list]                 = {}


# ══════════════════════════════════════════════════════
# 유틸
# ══════════════════════════════════════════════════════

def _safe_name(name: str) -> str:
    return ("".join(c for c in name if c.isalnum() or c in " _-").strip())[:64] or "unknown"

def _db_path(guild_name: str) -> str:
    p = os.path.abspath(os.path.join(DB_DIR, f"{_safe_name(guild_name)}.db"))
    if not p.startswith(os.path.abspath(DB_DIR)):
        raise ValueError("경로 조작 감지")
    return p

def _db_path_by_id(guild_id: str) -> str | None:
    for f in os.listdir(DB_DIR):
        if not f.endswith(".db") or f == "라이센스.db":
            continue
        p = os.path.join(DB_DIR, f)
        try:
            with sqlite3.connect(p) as con:
                if con.execute("SELECT 1 FROM info WHERE guild_id=?", (guild_id,)).fetchone():
                    return p
        except Exception:
            pass
    return None

def _hex(s: str) -> str:
    s = s.strip().lstrip("#")
    return f"#{s}" if re.fullmatch(r"[0-9A-Fa-f]{6}", s) else "#5865F2"

def _clean(s: str, n: int = 500) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", s).strip()[:n]

def _valid_key(k: str) -> bool:
    return bool(re.fullmatch(r"VOUT-[A-Z0-9]{6}-[A-Z0-9]{4}-[A-Z0-9]{4}", k.strip().upper()))

def _is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

def _rate(ip: str, lim=30, win=60) -> bool:
    now = datetime.now().timestamp()
    hits = [t for t in _rate_store.get(ip, []) if now - t < win]
    if len(hits) >= lim:
        return False
    _rate_store[ip] = hits + [now]
    return True

def _hmac_ok(body: bytes, sig: str) -> bool:
    return hmac.compare_digest(hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest(), sig)

def _get_color(guild_id: str, db: str) -> discord.Color:
    try:
        with sqlite3.connect(db) as con:
            row = con.execute("SELECT accent_color FROM info WHERE guild_id=?", (guild_id,)).fetchone()
            if row and row[0]:
                return discord.Color.from_str(_hex(row[0]))
    except Exception:
        pass
    return discord.Color.from_str("#373842")

def _get_token(guild_id: str, db: str) -> str | None:
    try:
        with sqlite3.connect(db) as con:
            row = con.execute("SELECT shortcut_token FROM info WHERE guild_id=?", (guild_id,)).fetchone()
            return row[0] if row and row[0] else None
    except Exception:
        return None


# ══════════════════════════════════════════════════════
# DB 초기화
# ══════════════════════════════════════════════════════

def init_license_db():
    with sqlite3.connect(LICENSE_DB) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS licenses(
            key TEXT PRIMARY KEY, days INTEGER NOT NULL,
            used INTEGER DEFAULT 0, guild_id TEXT, guild_name TEXT,
            created_at TEXT NOT NULL, expires_at TEXT)""")
        con.commit()

def init_guild_db(guild_id: str, guild_name: str) -> str:
    p = _db_path(guild_name)
    with sqlite3.connect(p) as con:
        con.execute("CREATE TABLE IF NOT EXISTS info(guild_id TEXT PRIMARY KEY, guild_name TEXT)")
        for col, typ in [
            ("license_key","TEXT"), ("registered_at","TEXT"), ("expires_at","TEXT"),
            ("vending_title","TEXT DEFAULT '구매하기'"),
            ("vending_description","TEXT DEFAULT '아래 버튼을 눌러 이용해주세요'"),
            ("accent_color","TEXT DEFAULT '#5865F2'"),
            ("enabled_features","TEXT DEFAULT '제품 구매 충전 정보'"),
            ("bank_name","TEXT DEFAULT ''"), ("account_number","TEXT DEFAULT ''"),
            ("account_holder","TEXT DEFAULT ''"),
            ("min_charge","INTEGER DEFAULT 1000"), ("charge_unit","INTEGER DEFAULT 1000"),
            ("shortcut_token","TEXT"),
        ]:
            try:
                con.execute(f"ALTER TABLE info ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError:
                pass
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            user_id TEXT PRIMARY KEY, username TEXT, points INTEGER DEFAULT 0, created_at TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS charge_pending(
            charge_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, username TEXT,
            depositor TEXT NOT NULL, amount INTEGER NOT NULL,
            status TEXT DEFAULT 'pending', created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
            completed_at TEXT, channel_id TEXT, message_id TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS charge_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT, charge_id TEXT, user_id TEXT,
            username TEXT, depositor TEXT, amount INTEGER, status TEXT,
            created_at TEXT, completed_at TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            price INTEGER NOT NULL, stock INTEGER NOT NULL,
            content TEXT NOT NULL, created_at TEXT NOT NULL)""")
        con.commit()
    return p


# ══════════════════════════════════════════════════════
# 라이센스 키
# ══════════════════════════════════════════════════════

def _new_key() -> str:
    def r(n): return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))
    return f"VOUT-{r(6)}-{r(4)}-{r(4)}"

def _key_exists(k: str) -> bool:
    with sqlite3.connect(LICENSE_DB) as con:
        return con.execute("SELECT 1 FROM licenses WHERE key=?", (k,)).fetchone() is not None

def _make_key() -> str:
    for _ in range(1000):
        k = _new_key()
        if not _key_exists(k):
            return k
    raise RuntimeError("키 생성 실패")


# ══════════════════════════════════════════════════════
# SMS 파싱
# ══════════════════════════════════════════════════════

def _parse_sms(sms: str) -> tuple[str, int] | None:
    if "[카카오뱅크]" not in sms:
        return None
    lines = [l.strip() for l in sms.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        m = re.search(r"입금\s+([\d,]+)원", line)
        if m:
            try:
                amt = int(m.group(1).replace(",", ""))
            except ValueError:
                return None
            if i + 1 < len(lines):
                dep = lines[i + 1]
                if not re.search(r"잔액", dep) and re.fullmatch(r"[가-힣a-zA-Z0-9]{1,20}", dep):
                    if 0 < amt <= 10_000_000:
                        return dep, amt
    return None


# ══════════════════════════════════════════════════════
# Components V2 ─ SimpleLayout (색상 파라미터)
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

def err(msg: str, guild_color: discord.Color | None = None) -> SimpleLayout:
    return SimpleLayout("## 오류", f"-# {msg}", guild_color or discord.Color.red())


# ══════════════════════════════════════════════════════
# 등록 확인 Layout
# ══════════════════════════════════════════════════════

class RegisterConfirmLayout(discord.ui.LayoutView):
    def __init__(self, key: str, days: int, expires: str, guild_name: str):
        super().__init__(timeout=None)
        self.license_key = key
        self.days = days
        self.expires = expires
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
            accent_color=discord.Color.from_str("#373842"),
        )
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        btn_ok  = discord.ui.Button(label="진행", style=discord.ButtonStyle.secondary)
        btn_ok.callback = self._confirm
        btn_no  = discord.ui.Button(label="취소", style=discord.ButtonStyle.secondary)
        btn_no.callback = self._cancel
        container.add_item(discord.ui.ActionRow(btn_ok, btn_no))
        self.add_item(container)

    async def _confirm(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("서버에서만 사용 가능합니다", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            with sqlite3.connect(LICENSE_DB) as con:
                row = con.execute("SELECT used FROM licenses WHERE key=?", (self.license_key,)).fetchone()
                if not row or row[0]:
                    await interaction.edit_original_response(view=err("이미 사용된 라이센스입니다"))
                    return
                now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                guild = interaction.guild
                con.execute(
                    "UPDATE licenses SET used=1,guild_id=?,guild_name=?,expires_at=? WHERE key=? AND used=0",
                    (str(guild.id), guild.name[:100], self.expires, self.license_key))
                if con.execute("SELECT changes()").fetchone()[0] == 0:
                    await interaction.edit_original_response(view=err("이미 사용된 라이센스입니다"))
                    return
                con.commit()

            # ← 진행 버튼 눌렀을 때 서버.db 생성
            db = init_guild_db(str(guild.id), guild.name)
            with sqlite3.connect(db) as con:
                con.execute(
                    "INSERT OR REPLACE INTO info(guild_id,guild_name,license_key,registered_at,expires_at) VALUES(?,?,?,?,?)",
                    (str(guild.id), guild.name[:100], self.license_key, now, self.expires))
                con.commit()

            await interaction.edit_original_response(view=SimpleLayout(
                "## 서버 등록 완료",
                f"> **서버:** {guild.name}\n> **기간:** {self.days}일\n> **만료일:** {self.expires}\n\n`/설정`으로 자판기를 설정하세요",
                discord.Color.green()))
        except Exception as e:
            print(f"[등록 오류] {e}")
            await interaction.edit_original_response(view=err("처리 중 문제가 발생했습니다"))

    async def _cancel(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.edit_original_response(view=SimpleLayout(
            "## 등록 취소", "서버 등록이 취소되었습니다", discord.Color.from_str("#99AAB5")))


# ══════════════════════════════════════════════════════
# Modal ─ 자판기 설정
# ══════════════════════════════════════════════════════

class VendingModal(discord.ui.Modal, title="자판기 설정"):
    t = discord.ui.TextInput(label="자판기 제목",    placeholder="구매하기",  required=True,  max_length=100)
    d = discord.ui.TextInput(label="자판기 설명",    style=discord.TextStyle.long, required=False, max_length=500)
    c = discord.ui.TextInput(label="색상",    placeholder="#373842",   required=True,  max_length=7)

    async def on_submit(self, i: discord.Interaction):
        if not i.guild:
            await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
        title = _clean(self.t.value, 100)
        desc  = _clean(self.d.value or "", 500)
        color = _hex(self.c.value)
        if not title:
            await i.response.send_message(view=err("제목을 입력해주세요"), ephemeral=True); return
        try:
            db = _db_path(i.guild.name)
            with sqlite3.connect(db) as con:
                con.execute("UPDATE info SET vending_title=?,vending_description=?,accent_color=? WHERE guild_id=?",
                            (title, desc, color, str(i.guild.id)))
                if con.execute("SELECT changes()").fetchone()[0] == 0:
                    await i.response.send_message(view=err("/등록 먼저 진행해주세요"), ephemeral=True); return
                con.commit()
            gc = discord.Color.from_str(color)
            await i.response.send_message(view=SimpleLayout(
                "## 설정 저장 완료", 
                f"> **제목:** {title}\n> **설명:** {desc or '없음'}\n> **색상:** `{color}`",
                gc), ephemeral=True)
        except Exception as e:
            print(f"[자판기 설정 오류] {e}")
            await i.response.send_message(view=err("저장 중 문제가 발생했습니다"), ephemeral=True)


# ══════════════════════════════════════════════════════
# Modal ─ 계좌 설정
# ══════════════════════════════════════════════════════

class BankModal(discord.ui.Modal, title="계좌 설정"):
    bn = discord.ui.TextInput(label="은행명",     placeholder="예) 카카오뱅크", required=True, max_length=20)
    ac = discord.ui.TextInput(label="계좌번호",   placeholder="예) 10-123-456789", required=True, max_length=30)
    ah = discord.ui.TextInput(label="예금주",     placeholder="예) 홍길동", required=True, max_length=20)

    async def on_submit(self, i: discord.Interaction):
        if not i.guild:
            await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
        bank   = _clean(self.bn.value, 20)
        number = _clean(self.ac.value, 30)
        holder = _clean(self.ah.value, 20)
        if not re.fullmatch(r"[\d\-]+", number):
            await i.response.send_message(view=err("계좌번호는 숫자와 - 만 입력 가능합니다"), ephemeral=True); return
        try:
            db = _db_path(i.guild.name)
            gc = _get_color(str(i.guild.id), db)
            with sqlite3.connect(db) as con:
                con.execute("UPDATE info SET bank_name=?,account_number=?,account_holder=? WHERE guild_id=?",
                            (bank, number, holder, str(i.guild.id)))
                con.commit()
            await i.response.send_message(view=SimpleLayout(
                "## 계좌 설정 완료",
                f"> **은행명:** {bank}\n> **계좌번호:** `{number}`\n> **예금주:** {holder}",
                gc), ephemeral=True)
        except Exception as e:
            print(f"[계좌 설정 오류] {e}")
            await i.response.send_message(view=err("저장 중 문제가 발생했습니다"), ephemeral=True)


# ══════════════════════════════════════════════════════
# Modal ─ 충전 설정
# ══════════════════════════════════════════════════════

class ChargeSettingModal(discord.ui.Modal, title="충전 설정"):
    mi = discord.ui.TextInput(label="최소 충전금액 (원)", placeholder="예) 1000", required=True, max_length=10)
    un = discord.ui.TextInput(label="충전 단위 (원)",     placeholder="예) 1000", required=True, max_length=10)

    async def on_submit(self, i: discord.Interaction):
        if not i.guild:
            await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
        try:
            mn = int(re.sub(r"[^0-9]", "", self.mi.value))
            un = int(re.sub(r"[^0-9]", "", self.un.value))
        except ValueError:
            await i.response.send_message(view=err("숫자만 입력 가능합니다"), ephemeral=True); return
        if not (100 <= mn <= 1_000_000):
            await i.response.send_message(view=err("최소 충전금액: 100원 ~ 1,000,000원"), ephemeral=True); return
        if not (100 <= un <= 100_000):
            await i.response.send_message(view=err("충전 단위: 100원 ~ 100,000원"), ephemeral=True); return
        try:
            db = _db_path(i.guild.name)
            gc = _get_color(str(i.guild.id), db)
            with sqlite3.connect(db) as con:
                con.execute("UPDATE info SET min_charge=?,charge_unit=? WHERE guild_id=?",
                            (mn, un, str(i.guild.id)))
                con.commit()
            await i.response.send_message(view=SimpleLayout(
                "## 충전 설정 완료",
                f"> **최소 충전금액:** {mn:,}원\n> **충전 단위:** {un:,}원",
                gc), ephemeral=True)
        except Exception as e:
            print(f"[충전 설정 오류] {e}")
            await i.response.send_message(view=err("저장 중 문제가 발생했습니다"), ephemeral=True)


# ══════════════════════════════════════════════════════
# Modal ─ 계좌이체 충전
# ══════════════════════════════════════════════════════

class TransferModal(discord.ui.Modal, title="계좌이체 충전"):
    dep = discord.ui.TextInput(label="입금자명",        placeholder="예) 홍길동", required=True, max_length=20)
    amt = discord.ui.TextInput(label="충전 금액 (원)",  placeholder="예) 10000",              required=True, max_length=10)

    def __init__(self, guild_id: str, guild_name: str):
        super().__init__()
        self.gid  = guild_id
        self.gname = guild_name

    async def on_submit(self, i: discord.Interaction):
        if not i.guild or str(i.guild.id) != self.gid:
            await i.response.send_message("잘못된 접근입니다", ephemeral=True); return
        depositor = _clean(self.dep.value, 20)
        if not re.fullmatch(r"[가-힣a-zA-Z0-9]{1,20}", depositor):
            await i.response.send_message(view=err("입금자명은 한글/영문/숫자만 입력 가능합니다"), ephemeral=True); return
        try:
            amount = int(re.sub(r"[^0-9]", "", self.amt.value))
        except ValueError:
            await i.response.send_message(view=err("금액은 숫자만 입력 가능합니다"), ephemeral=True); return

        try:
            db = _db_path(self.gname)
            gc = _get_color(self.gid, db)
            with sqlite3.connect(db) as con:
                row = con.execute(
                    "SELECT bank_name,account_number,account_holder,min_charge,charge_unit FROM info WHERE guild_id=?",
                    (self.gid,)).fetchone()
        except Exception as e:
            print(f"[충전 Modal DB 오류] {e}")
            await i.response.send_message(view=err("서버 정보를 불러올 수 없습니다"), ephemeral=True); return

        if not row:
            await i.response.send_message(view=err("등록된 서버가 아닙니다"), ephemeral=True); return

        bank, acnum, holder, min_c, unit = row
        min_c = min_c or 1000
        unit  = unit  or 1000

        if not bank or not acnum:
            await i.response.send_message(view=err("계좌 정보가 설정되지 않았습니다\n-# 관리자에게 문의하세요"), ephemeral=True); return
        if amount < min_c:
            await i.response.send_message(view=err(f"최소 충전금액은 {min_c:,}원입니다"), ephemeral=True); return
        if amount % unit != 0:
            await i.response.send_message(view=err(f"충전 단위는 {unit:,}원입니다"), ephemeral=True); return
        if amount > 10_000_000:
            await i.response.send_message(view=err("1회 최대 충전금액은 10,000,000원입니다"), ephemeral=True); return

        with sqlite3.connect(db) as con:
            if con.execute("SELECT charge_id FROM charge_pending WHERE user_id=? AND status='pending'",
                           (str(i.user.id),)).fetchone():
                await i.response.send_message(view=err("-# 진행 중인 충전 요청이 있습니다\n-# 5분 후에 다시 신청해주세요"), ephemeral=True); return

        now     = datetime.now()
        expires = now + timedelta(minutes=5)
        cid     = secrets.token_hex(16)

        with sqlite3.connect(db) as con:
            con.execute("""INSERT INTO charge_pending
                (charge_id,user_id,username,depositor,amount,status,created_at,expires_at)
                VALUES(?,?,?,?,?,'pending',?,?)""",
                (cid, str(i.user.id), str(i.user), depositor, amount,
                 now.strftime("%Y-%m-%d %H:%M:%S"), expires.strftime("%Y-%m-%d %H:%M:%S")))
            con.commit()

        view = discord.ui.LayoutView()
        view.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content="## 계좌 안내"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=(
                f"> **은행명:** {bank}\n"
                f"> **계좌번호:** `{acnum}`\n"
                f"> **예금주:** {holder}\n\n"
                f"> **입금금액:** {amount:,}원\n"
                f"> **입금자명:** {depositor}\n"
                f"> **만료시각:** {expires.strftime('%H:%M:%S')} (5분)"
            )),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=(
                "-# 입금자명을 정확히 입력 후 이체해주세요\n"
                "-# 5분 내 입금이 확인되지 않으면 취소됩니다"
            )),
            accent_color=gc,
        ))
        await i.response.send_message(view=view, ephemeral=True)
        msg = await i.original_response()

        with sqlite3.connect(db) as con:
            con.execute("UPDATE charge_pending SET channel_id=?,message_id=? WHERE charge_id=?",
                        (str(i.channel_id), str(msg.id), cid))
            con.commit()

        pending_charges[cid] = i
        asyncio.create_task(_charge_timeout(cid, db, i, gc))


# ══════════════════════════════════════════════════════
# 충전 타이머
# ══════════════════════════════════════════════════════

async def _charge_timeout(cid: str, db: str, i: discord.Interaction, gc: discord.Color):
    await asyncio.sleep(300)
    try:
        with sqlite3.connect(db) as con:
            row = con.execute("SELECT status FROM charge_pending WHERE charge_id=?", (cid,)).fetchone()
            if not row or row[0] != "pending":
                return
            con.execute("UPDATE charge_pending SET status='expired' WHERE charge_id=? AND status='pending'", (cid,))
            con.commit()
        view = discord.ui.LayoutView()
        view.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content="## 충전 취소"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="-# 입금이 확인되지 않아 충전이 취소되었습니다\n-# 다시 충전하려면 충전 버튼을 눌러주세요"),
            accent_color=discord.Color.red(),
        ))
        await i.edit_original_response(view=view)
    except Exception as e:
        print(f"[충전 타이머 오류] {e}")
    finally:
        pending_charges.pop(cid, None)


# ══════════════════════════════════════════════════════
# 충전 완료 처리 (FastAPI → 봇)
# ══════════════════════════════════════════════════════

async def _complete_charge(cid: str, depositor: str, amount: int, guild_id: str, sig: str, raw: bytes) -> bool:
    if not _hmac_ok(raw, sig):
        print(f"[웹훅 보안] HMAC 실패 cid={cid}")
        return False

    db = _db_path_by_id(guild_id)
    if not db:
        return False

    gc = _get_color(guild_id, db)

    with sqlite3.connect(db) as con:
        row = con.execute(
            "SELECT user_id,username,depositor,amount,status FROM charge_pending WHERE charge_id=?",
            (cid,)).fetchone()
        if not row:
            return False
        uid, uname, exp_dep, exp_amt, status = row
        if status != "pending":
            return False
        if depositor.strip() != exp_dep.strip() or amount != exp_amt:
            print(f"[웹훅 보안] 불일치 dep={depositor}/{exp_dep} amt={amount}/{exp_amt}")
            return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        con.execute("UPDATE charge_pending SET status='completed',completed_at=? WHERE charge_id=? AND status='pending'",
                    (now, cid))
        if con.execute("SELECT changes()").fetchone()[0] == 0:
            return False
        con.execute("""INSERT INTO users(user_id,username,points,created_at) VALUES(?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET points=points+?,username=excluded.username""",
            (uid, uname, amount, now, amount))
        con.execute("""INSERT INTO charge_history(charge_id,user_id,username,depositor,amount,status,created_at,completed_at)
            VALUES(?,?,?,?,?,'completed',?,?)""",
            (cid, uid, uname, depositor, amount, now, now))
        new_pts = con.execute("SELECT points FROM users WHERE user_id=?", (uid,)).fetchone()[0]
        con.commit()

    orig_i = pending_charges.get(cid)
    if orig_i:
        try:
            view = discord.ui.LayoutView()
            view.add_item(discord.ui.Container(
                discord.ui.TextDisplay(content="## 충전 완료"),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(content=(
                    f"> **충전 금액:** {amount:,}원\n"
                    f"> **보유 잔액:** {new_pts:,}원"
                )),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(content=(
                    f"-# 처리시각: {now}"
                )),
                accent_color=gc,
            ))
            await orig_i.edit_original_response(view=view)
        except Exception as e:
            print(f"[충전 완료 메시지 오류] {e}")
        finally:
            pending_charges.pop(cid, None)
    return True


# ══════════════════════════════════════════════════════
# 단축어 토큰 발급
# ══════════════════════════════════════════════════════

async def _issue_token(i: discord.Interaction):
    if not i.guild:
        await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
    try:
        db = _db_path(i.guild.name)
        gc = _get_color(str(i.guild.id), db)
    except ValueError:
        await i.response.send_message(view=err("비정상적인 접근입니다"), ephemeral=True); return

    with sqlite3.connect(db) as con:
        row = con.execute("SELECT shortcut_token FROM info WHERE guild_id=?", (str(i.guild.id),)).fetchone()
    if not row:
        await i.response.send_message(view=err("등록된 서버가 아닙니다"), ephemeral=True); return

    existing = row[0]
    if existing:
        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## IOS 자충 토큰"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=(
                f"> **토큰:** `{existing}`"
            )),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=(
                "-# 이미 발급된 토큰이 있습니다\n"
                "-# 재발급하면 기존 토큰은 무효화됩니다\n"
                "-# 본인 외에는 절대 공유하지 마세요"
            )),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            accent_color=gc,
        )
        btn = discord.ui.Button(label="재발급", style=discord.ButtonStyle.danger,
                                custom_id=f"token_reissue_{i.guild.id}")
        container.add_item(discord.ui.ActionRow(btn))
        view.add_item(container)
        await i.response.send_message(view=view, ephemeral=True)
    else:
        tok = secrets.token_hex(24)
        with sqlite3.connect(db) as con:
            con.execute("UPDATE info SET shortcut_token=? WHERE guild_id=?", (tok, str(i.guild.id)))
            con.commit()
        view = discord.ui.LayoutView()
        view.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content="## IOS 자충 토큰"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=f"> **토큰:** `{tok}`"),
            accent_color=gc,
        ))
        await i.response.send_message(view=view, ephemeral=True)


# ══════════════════════════════════════════════════════
# /자판기 명령어
# ══════════════════════════════════════════════════════

@bot.tree.command(name="자판기", description="자판기를 전송합니다")
async def cmd_vending(i: discord.Interaction):
    if not i.guild:
        await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
    try:
        db = _db_path(i.guild.name)
    except ValueError:
        await i.response.send_message(view=err("비정상적인 접근입니다"), ephemeral=True); return

    with sqlite3.connect(db) as con:
        row = con.execute(
            "SELECT vending_title,vending_description,accent_color,enabled_features FROM info WHERE guild_id=?",
            (str(i.guild.id),)).fetchone()
    if not row:
        await i.response.send_message(view=err("먼저 /등록 명령어로 서버를 등록해주세요"), ephemeral=True); return

    title, desc, color_s, features = row
    title    = _clean(title  or "구매하기", 100)
    desc     = _clean(desc   or "아래 버튼을 눌러 이용해주세요", 500)
    color_s  = _hex(color_s  or "#373842")
    gc       = discord.Color.from_str(color_s)
    enabled  = features.split() if features else []

    # 자판기 전송 안내
    await i.response.send_message(
        view=SimpleLayout("## 자판기 전송", "자판기가 채널에 전송되었습니다", gc),
        ephemeral=True)

    # 공개 자판기
    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"## {title}"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        accent_color=gc,
    )
    if desc:
        container.add_item(discord.ui.TextDisplay(content=desc))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

    btns = []
    if "구매" in enabled:
        btns.append(discord.ui.Button(label="구매", style=discord.ButtonStyle.secondary, custom_id="vend_buy", emoji="<:emoji_48:1498298170281558058>"))
    if "제품" in enabled:
        btns.append(discord.ui.Button(label="제품", style=discord.ButtonStyle.secondary, custom_id="vend_products", emoji="<:emoji_46:1498296760483709029>"))
    if "충전" in enabled:
        btns.append(discord.ui.Button(label="충전", style=discord.ButtonStyle.secondary, custom_id="vend_charge", emoji="<:emoji_46:1498297238630305903>"))
    if "정보" in enabled:
        btns.append(discord.ui.Button(label="정보", style=discord.ButtonStyle.secondary, custom_id="vend_info", emoji="<:emoji_47:1498298137406738483>"))
    if btns:
        container.add_item(discord.ui.ActionRow(*btns))
    view.add_item(container)
    await i.channel.send(view=view)


# ══════════════════════════════════════════════════════
# /설정 명령어
# ══════════════════════════════════════════════════════

@bot.tree.command(name="설정", description="자판기 설정을 관리합니다")
async def cmd_settings(i: discord.Interaction):
    if not i.guild:
        await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
    try:
        db = _db_path(i.guild.name)
    except ValueError:
        await i.response.send_message(view=err("비정상적인 접근입니다"), ephemeral=True); return

    with sqlite3.connect(db) as con:
        if not con.execute("SELECT 1 FROM info WHERE guild_id=?", (str(i.guild.id),)).fetchone():
            await i.response.send_message(view=err("먼저 /등록 명령어로 서버를 등록해주세요"), ephemeral=True); return

    gc = _get_color(str(i.guild.id), db)
    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 설정하기"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="아래 드롭바를 눌러 설정할 항목을 선택하세요"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        accent_color=gc,
    )
    sel = discord.ui.Select(placeholder="설정할 항목 선택해주세요", options=[
        discord.SelectOption(label="자판기 설정",    value="vending"),
        discord.SelectOption(label="계좌 설정",      value="bank"),
        discord.SelectOption(label="충전 설정",      value="charge"),
        discord.SelectOption(label="IOS 자충 토큰", value="token"),
    ])
    async def _sel(si: discord.Interaction):
        if si.guild_id != i.guild_id:
            await si.response.send_message("권한이 없습니다", ephemeral=True); return
        v = si.data["values"][0]
        if v == "vending":  await si.response.send_modal(VendingModal())
        elif v == "bank":   await si.response.send_modal(BankModal())
        elif v == "charge": await si.response.send_modal(ChargeSettingModal())
        elif v == "token":  await _issue_token(si)
    sel.callback = _sel
    container.add_item(discord.ui.ActionRow(sel))
    view.add_item(container)
    await i.response.send_message(view=view, ephemeral=True)


# ══════════════════════════════════════════════════════
# 버튼 인터랙션
# ══════════════════════════════════════════════════════

@bot.event
async def on_interaction(i: discord.Interaction):
    if i.type != discord.InteractionType.component or not i.guild:
        return
    cid = i.data.get("custom_id", "")

    try:
        db = _db_path(i.guild.name)
        gc = _get_color(str(i.guild.id), db)
    except ValueError:
        await i.response.send_message(view=err("비정상적인 접근입니다"), ephemeral=True); return

    if cid == "vend_charge":
        with sqlite3.connect(db) as con:
            row = con.execute("SELECT bank_name,account_number FROM info WHERE guild_id=?",
                              (str(i.guild.id),)).fetchone()
        if not row or not row[0] or not row[1]:
            await i.response.send_message(view=err("-# 계좌 정보가 설정되지 않았습니다\n-# 관리자에게 문의하세요"), ephemeral=True); return

        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## 결제수단"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="아래 버튼을 눌러 충전 방법을 선택하세요"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            accent_color=gc,
        )
        btn = discord.ui.Button(label="계좌이체 (account)", style=discord.ButtonStyle.secondary, custom_id="vend_transfer")
        container.add_item(discord.ui.ActionRow(btn))
        view.add_item(container)
        await i.response.send_message(view=view, ephemeral=True)

    elif cid == "vend_transfer":
        await i.response.send_modal(TransferModal(str(i.guild.id), i.guild.name))

    elif cid.startswith("token_reissue_"):
        rgid = cid.replace("token_reissue_", "")
        if str(i.guild.id) != rgid:
            await i.response.send_message("권한이 없습니다", ephemeral=True); return
        tok = secrets.token_hex(24)
        with sqlite3.connect(db) as con:
            con.execute("UPDATE info SET shortcut_token=? WHERE guild_id=?", (tok, str(i.guild.id)))
            con.commit()
        view = discord.ui.LayoutView()
        view.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content="## IOS 자충 토큰 재발급"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=f"> **새 토큰:** `{tok}`"),
            accent_color=gc,
        ))
        await i.response.edit_message(view=view)


# ══════════════════════════════════════════════════════
# 라이센스 명령어 (관리자)
# ══════════════════════════════════════════════════════

@bot.tree.command(name="라이센스_생성", description="라이센스 키를 생성합니다")
@app_commands.describe(기간="기간 선택", 수량="수량 (최대 100)")
@app_commands.choices(기간=[
    app_commands.Choice(name="7일",  value=7),
    app_commands.Choice(name="30일", value=30),
    app_commands.Choice(name="60일", value=60),
    app_commands.Choice(name="90일", value=90),
])
async def cmd_create_license(i: discord.Interaction, 기간: app_commands.Choice[int], 수량: int):
    if not _is_admin(i.user.id):
        await i.response.send_message(view=err("봇 관리자만 사용 가능합니다"), ephemeral=True); return
    if not 1 <= 수량 <= 100:
        await i.response.send_message(view=err("1~100개 사이로 입력해주세요"), ephemeral=True); return
    await i.response.defer(ephemeral=True)
    try:
        keys = []
        now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(LICENSE_DB) as con:
            for _ in range(수량):
                k = _make_key()
                con.execute("INSERT INTO licenses(key,days,created_at) VALUES(?,?,?)", (k, 기간.value, now))
                keys.append(k)
            con.commit()
    except Exception as e:
        print(f"[라이센스 생성 오류] {e}")
        await i.followup.send(view=err("생성 중 문제가 발생했습니다"), ephemeral=True); return

    txt = f"VOUT 라이센스 키 목록\n생성일시: {now}\n기간: {기간.value}일 / 수량: {수량}개\n" + "="*50 + "\n\n"
    for idx, k in enumerate(keys, 1):
        txt += f"{idx:>3}. {k}\n"
    fname = f"licenses_{기간.value}일_{수량}개_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    f = discord.File(fp=io.BytesIO(txt.encode()), filename=fname)
    view = discord.ui.LayoutView()
    view.add_item(discord.ui.Container(
        discord.ui.TextDisplay(content="## 라이센스 생성 완료"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"{수량}개가 데이터베이스에 저장되었습니다"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.File(f"attachment://{fname}"),
        accent_color=0x373842,
    ))
    await i.followup.send(view=view, file=f, ephemeral=True)


@bot.tree.command(name="라이센스_목록", description="라이센스 키 목록을 조회합니다")
@app_commands.choices(필터=[
    app_commands.Choice(name="전체",   value="all"),
    app_commands.Choice(name="미사용", value="unused"),
    app_commands.Choice(name="사용됨", value="used"),
])
async def cmd_list_license(i: discord.Interaction, 필터: app_commands.Choice[str] = None):
    if not _is_admin(i.user.id):
        await i.response.send_message(view=err("봇 관리자만 사용 가능합니다"), ephemeral=True); return
    await i.response.defer(ephemeral=True)
    fv = 필터.value if 필터 else "all"
    with sqlite3.connect(LICENSE_DB) as con:
        if fv == "unused": rows = con.execute("SELECT key,days,used,guild_name,created_at FROM licenses WHERE used=0").fetchall()
        elif fv == "used": rows = con.execute("SELECT key,days,used,guild_name,created_at FROM licenses WHERE used=1").fetchall()
        else:              rows = con.execute("SELECT key,days,used,guild_name,created_at FROM licenses").fetchall()
    fl = {"all":"전체","unused":"미사용","used":"사용됨"}.get(fv,"전체")
    if not rows:
        await i.followup.send(view=SimpleLayout(f"## 라이센스 목록 [{fl}]","조회된 라이센스가 없습니다",discord.Color.from_str("#5865F2")), ephemeral=True); return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txt = f"VOUT 라이센스 목록 [{fl}]\n조회일시: {now} / 총 {len(rows)}개\n" + "="*60 + "\n\n"
    for idx,(key,days,used,gname,cat) in enumerate(rows,1):
        st = f"사용됨({gname})" if used else "미사용"
        txt += f"{idx:>3}. {key}  |  {days}일  |  {st}  |  {cat}\n"
    fname = f"licenses_{fv}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    f = discord.File(fp=io.BytesIO(txt.encode()), filename=fname)
    view = discord.ui.LayoutView()
    view.add_item(discord.ui.Container(
        discord.ui.TextDisplay(content=f"## 라이센스 목록 [{fl}]"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"총 {len(rows)}개의 라이센스가 조회되었습니다"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.File(f"attachment://{fname}"),
        accent_color=discord.Color.from_str("#373842"),
    ))
    await i.followup.send(view=view, file=f, ephemeral=True)


@bot.tree.command(name="라이센스_삭제", description="라이센스 키를 삭제합니다")
@app_commands.describe(키="삭제할 키")
async def cmd_del_license(i: discord.Interaction, 키: str):
    if not _is_admin(i.user.id):
        await i.response.send_message(view=err("봇 관리자만 사용 가능합니다"), ephemeral=True); return
    if not _valid_key(키):
        await i.response.send_message(view=err("올바른 라이센스 키 형식이 아닙니다"), ephemeral=True); return
    with sqlite3.connect(LICENSE_DB) as con:
        row = con.execute("SELECT key,days,used,guild_name FROM licenses WHERE key=?", (키.strip().upper(),)).fetchone()
        if not row:
            await i.response.send_message(view=err("키를 찾을 수 없습니다"), ephemeral=True); return
        key, days, used, gname = row
        con.execute("DELETE FROM licenses WHERE key=?", (key,))
        con.commit()
    st = f"사용됨 (서버: {gname})" if used else "미사용"
    await i.response.send_message(view=SimpleLayout(
        "## 라이센스 삭제 완료",
        f"> **키:** `{key}`\n> **기간:** {days}일\n> **상태:** {st}",
        discord.Color.from_str("#373842")), ephemeral=True)


@bot.tree.command(name="등록", description="서버를 등록합니다")
@app_commands.describe(라이센스="발급받은 라이센스 키")
async def cmd_register(i: discord.Interaction, 라이센스: str):
    if not i.guild:
        await i.response.send_message("서버에서만 사용 가능합니다", ephemeral=True); return
    key_in = 라이센스.strip().upper()
    if not _valid_key(key_in):
        await i.response.send_message(view=err("올바른 라이센스 키 형식이 아닙니다"), ephemeral=True); return
    with sqlite3.connect(LICENSE_DB) as con:
        row = con.execute("SELECT key,days,used FROM licenses WHERE key=?", (key_in,)).fetchone()
    if not row:
        await i.response.send_message(view=err("라이센스 키를 찾을 수 없습니다"), ephemeral=True); return
    key, days, used = row
    if used:
        await i.response.send_message(view=err("이미 다른 서버에서 사용된 키입니다"), ephemeral=True); return
    expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    await i.response.send_message(
        view=RegisterConfirmLayout(key=key, days=days, expires=expires, guild_name=i.guild.name),
        ephemeral=True)


# ══════════════════════════════════════════════════════
# FastAPI ─ SMS 웹훅
# ══════════════════════════════════════════════════════

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
    print(f"[웹훅] IP={req.client.host} guild={payload.guild_id} tok_len={len(payload.token)}")

    db = _db_path_by_id(payload.guild_id)
    if not db:
        raise HTTPException(404, "서버를 찾을 수 없습니다")

    stored = _get_token(payload.guild_id, db)
    if not stored:
        raise HTTPException(401, "단축어 토큰이 발급되지 않았습니다")
    if not hmac.compare_digest(stored, payload.token):
        raise HTTPException(401, "Unauthorized")

    parsed = _parse_sms(payload.sms_body)
    if not parsed:
        raise HTTPException(400, "카카오뱅크 입금 알림 형식이 아닙니다")
    depositor, amount = parsed

    with sqlite3.connect(db) as con:
        row = con.execute(
            "SELECT charge_id FROM charge_pending WHERE status='pending' AND depositor=? AND amount=? ORDER BY created_at LIMIT 1",
            (depositor, amount)).fetchone()
    if not row:
        raise HTTPException(404, "일치하는 충전 대기가 없습니다")

    cid  = row[0]
    body = f"{cid}:{depositor}:{amount}:{payload.guild_id}".encode()
    sig  = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()

    ok = await _complete_charge(cid, depositor, amount, payload.guild_id, sig, body)
    if not ok:
        raise HTTPException(400, "충전 처리 실패")
    return {"status": "ok", "charge_id": cid, "amount": amount}


@api.get("/shortcut/guide")
async def shortcut_guide(token: str, guild_id: str, req: Request):
    if not _rate(req.client.host, lim=10):
        raise HTTPException(429, "Too Many Requests")
    if not re.fullmatch(r"\d{17,20}", guild_id):
        raise HTTPException(400, "잘못된 guild_id")
    db = _db_path_by_id(guild_id)
    if not db:
        raise HTTPException(404, "서버를 찾을 수 없습니다")
    stored = _get_token(guild_id, db)
    if not stored or not hmac.compare_digest(stored, token):
        raise HTTPException(401, "Unauthorized")
    return {
        "steps": [
            "1. iPhone 단축어 앱 > 자동화 > 새 자동화",
            "2. 메시지 수신 > 보낸 사람: 카카오뱅크",
            "3. 동작 추가: URL 가져오기",
            f"4. URL: https://{DOMAIN}/webhook/sms",
            "5. 방법: POST  /  Content-Type: application/json",
            f'6. 본문: {{"token":"{token}","guild_id":"{guild_id}","sms_body":"[수신된 메시지 내용]"}}',
        ]
    }


@api.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


# ══════════════════════════════════════════════════════
# 봇 이벤트 + 통합 실행
# ══════════════════════════════════════════════════════

@bot.event
async def on_ready():
    init_license_db()
    bot.add_view(RegisterConfirmLayout("", 0, "", ""))
    await bot.tree.sync()
    print(f"{bot.user} 온라인")


async def main():
    config = uvicorn.Config(api, host=API_HOST, port=API_PORT, log_level="info")
    server = uvicorn.Server(config)
    await asyncio.gather(
        bot.start(TOKEN),
        server.serve(),
    )

if __name__ == "__main__":
    asyncio.run(main())
