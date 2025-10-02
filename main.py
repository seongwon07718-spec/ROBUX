import os, json, time, re, statistics, threading, hashlib, asyncio
import discord
from discord import app_commands
from discord.ext import commands
from fastapi import FastAPI, Request
import uvicorn

# ===== 기본/환경 =====
GUILD_ID = int(os.getenv("GUILD_ID", "1419200424636055592"))
GUILD = discord.Object(id=GUILD_ID)

GRAY = discord.Color.from_str("#808080")
RED = discord.Color.red()
GREEN = discord.Color.green()
ORANGE = discord.Color.orange()

# 이모지(raw 문자열 저장, 표시시 PartialEmoji로 파싱)
EMOJI_NOTICE = "<:Announcement:1422906665249800274>"
EMOJI_CHARGE = "<a:11845034938353746621:1421383445669613660>"
EMOJI_INFO = "<:info:1422579514218905731>"
EMOJI_BUY = "<:Nitro:1422614999804809226>"
EMOJI_TOSS = "<:TOSS:1421430302684745748>"
EMOJI_COIN = "<:emoji_68:1421430304706658347>"
EMOJI_CULTURE = "<:culture:1421430797604229150>"

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== 파일 DB =====
DB_PATH = "data.json"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "KBRIDGE_9f8a1c2b0e4a4a7f")
_db_lock = threading.Lock()

def _default_db():
    return {
        "categories": [],
        "products": [],
        "logs": {
            "purchase": {"enabled": False, "target_channel_id": None},
            "review": {"enabled": False, "target_channel_id": None},
            "admin": {"enabled": False, "target_channel_id": None}
        },
        "payments": {"bank": False, "coin": False, "culture": False},
        "balances": {},
        "orders": {},
        "account": {"bank": "", "number": "", "holder": ""},
        "bans": {},
        "reviews": {},
        # requests: [{userId, amount, depositor, ts, status(pending|ok|expired)}]
        # receipts: [{hash, amount, depositor, ts, guildId, userId}]
        "topups": {"requests": [], "receipts": []}
    }

def _hash_receipt(gid: int, amount: int, depositor: str, ts_bucket: int) -> str:
    # ts_bucket: 초를 10초 단위 버킷으로 하여 유사중복 줄이기
    base = f"{gid}|{amount}|{str(depositor).strip().lower()}|{ts_bucket}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]

def db_load():
    if not os.path.exists(DB_PATH):
        return _default_db()
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return _default_db()

    base = _default_db()
    for k, v in base.items():
        if k not in data:
            data[k] = v

    # 타입 보정
    if not isinstance(data.get("orders"), dict):
        data["orders"] = {}
    if not isinstance(data.get("balances"), dict):
        data["balances"] = {}
    if not isinstance(data.get("account"), dict):
        data["account"] = {"bank": "", "number": "", "holder": ""}
    if not isinstance(data.get("bans"), dict):
        data["bans"] = {}
    if not isinstance(data.get("reviews"), dict):
        data["reviews"] = {}
    if not isinstance(data.get("topups"), dict):
        data["topups"] = {"requests": [], "receipts": []}
    data["topups"].setdefault("requests", [])
    data["topups"].setdefault("receipts", [])
    if isinstance(data["topups"]["requests"], dict):
        # 과거 guild별 dict였던 걸 리스트로 변환
        merged = []
        for gid, arr in data["topups"]["requests"].items():
            if isinstance(arr, list):
                for r in arr:
                    if isinstance(r, dict):
                        r.setdefault("status", "pending")
                        merged.append(r)
        data["topups"]["requests"] = merged
    if isinstance(data["topups"]["receipts"], dict):
        data["topups"]["receipts"] = []

    # orders 보정
    fixed_orders = {}
    for gid, users in (data["orders"].items() if isinstance(data["orders"], dict) else []):
        bucket = {}
        if isinstance(users, dict):
            for uid, arr in users.items():
                out = []
                if isinstance(arr, list):
                    for rec in arr:
                        if isinstance(rec, dict):
                            out.append({
                                "product": rec.get("product", ""),
                                "qty": int(rec.get("qty", 1) or 1),
                                "ts": int(rec.get("ts", int(time.time())))
                            })
                bucket[str(uid)] = out
        fixed_orders[str(gid)] = bucket
    data["orders"] = fixed_orders

    # balances 보정
    fixed_bal = {}
    for gid, users in (data["balances"].items() if isinstance(data["balances"], dict) else []):
        b = {}
        if isinstance(users, dict):
            for uid, val in users.items():
                try: b[str(uid)] = int(val)
                except: b[str(uid)] = 0
        fixed_bal[str(gid)] = b
    data["balances"] = fixed_bal

    # bans 보정
    fixed_bans = {}
    for gid, users in (data["bans"].items() if isinstance(data["bans"], dict) else []):
        bb = {}
        if isinstance(users, dict):
            for uid, flag in users.items(): bb[str(uid)] = bool(flag)
        fixed_bans[str(gid)] = bb
    data["bans"] = fixed_bans

    # reviews 보정
    fixed_reviews = {}
    for gid, users in (data["reviews"].items() if isinstance(data["reviews"], dict) else []):
        rr = {}
        if isinstance(users, dict):
            for uid, arr in users.items():
                if isinstance(arr, list): rr[str(uid)] = [str(x) for x in arr]
                else: rr[str(uid)] = []
        fixed_reviews[str(gid)] = rr
    data["reviews"] = fixed_reviews

    # account 문자열화
    for k in ("bank", "number", "holder"):
        data["account"][k] = str(data["account"].get(k, ""))

    return data

def db_save():
    with _db_lock:
        tmp = DB.copy()
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(tmp, f, ensure_ascii=False, indent=2)

DB = db_load()

# ===== 유틸 =====
CUSTOM_EMOJI_RE = re.compile(r'^<(?P<anim>a?):(?P<name>[A-Za-z0-9_]+):(?P<id>\d+)>$')
def parse_partial_emoji(text: str):
    if not text: return None
    m = CUSTOM_EMOJI_RE.match(text.strip())
    if not m: return None
    try:
        return discord.PartialEmoji(name=m.group("name"), id=int(m.group("id")), animated=(m.group("anim")=="a"))
    except:
        return None

def safe_emoji(raw: str | None):
    pe = parse_partial_emoji(raw or "")
    return pe if pe else None  # 실패 시 None 리턴해서 UI 안전하게

def is_admin():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.guild_permissions.manage_guild:
            return True
        await interaction.response.send_message("관리자만 사용할 수 있어.", ephemeral=True)
        return False
    return app_commands.check(predicate)

def star_bar_or_none(avg: float | None) -> str:
    if avg is None: return "평점 없음"
    n = max(1, min(int(round(avg)), 5))
    return "⭐️" * n

def ban_is_blocked(gid: int, uid: int) -> bool:
    return bool(DB["bans"].get(str(gid), {}).get(str(uid), False))

# ===== DB 헬퍼 =====
def cat_exists(name: str) -> bool:
    return any(c["name"] == name for c in DB["categories"])

def cat_upsert(name: str, desc: str = "", emoji_raw: str = ""):
    i = next((k for k, c in enumerate(DB["categories"]) if c["name"] == name), -1)
    row = {"name": name, "desc": desc, "emoji_raw": emoji_raw}
    if i >= 0: DB["categories"][i] = row
    else: DB["categories"].append(row)
    db_save()

def cat_delete(name: str):
    DB["categories"] = [c for c in DB["categories"] if c["name"] != name]
    DB["products"] = [p for p in DB["products"] if p["category"] != name]
    db_save()

def prod_get(name: str, category: str):
    return next((p for p in DB["products"] if p["name"] == name and p["category"] == category), None)

def prod_list_by_cat(category: str):
    return [p for p in DB["products"] if p["category"] == category]

def prod_list_all():
    return list(DB["products"])

def prod_upsert(name: str, category: str, price: int, emoji_raw: str = ""):
    p = prod_get(name, category)
    if p:
        p.update({"price": int(max(0, price)), "emoji_raw": emoji_raw})
    else:
        DB["products"].append({
            "name": name, "category": category, "price": int(max(0, price)),
            "stock": 0, "items": [], "emoji_raw": emoji_raw, "ratings": [], "sold_count": 0
        })
    db_save()

def prod_delete(name: str, category: str):
    DB["products"] = [p for p in DB["products"] if not (p["name"] == name and p["category"] == category)]
    db_save()

def product_desc_line(p: dict) -> str:
    ratings = p.get("ratings", [])
    avg = round(statistics.mean(ratings), 1) if ratings else None
    return f"{p['price']}원 | 재고{p['stock']}개 | 평점{star_bar_or_none(avg)}"

def orders_get(gid: int, uid: int):
    g = DB["orders"].get(str(gid))
    if not isinstance(g, dict): return []
    u = g.get(str(uid))
    return u if isinstance(u, list) else []

def orders_add(gid: int, uid: int, product: str, qty: int):
    DB["orders"].setdefault(str(gid), {}).setdefault(str(uid), []).append({"product": product, "qty": qty, "ts": int(time.time())})
    db_save()

def bal_get(gid: int, uid: int) -> int:
    return DB["balances"].get(str(gid), {}).get(str(uid), 0)

def bal_set(gid: int, uid: int, val: int):
    DB["balances"].setdefault(str(gid), {})
    DB["balances"][str(gid)][str(uid)] = val
    db_save()

def bal_add(gid: int, uid: int, amt: int):
    bal_set(gid, uid, bal_get(gid, uid) + max(0, amt))

def bal_sub(gid: int, uid: int, amt: int):
    bal_set(gid, uid, bal_get(gid, uid) - max(0, amt))

# ===== 로그 전송 =====
async def send_log_embed(guild: discord.Guild | None, key: str, embed: discord.Embed):
    if guild is None: return False
    cfg = DB["logs"].get(key) or {}
    if not cfg.get("enabled") or not cfg.get("target_channel_id"): return False
    ch = guild.get_channel(int(cfg["target_channel_id"]))
    if not isinstance(ch, discord.TextChannel): return False
    try:
        await ch.send(embed=embed)
        return True
    except:
        return False

async def send_log_text(guild: discord.Guild | None, key: str, text: str):
    if guild is None: return False
    cfg = DB["logs"].get(key) or {}
    if not cfg.get("enabled") or not cfg.get("target_channel_id"): return False
    ch = guild.get_channel(int(cfg["target_channel_id"]))
    if not isinstance(ch, discord.TextChannel): return False
    try:
        await ch.send(text)
        return True
    except:
        return False

# ===== 임베드 =====
def emb_purchase_log(user: discord.User, product: str, qty: int):
    e = discord.Embed(description=f"{user.mention}님이 {product} {qty}개 구매 감사합니다\n후기 작성 부탁드립니다", color=GRAY)
    e.set_footer(text="구매 시간"); e.timestamp = discord.utils.utcnow(); return e

def emb_review(product: str, stars: int, content: str):
    stars = max(1, min(stars, 5))
    stars_text = "⭐️" * stars
    line = "ㅡ" * 18
    e = discord.Embed(title="구매후기", description=f"**구매 제품** {product}\n**별점** {stars_text}\n{line}\n{content}\n{line}\n이용해주셔서 감사합니다.", color=GRAY)
    e.set_footer(text="작성 시간"); e.timestamp = discord.utils.utcnow(); return e

def emb_purchase_dm(product: str, qty: int, price: int, stock_items: list[str]):
    total = int(price) * int(qty)
    line = "ㅡ" * 18
    visible = stock_items[:20]
    rest = len(stock_items) - len(visible)
    items_block = "\n".join(visible) + (f"\n외 {rest}개…" if rest > 0 else "")
    if not items_block: items_block = "표시할 항목이 없습니다"
    e = discord.Embed(title="구매 성공", description=f"제품 이름 : {product}\n구매 개수 : {qty}개\n차감 금액 : {total}원\n{line}\n구매한 제품\n{items_block}", color=GRAY)
    e.set_footer(text="구매 시간"); e.timestamp = discord.utils.utcnow(); return e

# ===== 자동충전 처리(멀티/5분 타임아웃/임베드 삭제 스케줄) =====
TOPUP_TIMEOUT_SEC = 5 * 60

def _now() -> int: return int(time.time())

def _normalize_name(s: str) -> str:
    return str(s or "").strip().lower()

def _expire_old_requests():
    now = _now()
    changed = False
    for r in DB["topups"]["requests"]:
        if r.get("status", "pending") == "pending":
            if now - int(r.get("ts", now)) > TOPUP_TIMEOUT_SEC:
                r["status"] = "expired"
                changed = True
    if changed: db_save()

async def handle_deposit(guild: discord.Guild, amount: int, depositor: str):
    # 1) 만료 처리
    _expire_old_requests()

    # 2) 중복 수신 방지
    ts_bucket = _now() // 10
    key_hash = _hash_receipt(guild.id, int(amount), depositor, ts_bucket)
    if any(rc.get("hash")==key_hash for rc in DB["topups"]["receipts"]):
        return False, "duplicate"

    # 3) 후보 추출(pending && 5분내)
    now = _now()
    pending = [r for r in DB["topups"]["requests"]
               if r.get("status","pending")=="pending"
               and now - int(r.get("ts", now)) <= TOPUP_TIMEOUT_SEC
               and int(r.get("amount",0)) == int(amount)]

    nd = _normalize_name(depositor)
    exact = [r for r in pending if _normalize_name(r.get("depositor")) == nd]

    # 정렬: 최신 우선
    exact.sort(key=lambda r: int(r.get("ts", 0)), reverse=True)
    pending.sort(key=lambda r: int(r.get("ts", 0)), reverse=True)

    target = None
    if exact:
        target = exact[0]
    elif pending:
        target = pending[0]

    matched_user_id = None
    if target:
        matched_user_id = int(target["userId"])
        target["status"] = "ok"
        bal_add(guild.id, matched_user_id, int(amount))
        db_save()
        try:
            user = guild.get_member(matched_user_id) or await guild.fetch_member(matched_user_id)
            dm = await user.create_dm()
            await dm.send(f"[자동충전 완료]\n금액: {amount}원\n입금자: {depositor}")
        except:
            pass

    DB["topups"]["receipts"].append({
        "hash": key_hash,
        "amount": int(amount),
        "depositor": depositor,
        "ts": _now(),
        "guildId": guild.id,
        "userId": matched_user_id
    })
    db_save()

    if matched_user_id:
        await send_log_text(guild, "admin", f"[자동충전] {amount}원, 입금자={depositor} → user={matched_user_id} 매칭")
        return True, "matched"
    else:
        await send_log_text(guild, "admin", f"[자동충전] {amount}원, 입금자={depositor} 매칭 대기")
        return False, "queued"

async def schedule_delete_after(inter: discord.Interaction, message_id: int, delay_sec: int = TOPUP_TIMEOUT_SEC):
    await asyncio.sleep(delay_sec)
    try:
        msg = await inter.channel.fetch_message(message_id)
        await msg.delete()
    except:
        pass

# ===== 후기/수량 모달 =====
class ReviewModal(discord.ui.Modal, title="구매 후기 작성"):
    product_input = discord.ui.TextInput(label="구매 제품", required=True, max_length=60)
    stars_input = discord.ui.TextInput(label="별점(1~5)", required=True, max_length=1)
    content_input = discord.ui.TextInput(label="후기 내용", style=discord.TextStyle.paragraph, required=True, max_length=500)
    def __init__(self, owner_id: int, product_name: str, category: str):
        super().__init__(); self.owner_id = owner_id; self.category = category; self.product_name = product_name; self.product_input.default = product_name
    async def on_submit(self, it: discord.Interaction):
        try:
            if it.user.id != self.owner_id:
                await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
            gid = str(it.guild.id); uid = str(it.user.id)
            DB["reviews"].setdefault(gid, {}); DB["reviews"][gid].setdefault(uid, [])
            if self.product_name in DB["reviews"][gid][uid]:
                await it.response.send_message("이미 이 제품에 대한 후기를 작성했어.", ephemeral=True); return
            product = str(self.product_input.value).strip()
            s = str(self.stars_input.value).strip()
            content = str(self.content_input.value).strip()
            if not s.isdigit():
                await it.response.send_message("별점은 1~5 숫자로 입력해줘.", ephemeral=True); return
            stars = int(s)
            if stars < 1 or stars > 5:
                await it.response.send_message("별점은 1~5 사이여야 해.", ephemeral=True); return
            p = prod_get(product, self.category)
            if p:
                p.setdefault("ratings", []); p["ratings"].append(stars); db_save()
            try: await send_log_embed(it.guild, "review", emb_review(product, stars, content))
            except: pass
            if self.product_name not in DB["reviews"][gid][uid]:
                DB["reviews"][gid][uid].append(self.product_name); db_save()
            await it.response.send_message("후기 고마워!", ephemeral=True)
        except:
            if not it.response.is_done():
                try: await it.response.send_message("후기 접수 완료!", ephemeral=True)
                except: pass

class ReviewOpenView(discord.ui.View):
    def __init__(self, product_name: str, category: str, owner_id: int):
        super().__init__(timeout=None)
        btn = discord.ui.Button(label="후기 작성", style=discord.ButtonStyle.secondary)
        async def _cb(i: discord.Interaction):
            if i.user.id != owner_id:
                await i.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
            await i.response.send_modal(ReviewModal(owner_id, product_name, category))
        btn.callback = _cb; self.add_item(btn)

class QuantityModal(discord.ui.Modal, title="수량 입력"):
    qty_input = discord.ui.TextInput(label="구매 수량", required=True, max_length=6)
    def __init__(self, owner_id: int, category: str, product_name: str, origin_msg_id: int):
        super().__init__(); self.owner_id = owner_id; self.category = category; self.product_name = product_name; self.origin_msg_id = origin_msg_id
    async def on_submit(self, it: discord.Interaction):
        if it.user.id != self.owner_id:
            await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        s = str(self.qty_input.value).strip()
        if not s.isdigit() or int(s) <= 0:
            await it.response.send_message("수량은 1 이상의 숫자여야 해.", ephemeral=True); return
        qty = int(s)
        p = prod_get(self.product_name, self.category)
        if not p:
            await it.response.send_message("유효하지 않은 제품입니다.", ephemeral=True); return
        if p["stock"] < qty:
            embed_no = discord.Embed(title="재고 부족", description=f"{self.product_name} 재고가 부족합니다.", color=ORANGE)
            try: await it.response.edit_message(embed=embed_no, view=None)
            except discord.InteractionResponded:
                try: await it.followup.edit_message(message_id=self.origin_msg_id, embed=embed_no, view=None)
                except: pass
            return
        taken = []; cnt = qty
        while cnt > 0 and p["items"]:
            taken.append(p["items"].pop(0)); cnt -= 1
        p["stock"] -= qty; p["sold_count"] += qty; db_save()
        bal_sub(it.guild.id, it.user.id, p["price"] * qty)
        await send_log_embed(it.guild, "purchase", emb_purchase_log(it.user, self.product_name, qty))
        try:
            dm = await it.user.create_dm()
            await dm.send(embed=emb_purchase_dm(self.product_name, qty, p["price"], taken),
                          view=ReviewOpenView(self.product_name, self.category, it.user.id))
        except: pass
        embed_ok = discord.Embed(title="구매 완료", description=f"{self.product_name} 구매가 완료되었습니다. DM을 확인해주세요.", color=GREEN)
        try: await it.response.edit_message(embed=embed_ok, view=None)
        except discord.InteractionResponded:
            try: await it.followup.edit_message(message_id=self.origin_msg_id, embed=embed_ok, view=None)
            except: pass

class ProductSelect(discord.ui.Select):
    def __init__(self, owner_id: int, category: str, origin_msg_id: int):
        prods = prod_list_by_cat(category)
        if prods:
            opts = []
            for p in prods[:25]:
                opt = {"label": p["name"], "value": p["name"], "description": product_desc_line(p)}
                e = safe_emoji(p.get("emoji_raw"))
                if e: opt["emoji"] = e
                opts.append(discord.SelectOption(**opt))
        else:
            opts = [discord.SelectOption(label="해당 카테고리에 제품이 없습니다", value="__none__")]
        super().__init__(placeholder="제품을 선택하세요", min_values=1, max_values=1, options=opts, custom_id=f"prod_sel_{owner_id}")
        self.owner_id = owner_id; self.category = category; self.origin_msg_id = origin_msg_id
    async def callback(self, it: discord.Interaction):
        if it.user.id != self.owner_id:
            await it.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
        val = self.values[0]
        if val == "__none__":
            await it.response.send_message("먼저 제품을 추가해주세요.", ephemeral=True); return
        await it.response.send_modal(QuantityModal(self.owner_id, self.category, val, self.origin_msg_id))

class BuyFlowView(discord.ui.View):
    def __init__(self, owner_id: int, category: str, origin_msg_id: int):
        super().__init__(timeout=None); self.add_item(ProductSelect(owner_id, category, origin_msg_id))

class CategorySelectForBuy(discord.ui.Select):
    def __init__(self, owner_id: int, origin_msg_id: int):
        cats = DB["categories"]
        if cats:
            opts = []
            for c in cats[:25]:
                opt = {"label": c["name"], "value": c["name"], "description": (c.get("desc")[:80] if c.get("desc") else None)}
                e = safe_emoji(c.get("emoji_raw"))
                if e: opt["emoji"] = e
                opts.append(discord.SelectOption(**opt))
        else:
            opts = [discord.SelectOption(label="등록된 카테고리가 없습니다", value="__none__")]
        super().__init__(placeholder="카테고리를 선택하세요", min_values=1, max_values=1, options=opts, custom_id=f"cat_buy_{owner_id}")
        self.owner_id = owner_id; self.origin_msg_id = origin_msg_id
    async def callback(self, it: discord.Interaction):
        if it.user.id != self.owner_id:
            await it.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
        val = self.values[0]
        if val == "__none__":
            await it.response.send_message("먼저 카테고리를 추가해주세요.", ephemeral=True); return
        embed = discord.Embed(title="제품 선택하기", description=f"{val} 카테고리의 제품을 선택해주세요", color=GRAY)
        view = BuyFlowView(self.owner_id, val, self.origin_msg_id)
        try: await it.response.edit_message(embed=embed, view=view)
        except discord.InteractionResponded:
            try: await it.followup.edit_message(message_id=self.origin_msg_id, embed=embed, view=view)
            except: pass

class CategorySelectForBuyView(discord.ui.View):
    def __init__(self, owner_id: int, origin_msg_id: int):
        super().__init__(timeout=None); self.add_item(CategorySelectForBuy(owner_id, origin_msg_id))

# ===== 결제수단/계좌/요청 스냅샷 + 5분 임베드 삭제 =====
class PaymentModal(discord.ui.Modal, title="충전 신청"):
    amount_input = discord.ui.TextInput(label="충전할 금액", required=True, max_length=12)
    depositor_input = discord.ui.TextInput(label="입금자명", required=True, max_length=20)
    def __init__(self, method_label: str):
        super().__init__(); self.method_label = method_label
    async def on_submit(self, it: discord.Interaction):
        try:
            if self.method_label == "계좌이체":
                try:
                    amt_raw = str(self.amount_input.value).strip().replace(",", "")
                    amt = int(amt_raw) if amt_raw.isdigit() else 0
                    depos = str(self.depositor_input.value).strip()
                    if amt > 0 and depos:
                        DB["topups"]["requests"].append({
                            "userId": it.user.id,
                            "guildId": it.guild.id,
                            "amount": amt,
                            "depositor": depos,
                            "ts": _now(),
                            "status": "pending"
                        })
                        db_save()
                except:
                    pass

                bank = DB.get("account", {}).get("bank", "미등록")
                number = DB.get("account", {}).get("number", "미등록")
                holder = DB.get("account", {}).get("holder", "미등록")
                amount = str(self.amount_input.value).strip()
                desc = f"은행명 `{bank}`\n계좌번호 `{number}`\n예금주 `{holder}`\n입금 금액 `{amount}`\n- 5분 이내로 입금 부탁드립니다."
                await it.response.send_message(embed=discord.Embed(title="계좌이체 안내", description=desc, color=GRAY), ephemeral=False)
                msg = await it.original_response()
                # 5분 뒤 자동 삭제 스케줄
                asyncio.create_task(schedule_delete_after(it, msg.id, TOPUP_TIMEOUT_SEC))
            else:
                await it.response.send_message(embed=discord.Embed(
                    title="충전 신청 접수",
                    description=f"결제수단: {self.method_label}\n금액: {str(self.amount_input.value).strip()}원\n입금자명: {str(self.depositor_input.value).strip()}",
                    color=GRAY
                ), ephemeral=True)
        except:
            if not it.response.is_done():
                try: await it.response.send_message("충전 신청 접수 완료!", ephemeral=True)
                except: pass

class PaymentMethodView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        b1 = discord.ui.Button(label="계좌이체", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMOJI_TOSS))
        b2 = discord.ui.Button(label="코인충전", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMOJI_COIN))
        b3 = discord.ui.Button(label="문상충전", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMOJI_CULTURE))
        async def _cb(i: discord.Interaction, label: str):
            key = {"계좌이체": "bank", "코인충전": "coin", "문상충전": "culture"}[label]
            if not DB["payments"].get(key, False):
                await i.response.send_message(embed=discord.Embed(title="실패", description="현재 미지원", color=RED), ephemeral=True); return
            await i.response.send_modal(PaymentModal(label))
        b1.callback = lambda i: _cb(i, "계좌이체")
        b2.callback = lambda i: _cb(i, "코인충전")
        b3.callback = lambda i: _cb(i, "문상충전")
        self.add_item(b1); self.add_item(b2); self.add_item(b3)

class AccountSetupModal(discord.ui.Modal, title="계좌번호 설정"):
    bank_input = discord.ui.TextInput(label="은행명", required=True, max_length=30)
    number_input = discord.ui.TextInput(label="계좌번호", required=True, max_length=40)
    holder_input = discord.ui.TextInput(label="예금주", required=True, max_length=30)
    def __init__(self, owner_id: int):
        super().__init__(); self.owner_id = owner_id
    async def on_submit(self, it: discord.Interaction):
        try:
            if it.user.id != self.owner_id:
                await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
            DB.setdefault("account", {})
            DB["account"]["bank"] = str(self.bank_input.value).strip()
            DB["account"]["number"] = str(self.number_input.value).strip()
            DB["account"]["holder"] = str(self.holder_input.value).strip()
            db_save()
            await it.response.send_message(embed=discord.Embed(
                title="계좌정보 저장 완료",
                description=f"은행명 `{DB['account']['bank']}`\n계좌번호 `{DB['account']['number']}`\n예금주 `{DB['account']['holder']}`",
                color=GRAY
            ), ephemeral=True)
        except:
            if not it.response.is_done():
                try: await it.response.send_message("계좌정보 저장 완료!", ephemeral=True)
                except: pass

# ===== 최근 구매/내 정보 =====
class RecentOrdersSelect(discord.ui.Select):
    def __init__(self, owner_id: int, orders: list[dict]):
        opts = []
        for o in orders[-5:][::-1]:
            label = f"{o['product']} x{o['qty']}"
            ts = time.strftime('%Y-%m-%d %H:%M', time.localtime(o['ts']))
            opts.append(discord.SelectOption(label=label, description=ts, value=f"{o['product']}||{o['qty']}||{o['ts']}"))
        if not opts:
            opts = [discord.SelectOption(label="최근 구매 없음", value="__none__", description="표시할 항목이 없습니다")]
        super().__init__(placeholder="최근 구매 내역 보기", min_values=1, max_values=1, options=opts, custom_id=f"recent_{owner_id}")
        self.owner_id = owner_id
    async def callback(self, it: discord.Interaction):
        if it.user.id != self.owner_id:
            await it.response.send_message("작성자만 볼 수 있어.", ephemeral=True); return
        val = self.values[0]
        if val == "__none__":
            await it.response.send_message("최근 구매가 없습니다.", ephemeral=True); return
        name, qty, ts = val.split("||")
        ts_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(int(ts)))
        await it.response.send_message(embed=discord.Embed(title="구매 상세", description=f"- 제품: {name}\n- 수량: {qty}\n- 시간: {ts_str}", color=GRAY), ephemeral=True)

class MyInfoView(discord.ui.View):
    def __init__(self, owner_id: int, orders: list[dict]):
        super().__init__(timeout=None); self.add_item(RecentOrdersSelect(owner_id, orders))

# ===== 2x2 버튼 패널 =====
class ButtonPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        n = discord.ui.Button(label="공지사항", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMOJI_NOTICE), row=0)
        c = discord.ui.Button(label="충전", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMOJI_CHARGE), row=0)
        i = discord.ui.Button(label="내 정보", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMOJI_INFO), row=1)
        b = discord.ui.Button(label="구매", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMOJI_BUY), row=1)
        async def _notice(it): await it.response.send_message(embed=discord.Embed(title="공지사항", description="서버규칙 필독 부탁드립니다\n자충 오류시 티켓 열어주세요", color=GRAY), ephemeral=True)
        async def _charge(it):
            if ban_is_blocked(it.guild.id, it.user.id):
                await it.response.send_message(embed=discord.Embed(title="이용 불가", description="차단 상태입니다. /유저_설정으로 해제하세요.", color=RED), ephemeral=True); return
            await it.response.send_message(embed=discord.Embed(title="결제수단 선택하기", description="원하시는 결제수단 버튼을 클릭해주세요", color=GRAY), view=PaymentMethodView(), ephemeral=True)
        async def _info(it):
            gid = it.guild.id; uid = it.user.id
            balance = bal_get(gid, uid)
            ords = orders_get(gid, uid)
            total_spent = 0
            for o in ords:
                p = next((pp for pp in DB["products"] if pp["name"] == o["product"]), None)
                if p: total_spent += p["price"] * o["qty"]
            header = f"보유 금액 : {balance}원\n누적 금액 : {total_spent}원\n거래 횟수 : {len(ords)}건"
            await it.response.send_message(embed=discord.Embed(title="내 정보", description=header, color=GRAY), view=MyInfoView(uid, ords), ephemeral=True)
        async def _buy(it):
            if ban_is_blocked(it.guild.id, it.user.id):
                await it.response.send_message(embed=discord.Embed(title="이용 불가", description="차단 상태입니다. /유저_설정으로 해제하세요.", color=RED), ephemeral=True); return
            await it.response.send_message(embed=discord.Embed(title="카테고리 선택하기", description="구매할 카테고리를 선택해주세요", color=GRAY), ephemeral=True)
            msg = await it.original_response()
            await msg.edit(view=CategorySelectForBuyView(it.user.id, msg.id))
        n.callback = _notice; c.callback = _charge; i.callback = _info; b.callback = _buy
        self.add_item(n); self.add_item(c); self.add_item(i); self.add_item(b)

# ===== 카테고리/제품/재고/로그 =====
class LogChannelIdModal(discord.ui.Modal, title="로그 채널 설정"):
    channel_id_input = discord.ui.TextInput(label="채널 ID", required=True, max_length=25)
    def __init__(self, owner_id: int, log_key: str):
        super().__init__(); self.owner_id = owner_id; self.log_key = log_key
    async def on_submit(self, it: discord.Interaction):
        if it.user.id != self.owner_id:
            await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        raw = str(self.channel_id_input.value).strip()
        if not raw.isdigit():
            await it.response.send_message(embed=discord.Embed(title="실패", description="채널 ID는 숫자여야 합니다.", color=RED), ephemeral=True); return
        ch = it.guild.get_channel(int(raw))
        if not isinstance(ch, discord.TextChannel):
            await it.response.send_message(embed=discord.Embed(title="실패", description="유효한 텍스트 채널 ID가 아닙니다.", color=RED), ephemeral=True); return
        DB["logs"].setdefault(self.log_key, {"enabled": False, "target_channel_id": None})
        DB["logs"][self.log_key]["target_channel_id"] = int(raw)
        DB["logs"][self.log_key]["enabled"] = True
        db_save()
        pretty = {"purchase": "구매로그", "review": "구매후기", "admin": "관리자로그"}[self.log_key]
        await it.response.send_message(embed=discord.Embed(title=f"{pretty} 채널 지정 완료", description=f"목적지: {ch.mention}", color=GRAY), ephemeral=True)

class StockAddModal(discord.ui.Modal, title="재고 추가"):
    lines_input = discord.ui.TextInput(label="재고 추가(줄마다 1개로 인식)", style=discord.TextStyle.paragraph, required=True, max_length=4000)
    def __init__(self, owner_id: int, product_name: str, category: str):
        super().__init__(); self.owner_id = owner_id; self.product_name = product_name; self.category = category
    async def on_submit(self, it: discord.Interaction):
        try:
            if it.user.id != self.owner_id:
                await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
            lines = [ln.strip() for ln in str(self.lines_input.value).splitlines() if ln.strip()]
            p = prod_get(self.product_name, self.category)
            if not p:
                await it.response.send_message("유효하지 않은 제품입니다.", ephemeral=True); return
            p["items"].extend(lines); p["stock"] += len(lines); db_save()
            await it.response.send_message(embed=discord.Embed(title="재고 추가 완료", description=f"제품: {self.product_name} ({self.category})\n추가 수량: {len(lines)}\n현재 재고: {p['stock']}", color=GRAY), ephemeral=True)
        except:
            if not it.response.is_done():
                try: await it.response.send_message("재고 추가 완료!", ephemeral=True)
                except: pass

class CategorySetupModal(discord.ui.Modal, title="카테고리 추가"):
    name_input = discord.ui.TextInput(label="카테고리 이름", required=True, max_length=60)
    desc_input = discord.ui.TextInput(label="카테고리 설명", style=discord.TextStyle.paragraph, required=False, max_length=200)
    emoji_input = discord.ui.TextInput(label="카테고리 이모지", required=False, max_length=100)
    def __init__(self, owner_id: int):
        super().__init__(); self.owner_id = owner_id
    async def on_submit(self, it: discord.Interaction):
        if it.user.id != self.owner_id:
            await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        name = str(self.name_input.value).strip()
        desc = str(self.desc_input.value).strip() if self.desc_input.value else ""
        emoji = str(self.emoji_input.value).strip() if self.emoji_input.value else ""
        cat_upsert(name, desc, emoji)
        prev = str(parse_partial_emoji(emoji)) if emoji else ""
        await it.response.send_message(embed=discord.Embed(title="카테고리 등록 완료", description=f"{(prev+' ') if prev else ''}{name}\n{desc}", color=GRAY), ephemeral=True)

class CategoryDeleteSelect(discord.ui.Select):
    def __init__(self, owner_id: int):
        cats = DB["categories"]; opts = []
        for c in cats[:25]:
            opt = {"label": c["name"], "value": c["name"], "description": (c.get("desc")[:80] if c.get("desc") else None)}
            e = safe_emoji(c.get("emoji_raw"))
            if e: opt["emoji"] = e
            opts.append(discord.SelectOption(**opt))
        super().__init__(placeholder="삭제할 카테고리를 선택하세요", min_values=1, max_values=1, options=opts or [discord.SelectOption(label="삭제할 카테고리가 없습니다", value="__none__")], custom_id=f"cat_del_{owner_id}")
        self.owner_id = owner_id
    async def callback(self, it: discord.Interaction):
        if it.user.id != self.owner_id:
            await it.response.send_message("작성자만 선택할 수 있어.", ephemeral=True); return
        val = self.values[0]
        if val == "__none__":
            await it.response.send_message("삭제할 카테고리가 없습니다.", ephemeral=True); return
        cat_delete(val)
        await it.response.send_message(embed=discord.Embed(title="카테고리 삭제 완료", description=f"삭제된 카테고리: {val}", color=GRAY), ephemeral=True)

class CategoryDeleteView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None); self.add_item(CategoryDeleteSelect(owner_id))

class ProductSetupModal(discord.ui.Modal, title="제품 추가"):
    name_input = discord.ui.TextInput(label="제품 이름", required=True, max_length=60)
    category_input = discord.ui.TextInput(label="카테고리 이름", required=True, max_length=60)
    price_input = discord.ui.TextInput(label="제품 가격(원)", required=True, max_length=10)
    emoji_input = discord.ui.TextInput(label="제품 이모지", required=False, max_length=100)
    def __init__(self, owner_id: int):
        super().__init__(); self.owner_id = owner_id
    async def on_submit(self, it: discord.Interaction):
        if it.user.id != self.owner_id:
            await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        name = str(self.name_input.value).strip()
        cat = str(self.category_input.value).strip()
        price_s = str(self.price_input.value).strip()
        if not cat_exists(cat):
            await it.response.send_message("해당 카테고리가 존재하지 않습니다.", ephemeral=True); return
        if not price_s.isdigit():
            await it.response.send_message("가격은 숫자만 입력해줘.", ephemeral=True); return
        price = int(price_s)
        emoji = str(self.emoji_input.value).strip() if self.emoji_input.value else ""
        prod_upsert(name, cat, price, emoji)
        em = str(parse_partial_emoji(emoji)) if emoji else ""
        desc = product_desc_line(prod_get(name, cat))
        await it.response.send_message(embed=discord.Embed(title="제품 등록 완료", description=f"{(em+' ') if em else ''}{name}\n카테고리: {cat}\n{desc}", color=GRAY), ephemeral=True)

class ProductDeleteSelect(discord.ui.Select):
    def __init__(self, owner_id: int):
        prods = prod_list_all(); opts = []
        for p in prods[:25]:
            opt = {"label": p["name"], "value": f"{p['name']}||{p['category']}", "description": product_desc_line(p)}
            e = safe_emoji(p.get("emoji_raw"))
            if e: opt["emoji"] = e
            opts.append(discord.SelectOption(**opt))
        super().__init__(placeholder="삭제할 제품을 선택하세요", min_values=1, max_values=1, options=opts or [discord.SelectOption(label="삭제할 제품이 없습니다", value="__none__")], custom_id=f"prod_del_{owner_id}")
        self.owner_id = owner_id
    async def callback(self, it: discord.Interaction):
        if it.user.id != self.owner_id:
            await it.response.send_message("작성자만 선택할 수 있어.", ephemeral=True); return
        val = self.values[0]
        if val == "__none__":
            await it.response.send_message("삭제할 제품이 없습니다.", ephemeral=True); return
        name, cat = val.split("||", 1)
        prod_delete(name, cat)
        await it.response.send_message(embed=discord.Embed(title="제품 삭제 완료", description=f"삭제된 제품: {name} (카테고리: {cat})", color=GRAY), ephemeral=True)

class ProductDeleteView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None); self.add_item(ProductDeleteSelect(owner_id))

# ===== 슬래시 COG(10개) =====
class ControlCog(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    @app_commands.command(name="버튼패널", description="버튼 패널을 표시합니다.")
    @app_commands.guilds(GUILD)
    async def 버튼패널(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(title="윈드 OTT", description="아래 버튼으로 이용해주세요!", color=GRAY),
                                       view=ButtonPanel())

    @app_commands.command(name="카테고리_설정", description="구매 카테고리를 설정합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 카테고리_설정(self, it: discord.Interaction):
        view = discord.ui.View(timeout=None)
        class CategoryRootSelect(discord.ui.Select):
            def __init__(self, owner_id: int):
                super().__init__(placeholder="카테고리 설정하기", min_values=1, max_values=1,
                                 options=[discord.SelectOption(label="카테고리 추가", value="add"),
                                          discord.SelectOption(label="카테고리 삭제", value="del")],
                                 custom_id=f"cat_root_{owner_id}")
                self.owner_id = owner_id
            async def callback(self, inter: discord.Interaction):
                if inter.user.id != self.owner_id:
                    await inter.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
                if self.values[0] == "add":
                    await inter.response.send_modal(CategorySetupModal(self.owner_id))
                else:
                    await inter.response.send_message(embed=discord.Embed(title="카테고리 삭제", description="삭제할 카테고리를 선택하세요.", color=GRAY), view=CategoryDeleteView(self.owner_id), ephemeral=True)
        view.add_item(CategoryRootSelect(it.user.id))
        await it.response.send_message(embed=discord.Embed(title="카테고리 설정하기", description="카테고리 설정해주세요", color=GRAY), view=view, ephemeral=True)

    @app_commands.command(name="제품_설정", description="제품을 추가/삭제로 관리합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 제품_설정(self, it: discord.Interaction):
        view = discord.ui.View(timeout=None)
        class ProductRootSelect(discord.ui.Select):
            def __init__(self, owner_id: int):
                super().__init__(placeholder="제품 설정하기", min_values=1, max_values=1,
                                 options=[discord.SelectOption(label="제품 추가", value="add"),
                                          discord.SelectOption(label="제품 삭제", value="del")],
                                 custom_id=f"prod_root_{owner_id}")
                self.owner_id = owner_id
            async def callback(self, inter: discord.Interaction):
                if inter.user.id != self.owner_id:
                    await inter.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
                if self.values[0] == "add":
                    await inter.response.send_modal(ProductSetupModal(self.owner_id))
                else:
                    await inter.response.send_message(embed=discord.Embed(title="제품 삭제", description="삭제할 제품을 선택하세요.", color=GRAY), view=ProductDeleteView(self.owner_id), ephemeral=True)
        view.add_item(ProductRootSelect(it.user.id))
        await it.response.send_message(embed=discord.Embed(title="제품 설정하기", description="제품 설정해주세요", color=GRAY), view=view, ephemeral=True)

    @app_commands.command(name="재고_설정", description="제품 재고를 추가합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 재고_설정(self, it: discord.Interaction):
        class StockProductSelect(discord.ui.Select):
            def __init__(self, owner_id: int):
                prods = prod_list_all()
                if prods:
                    opts = []
                    for p in prods[:25]:
                        opt = {"label": f"{p['name']} ({p['category']})", "value": f"{p['name']}||{p['category']}", "description": product_desc_line(p)}
                        e = safe_emoji(p.get("emoji_raw"))
                        if e: opt["emoji"] = e
                        opts.append(discord.SelectOption(**opt))
                else:
                    opts = [discord.SelectOption(label="등록된 제품이 없습니다", value="__none__")]
                super().__init__(placeholder="재고를 설정할 제품을 선택하세요", min_values=1, max_values=1, options=opts, custom_id=f"stock_prod_{owner_id}")
                self.owner_id = owner_id
            async def callback(self, inter: discord.Interaction):
                if inter.user.id != self.owner_id:
                    await inter.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
                val = self.values[0]
                if val == "__none__":
                    await inter.response.send_message("먼저 제품을 추가해주세요.", ephemeral=True); return
                name, cat = val.split("||", 1)
                await inter.response.send_modal(StockAddModal(self.owner_id, name, cat))
        class StockRootView(discord.ui.View):
            def __init__(self, owner_id: int):
                super().__init__(timeout=None)
                class _Sel(discord.ui.Select):
                    def __init__(self, owner_id: int):
                        super().__init__(placeholder="재고 설정하기", min_values=1, max_values=1,
                                         options=[discord.SelectOption(label="재고 설정", value="set")],
                                         custom_id=f"stock_root_{owner_id}")
                        self.owner_id = owner_id
                    async def callback(self, inter: discord.Interaction):
                        if inter.user.id != self.owner_id:
                            await inter.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
                        embed = discord.Embed(title="제품 선택", description="재고를 설정할 제품을 선택해주세요", color=GRAY)
                        view = discord.ui.View(timeout=None); view.add_item(StockProductSelect(self.owner_id))
                        try: await inter.response.edit_message(embed=embed, view=view)
                        except discord.InteractionResponded:
                            try: await inter.followup.edit_message(message_id=inter.message.id, embed=embed, view=view)
                            except: pass
                self.add_item(_Sel(owner_id))
        await it.response.send_message(embed=discord.Embed(title="재고 설정하기", description="재고 설정해주세요", color=GRAY), view=StockRootView(it.user.id), ephemeral=True)

    @app_commands.command(name="로그_설정", description="구매로그/구매후기/관리자로그 채널을 설정합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 로그_설정(self, it: discord.Interaction):
        class LogRootView(discord.ui.View):
            def __init__(self, owner_id: int):
                super().__init__(timeout=None)
                class _Sel(discord.ui.Select):
                    def __init__(self, owner_id: int):
                        options = [discord.SelectOption(label="구매로그 설정", value="purchase"),
                                   discord.SelectOption(label="구매후기 설정", value="review"),
                                   discord.SelectOption(label="관리자로그 설정", value="admin")]
                        super().__init__(placeholder="설정할 로그 유형을 선택하세요", min_values=1, max_values=1, options=options, custom_id=f"log_root_{owner_id}")
                        self.owner_id = owner_id
                    async def callback(self, inter: discord.Interaction):
                        if inter.user.id != self.owner_id:
                            await inter.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
                        await inter.response.send_modal(LogChannelIdModal(self.owner_id, self.values[0]))
                self.add_item(_Sel(owner_id))
        await it.response.send_message(embed=discord.Embed(title="로그 설정하기", description="로그 설정해주세요", color=GRAY), view=LogRootView(it.user.id), ephemeral=True)

    @app_commands.command(name="잔액_설정", description="유저 잔액을 추가/차감합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    @app_commands.describe(유저="대상 유저", 금액="정수 금액", 여부="추가/차감")
    @app_commands.choices(여부=[app_commands.Choice(name="추가", value="추가"),
                               app_commands.Choice(name="차감", value="차감")])
    async def 잔액_설정(self, it: discord.Interaction, 유저: discord.Member, 금액: int, 여부: app_commands.Choice[str]):
        if 금액 < 0:
            await it.response.send_message("금액은 음수가 될 수 없어.", ephemeral=True); return
        gid = it.guild.id; uid = 유저.id; prev = bal_get(gid, uid)
        if 여부.value == "차감":
            bal_sub(gid, uid, 금액); after = bal_get(gid, uid)
            e = discord.Embed(title=f"{유저} 금액 차감", description=f"원래 금액 : {prev}\n차감 할 금액 : {금액}\n차감 후 금액 : {after}", color=RED)
            e.set_footer(text="변경 시간"); e.timestamp = discord.utils.utcnow()
            await it.response.send_message(embed=e, ephemeral=True)
        else:
            bal_add(gid, uid, 금액); after = bal_get(gid, uid)
            e = discord.Embed(title=f"{유저} 금액 추가", description=f"원래 금액 : {prev}\n추가 할 금액 : {금액}\n추가 후 금액 : {after}", color=GREEN)
            e.set_footer(text="변경 시간"); e.timestamp = discord.utils.utcnow()
            await it.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="결제수단_설정", description="결제수단 지원 여부를 설정합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    @app_commands.describe(계좌이체="지원/미지원", 코인충전="지원/미지원", 문상충전="지원/미지원")
    @app_commands.choices(
        계좌이체=[app_commands.Choice(name="지원", value="지원"), app_commands.Choice(name="미지원", value="미지원")],
        코인충전=[app_commands.Choice(name="지원", value="지원"), app_commands.Choice(name="미지원", value="미지원")],
        문상충전=[app_commands.Choice(name="지원", value="지원"), app_commands.Choice(name="미지원", value="미지원")]
    )
    async def 결제수단_설정(self, it: discord.Interaction,
                        계좌이체: app_commands.Choice[str],
                        코인충전: app_commands.Choice[str],
                        문상충전: app_commands.Choice[str]):
        DB["payments"]["bank"] = (계좌이체.value == "지원")
        DB["payments"]["coin"] = (코인충전.value == "지원")
        DB["payments"]["culture"] = (문상충전.value == "지원")
        db_save()
        await it.response.send_message(embed=discord.Embed(
            title="결제수단 설정 완료",
            description=f"계좌이체: {계좌이체.value}\n코인충전: {코인충전.value}\n문상충전: {문상충전.value}",
            color=GRAY
        ), ephemeral=True)

    @app_commands.command(name="계좌번호_설정", description="은행명/계좌번호/예금주를 설정합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 계좌번호_설정(self, it: discord.Interaction):
        await it.response.send_modal(AccountSetupModal(it.user.id))

    @app_commands.command(name="유저_설정", description="유저 차단/차단풀기")
    @app_commands.guilds(GUILD)
    @is_admin()
    @app_commands.describe(유저="대상 유저", 여부="차단하기/차단풀기")
    @app_commands.choices(여부=[app_commands.Choice(name="차단하기", value="ban"),
                               app_commands.Choice(name="차단풀기", value="unban")])
    async def 유저_설정(self, it: discord.Interaction, 유저: discord.Member, 여부: app_commands.Choice[str]):
        gid = str(it.guild.id); uid = str(유저.id)
        DB["bans"].setdefault(gid, {})
        if 여부.value == "ban":
            DB["bans"][gid][uid] = True; db_save()
            e = discord.Embed(title="차단하기", description=f"{유저}님은 자판기 이용 불가능합니다\n- 차단해제는 /유저_설정", color=RED)
            await it.channel.send(embed=e)
            await it.response.send_message("처리 완료", ephemeral=True)
        else:
            DB["bans"][gid].pop(uid, None); db_save()
            e = discord.Embed(title="차단풀기", description=f"{유저}님은 다시 자판기 이용 가능합니다", color=GREEN)
            await it.channel.send(embed=e)
            await it.response.send_message("처리 완료", ephemeral=True)

    @app_commands.command(name="유저_조회", description="유저 보유/누적 금액 조회")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 유저_조회(self, it: discord.Interaction, 유저: discord.Member):
        gid = it.guild.id; uid = 유저.id
        balance = bal_get(gid, uid)
        ords = orders_get(gid, uid)
        total_spent = 0
        for o in ords:
            p = next((pp for pp in DB["products"] if pp["name"] == o["product"]), None)
            if p: total_spent += p["price"] * o["qty"]
        e = discord.Embed(title=f"{유저} 정보", description=f"보유 금액 : `{balance}`\n누적 금액 : `{total_spent}`", color=GRAY)
        await it.response.send_message(embed=e, ephemeral=True)

# ===== FastAPI 웹훅 =====
app = FastAPI()

@app.post("/kbank-webhook")
async def kbank_webhook(req: Request):
    try:
        token = (req.headers.get("Authorization") or "").replace("Bearer", "").strip()
        if token != WEBHOOK_SECRET:
            return {"ok": False, "error": "unauthorized"}

        payload = await req.json()
        gid = int(payload.get("guildId"))
        amount = int(str(payload.get("amount")).replace(",", ""))
        depositor = str(payload.get("depositor")).strip()

        guild = bot.get_guild(gid)
        if not guild:
            return {"ok": False, "error": "guild_not_found"}

        ok, msg = await handle_deposit(guild, amount, depositor)
        return {"ok": ok, "result": msg}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8787")), log_level="warning")

# ===== 등록/싱크/기동 =====
async def guild_sync(b: commands.Bot):
    try:
        synced = await b.tree.sync(guild=GUILD)
        print(f"[setup_hook] 길드 싱크 완료({GUILD_ID}): {len(synced)}개 -> {', '.join('/'+c.name for c in synced)}")
    except Exception as e:
        print(f"[setup_hook] 길드 싱크 실패: {e}")

@bot.event
async def setup_hook():
    await bot.add_cog(ControlCog(bot))
    await guild_sync(bot)

@bot.event
async def on_ready():
    print(f"로그인: {bot.user} (준비 완료)")
    t = threading.Thread(target=run_api, daemon=True)
    t.start()

TOKEN = os.getenv("DISCORD_TOKEN", "여기에_토큰_넣기")
bot.run(TOKEN)
