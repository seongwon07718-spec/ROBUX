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

# 이모지
EMOJI_NOTICE = "<:Announcement:1422906665249800274>"
EMOJI_CHARGE = "<a:11845034938353746621:1421383445669613660>"
EMOJI_INFO = "<:info:1422579514218905731>"
EMOJI_BUY = "<:charge:1422579519222714482>"  # 요청대로 교체
EMOJI_TOSS = "<:TOSS:1421430302684745748>"
EMOJI_COIN = "<:emoji_68:1421430304706658347>"
EMOJI_CULTURE = "<:culture:1421430797604229150>"
EMOJI_TICKET = "<:ticket:1389546740054626304>"

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== DB =====
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
        "points": {},
        "orders": {},  # 전건 무제한 누적
        "account": {"bank": "", "number": "", "holder": ""},
        "bans": {},
        "reviews": {},
        "topups": {"requests": [], "receipts": []}
    }

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
        data.setdefault(k, v)
    # 정수 보정
    def _intmap(d):
        out={}
        if isinstance(d, dict):
            for k,v in d.items():
                try: out[str(k)] = int(v)
                except: out[str(k)] = 0
        return out
    data["balances"] = {str(g): _intmap(u) for g,u in data.get("balances", {}).items()}
    data["points"]   = {str(g): _intmap(u) for g,u in data.get("points",   {}).items()}
    for k in ("bank","number","holder"):
        data["account"][k] = str(data["account"].get(k,""))
    data["topups"].setdefault("requests", [])
    data["topups"].setdefault("receipts", [])
    return data

def db_save():
    with _db_lock:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(DB, f, ensure_ascii=False, indent=2)

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
    return pe if pe else None

def _now(): return int(time.time())

def star_bar(avg: float | None) -> str:
    if avg is None: return "평점 없음"
    n = max(1, min(int(round(avg)), 5))
    return "⭐️"*n

def ban_is_blocked(gid: int, uid: int) -> bool:
    return bool(DB["bans"].get(str(gid), {}).get(str(uid), False))

def bal_get(gid: int, uid: int) -> int:
    return DB["balances"].get(str(gid), {}).get(str(uid), 0)

def bal_set(gid: int, uid: int, val: int):
    DB["balances"].setdefault(str(gid), {})
    DB["balances"][str(gid)][str(uid)] = int(val); db_save()

def bal_add(gid: int, uid: int, amt: int):
    bal_set(gid, uid, bal_get(gid, uid) + max(0, int(amt)))

def bal_sub(gid: int, uid: int, amt: int):
    bal_set(gid, uid, bal_get(gid, uid) - max(0, int(amt)))

def pt_get(gid: int, uid: int) -> int:
    return DB["points"].get(str(gid), {}).get(str(uid), 0)

def pt_set(gid: int, uid: int, val: int):
    DB["points"].setdefault(str(gid), {})
    DB["points"][str(gid)][str(uid)] = int(val); db_save()

def orders_get(gid: int, uid: int):
    return DB.get("orders", {}).get(str(gid), {}).get(str(uid), [])

def orders_add(gid: int, uid: int, product: str, qty: int):
    DB.setdefault("orders", {}).setdefault(str(gid), {}).setdefault(str(uid), []).append(
        {"product": product, "qty": int(qty), "ts": _now()}
    ); db_save()

def prod_get(name: str, category: str):
    return next((p for p in DB["products"] if p["name"]==name and p["category"]==category), None)

def prod_list_by_cat(category: str):
    return [p for p in DB["products"] if p["category"]==category]

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
    DB["products"] = [p for p in DB["products"] if not (p["name"]==name and p["category"]==category)]
    db_save()

def product_desc_line(p: dict) -> str:
    ratings = p.get("ratings", [])
    avg = round(statistics.mean(ratings), 1) if ratings else None
    return f"{p['price']}원 | 재고{p['stock']}개 | 평점{star_bar(avg)}"

# ===== 공통 임베드 스타일 v2 =====
def set_footer_bot(embed: discord.Embed):
    try:
        embed.set_footer(text=str(bot.user), icon_url=bot.user.display_avatar.url)
    except:
        embed.set_footer(text=str(bot.user))
    embed.timestamp = discord.utils.utcnow()

# ===== 로그 전송 =====
async def send_log_embed(guild: discord.Guild | None, key: str, embed: discord.Embed):
    if guild is None: return False
    cfg = DB["logs"].get(key) or {}
    if not cfg.get("enabled") or not cfg.get("target_channel_id"): return False
    ch = guild.get_channel(int(cfg["target_channel_id"]))
    if not isinstance(ch, discord.TextChannel): return False
    try:
        await ch.send(embed=embed); return True
    except: return False

async def send_log_text(guild: discord.Guild | None, key: str, text: str):
    if guild is None: return False
    cfg = DB["logs"].get(key) or {}
    if not cfg.get("enabled") or not cfg.get("target_channel_id"): return False
    ch = guild.get_channel(int(cfg["target_channel_id"]))
    if not isinstance(ch, discord.TextChannel): return False
    try:
        await ch.send(text); return True
    except: return False

# ===== 구매로그/후기/DM 임베드 =====
def emb_purchase_log(user: discord.User, product: str, qty: int):
    e = discord.Embed(title="구매로그",
                      description=f"{user.mention}님 {product} {qty}개\n구매 감사합니다 후기 작성 부탁드립니다:gift_heart:",
                      color=GRAY)
    set_footer_bot(e)
    return e

def emb_review_full(user: discord.User, product: str, stars: int, content: str):
    stars = max(1, min(stars, 5))
    stars_text = "⭐️" * stars
    line = "ㅡ"*18
    e = discord.Embed(title="구매 후기",
                      description=f"**구매제품** : {product}\n**별점** : {stars_text}\n{line}\n{content}\n{line}",
                      color=GRAY)
    set_footer_bot(e)
    return e

def emb_purchase_dm(product: str, qty: int, price: int, items: list[str]):
    line = "ㅡ"*18
    visible = items[:20]
    rest = len(items) - len(visible)
    block = "\n".join(visible) + (f"\n외 {rest}개…" if rest>0 else "")
    if not block: block = "표시할 항목이 없습니다"
    e = discord.Embed(title="구매 성공",
                      description=f"제품 이름 : {product}\n구매 개수 : {qty}\n차감 금액 : {price}\n{line}\n{block}",
                      color=GREEN)
    set_footer_bot(e)
    return e

# ===== 자동충전(카뱅 파서) =====
TOPUP_TIMEOUT_SEC = 5*60

RE_AMOUNT = [re.compile(r"입금\s*([0-9][0-9,]*)\s*원")]
def parse_sms_kakaobank(msg: str) -> tuple[int | None, str | None]:
    text = str(msg or "")
    amount = None
    for r in RE_AMOUNT:
        m = r.search(text)
        if m:
            raw = m.group(1).replace(",", "")
            if raw.isdigit():
                amount = int(raw); break
    depositor = None
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for i,l in enumerate(lines):
        if l.startswith("입금"):
            if i+1 < len(lines):
                depositor = lines[i+1].split()[0]
            break
    if depositor and ("잔액" in depositor or depositor.startswith("잔액")):
        depositor = None
    return amount, depositor

RE_DEPOSITOR_FALLBACK = [
    re.compile(r"입금\s+[0-9,]+\s*원\s+([^\s\|]+)"),
    re.compile(r"입금자\s*[:\-]?\s*([^\s\|]+)"),
    re.compile(r"(보낸분|보낸이)\s*[:\-]?\s*([^\s\|]+)"),
    re.compile(r"\n([^\n\|]+)\s*(잔액|원|입금|$)")
]
def parse_sms_any(msg: str) -> tuple[int | None, str | None]:
    amount = None
    m = re.search(r"([0-9][0-9,]*)\s*원", msg or "")
    if m:
        raw = m.group(1).replace(",", "")
        if raw.isdigit():
            amount = int(raw)
    depositor = None
    for r in RE_DEPOSITOR_FALLBACK:
        m = r.search(msg or "")
        if m:
            name = m.group(2) if (m.lastindex and m.lastindex>=2) else m.group(1)
            depositor = str(name).strip()
            break
    return amount, depositor

def parse_sms(msg: str) -> tuple[int | None, str | None]:
    a, d = parse_sms_kakaobank(msg)
    if a is None or d is None:
        a2, d2 = parse_sms_any(msg)
        if a is None: a = a2
        if d is None: d = d2
    return a, d

def expire_old_requests():
    now = _now()
    changed=False
    for r in DB["topups"]["requests"]:
        if r.get("status","pending")=="pending" and now - int(r.get("ts", now)) > TOPUP_TIMEOUT_SEC:
            r["status"]="expired"; changed=True
    if changed: db_save()

def _hash_receipt(gid:int, amount:int, depositor:str):
    bucket = _now() // 10
    base = f"{gid}|{amount}|{str(depositor).lower()}|{bucket}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]

async def handle_deposit(guild: discord.Guild, amount: int, depositor: str):
    expire_old_requests()
    key = _hash_receipt(guild.id, int(amount), str(depositor))
    if any(rc.get("hash")==key for rc in DB["topups"]["receipts"]):
        return False, "duplicate"
    now = _now()
    pending = [r for r in DB["topups"]["requests"]
               if r.get("status","pending")=="pending"
               and r.get("guildId")==guild.id
               and now - int(r.get("ts", now)) <= TOPUP_TIMEOUT_SEC
               and int(r.get("amount",0)) == int(amount)]
    exact = [r for r in pending if str(r.get("depositor","")).strip().lower()==str(depositor).strip().lower()]
    exact.sort(key=lambda r: int(r.get("ts",0)), reverse=True)
    pending.sort(key=lambda r: int(r.get("ts",0)), reverse=True)
    target = exact[0] if exact else (pending[0] if pending else None)
    matched_user_id = None
    if target:
        matched_user_id = int(target["userId"])
        target["status"]="ok"
        bal_add(guild.id, matched_user_id, int(amount))
        db_save()
        try:
            user = guild.get_member(matched_user_id) or await guild.fetch_member(matched_user_id)
            dm = await user.create_dm()
            await dm.send(f"[자동충전 완료]\n금액: {amount}원\n입금자: {depositor}")
        except: pass
    DB["topups"]["receipts"].append({
        "hash": key, "guildId": guild.id, "amount": int(amount),
        "depositor": str(depositor), "ts": _now(), "userId": matched_user_id
    }); db_save()
    if matched_user_id:
        await send_log_text(guild, "admin", f"[자동충전] {amount}원, 입금자={depositor} → user={matched_user_id} 매칭")
        return True, "matched"
    else:
        await send_log_text(guild, "admin", f"[자동충전] {amount}원, 입금자={depositor} 매칭 대기")
        return False, "queued"

# ===== 구매/후기/결제 UI =====
class ReviewModal(discord.ui.Modal, title="구매 후기 작성"):
    product_input = discord.ui.TextInput(label="구매 제품", required=True, max_length=60)
    stars_input = discord.ui.TextInput(label="별점(1~5)", required=True, max_length=1)
    content_input = discord.ui.TextInput(label="후기 내용", style=discord.TextStyle.paragraph, required=True, max_length=500)
    def __init__(self, owner_id:int, product_name:str, category:str):
        super().__init__(); self.owner_id=owner_id; self.category=category; self.product_name=product_name; self.product_input.default=product_name
    async def on_submit(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        s=str(self.stars_input.value).strip()
        if not s.isdigit() or not (1<=int(s)<=5):
            await it.response.send_message("별점은 1~5 숫자로 입력해줘.", ephemeral=True); return
        p = prod_get(str(self.product_input.value).strip(), self.category)
        if p:
            p.setdefault("ratings", []).append(int(s)); db_save()
        e = emb_review_full(it.user, self.product_name, int(s), str(self.content_input.value))
        try: await send_log_embed(it.guild, "review", e)
        except: pass
        await it.response.send_message("후기 고마워!", ephemeral=True)

class QuantityModal(discord.ui.Modal, title="수량 입력"):
    qty_input = discord.ui.TextInput(label="구매 수량", required=True, max_length=6)
    def __init__(self, owner_id:int, category:str, product_name:str, origin_msg_id:int):
        super().__init__(); self.owner_id=owner_id; self.category=category; self.product_name=product_name; self.origin_msg_id=origin_msg_id
    async def on_submit(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        s=str(self.qty_input.value).strip()
        if not s.isdigit() or int(s)<=0:
            await it.response.send_message("수량은 1 이상의 숫자여야 해.", ephemeral=True); return
        qty=int(s); p=prod_get(self.product_name, self.category)
        if not p:
            await it.response.send_message("유효하지 않은 제품입니다.", ephemeral=True); return
        if p["stock"]<qty:
            embed_no=discord.Embed(title="재고 부족", description=f"{self.product_name} 재고가 부족합니다.", color=ORANGE)
            set_footer_bot(embed_no)
            try: await it.response.edit_message(embed=embed_no, view=None)
            except discord.InteractionResponded:
                try: await it.followup.edit_message(message_id=self.origin_msg_id, embed=embed_no, view=None)
                except: pass
            return
        taken=[]; cnt=qty
        while cnt>0 and p["items"]:
            taken.append(p["items"].pop(0)); cnt-=1
        p["stock"]-=qty; p["sold_count"]+=qty; db_save()
        bal_sub(it.guild.id, it.user.id, p["price"]*qty)
        try:
            dm=await it.user.create_dm()
            await dm.send(embed=emb_purchase_dm(self.product_name, qty, p["price"], taken))
        except: pass
        try: await send_log_embed(it.guild, "purchase", emb_purchase_log(it.user, self.product_name, qty))
        except: pass
        embed_ok=discord.Embed(title="구매 완료", description=f"{self.product_name} 구매가 완료되었습니다. DM을 확인해주세요.", color=GREEN)
        set_footer_bot(embed_ok)
        try: await it.response.edit_message(embed=embed_ok, view=None)
        except discord.InteractionResponded:
            try: await it.followup.edit_message(message_id=self.origin_msg_id, embed=embed_ok, view=None)
            except: pass

class ProductSelect(discord.ui.Select):
    def __init__(self, owner_id:int, category:str, origin_msg_id:int):
        prods=prod_list_by_cat(category)
        if prods:
            opts=[]
            for p in prods[:25]:
                opt={"label":p["name"], "value":p["name"], "description":product_desc_line(p)}
                em=safe_emoji(p.get("emoji_raw"))
                if em: opt["emoji"]=em
                opts.append(discord.SelectOption(**opt))
        else:
            opts=[discord.SelectOption(label="해당 카테고리에 제품이 없습니다", value="__none__")]
        super().__init__(placeholder="제품을 선택하세요", min_values=1, max_values=1, options=opts, custom_id=f"prod_sel_{owner_id}")
        self.owner_id=owner_id; self.category=category; self.origin_msg_id=origin_msg_id
    async def callback(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
        val=self.values[0]
        if val=="__none__":
            await it.response.send_message("먼저 제품을 추가해주세요.", ephemeral=True); return
        await it.response.send_modal(QuantityModal(self.owner_id, self.category, val, self.origin_msg_id))

class BuyFlowView(discord.ui.View):
    def __init__(self, owner_id:int, category:str, origin_msg_id:int):
        super().__init__(timeout=None); self.add_item(ProductSelect(owner_id, category, origin_msg_id))

class CategorySelectForBuy(discord.ui.Select):
    def __init__(self, owner_id:int, origin_msg_id:int):
        cats=DB["categories"]
        if cats:
            opts=[]
            for c in cats[:25]:
                opt={"label":c["name"], "value":c["name"], "description":(c.get("desc")[:80] if c.get("desc") else None)}
                em=safe_emoji(c.get("emoji_raw"))
                if em: opt["emoji"]=em
                opts.append(discord.SelectOption(**opt))
        else:
            opts=[discord.SelectOption(label="등록된 카테고리가 없습니다", value="__none__")]
        super().__init__(placeholder="카테고리를 선택하세요", min_values=1, max_values=1, options=opts, custom_id=f"cat_buy_{owner_id}")
        self.owner_id=owner_id; self.origin_msg_id=origin_msg_id
    async def callback(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
        val=self.values[0]
        if val=="__none__":
            await it.response.send_message("먼저 카테고리를 추가해주세요.", ephemeral=True); return
        embed=discord.Embed(title="제품 선택하기", description=f"{val} 카테고리의 제품을 선택해주세요", color=GRAY)
        set_footer_bot(embed)
        view=BuyFlowView(self.owner_id, val, self.origin_msg_id)
        try: await it.response.edit_message(embed=embed, view=view)
        except discord.InteractionResponded:
            try: await it.followup.edit_message(message_id=self.origin_msg_id, embed=embed, view=view)
            except: pass

class CategorySelectForBuyView(discord.ui.View):
    def __init__(self, owner_id:int, origin_msg_id:int):
        super().__init__(timeout=None); self.add_item(CategorySelectForBuy(owner_id, origin_msg_id))

# ===== 결제(충전신청) =====
class PaymentModal(discord.ui.Modal, title="충전 신청"):
    amount_input = discord.ui.TextInput(label="충전할 금액", required=True, max_length=12)
    depositor_input = discord.ui.TextInput(label="입금자명", required=True, max_length=20)
    def __init__(self, owner_id:int):
        super().__init__(); self.owner_id=owner_id
    async def on_submit(self, it: discord.Interaction):
        try:
            amt_raw=str(self.amount_input.value).strip().replace(",", "")
            amt=int(amt_raw) if amt_raw.isdigit() else 0
            depos=str(self.depositor_input.value).strip()
            if amt>0 and depos:
                DB["topups"]["requests"].append({
                    "guildId": it.guild.id, "userId": it.user.id,
                    "amount": amt, "depositor": depos,
                    "ts": _now(), "status": "pending"
                }); db_save()
        except: pass
        bank=DB.get("account",{}).get("bank","미등록")
        holder=DB.get("account",{}).get("holder","미등록")
        number=DB.get("account",{}).get("number","미등록")
        amount_txt=f"{amt_raw}원" if amt_raw else "0원"
        desc = f"은행명 : {bank}\n예금주 : {holder}\n계좌번호 : `{number}`\n보내야할 금액 : {amount_txt}"
        e = discord.Embed(title="충전신청", description=desc, color=GREEN)
        set_footer_bot(e)
        await it.response.send_message(embed=e, ephemeral=True)
        # DM 안내 5분 뒤 삭제
        try:
            dm = await it.user.create_dm()
            msg = await dm.send(embed=discord.Embed(title="충전신청", description=desc, color=GREEN))
            async def _del():
                await asyncio.sleep(TOPUP_TIMEOUT_SEC)
                try: await msg.delete()
                except: pass
            asyncio.create_task(_del())
        except: pass

class PaymentMethodView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        items=[]
        if DB["payments"].get("bank", False):
            items.append(discord.ui.Button(label="계좌이체", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMOJI_TOSS)))
        if DB["payments"].get("coin", False):
            items.append(discord.ui.Button(label="코인충전", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMOJI_COIN)))
        if DB["payments"].get("culture", False):
            items.append(discord.ui.Button(label="문상충전", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMOJI_CULTURE)))
        for b in items:
            async def _cb(i:discord.Interaction, label=b.label):
                if label=="계좌이체":
                    await i.response.send_modal(PaymentModal(i.user.id))
                else:
                    e=discord.Embed(title="실패", description="현재 미지원", color=RED)
                    set_footer_bot(e)
                    await i.response.send_message(embed=e, ephemeral=True)
            b.callback=_cb
            self.add_item(b)

# ===== 내 정보(썸네일에 유저 프사, 드롭다운 5개) =====
class RecentOrdersSelect(discord.ui.Select):
    def __init__(self, owner_id:int, orders:list[dict]):
        opts=[]
        for o in orders[-5:][::-1]:
            ts = time.strftime('%Y-%m-%d %H:%M', time.localtime(o['ts']))
            opts.append(discord.SelectOption(label=f"{o['product']} x{o['qty']}", description=ts, value=f"{o['product']}||{o['qty']}||{o['ts']}"))
        if not opts:
            opts=[discord.SelectOption(label="최근 구매 없음", value="__none__", description="표시할 항목이 없습니다")]
        super().__init__(placeholder="최근 구매 내역 보기", min_values=1, max_values=1, options=opts, custom_id=f"recent_{owner_id}")
        self.owner_id=owner_id
    async def callback(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 볼 수 있어.", ephemeral=True); return
        val=self.values[0]
        if val=="__none__":
            await it.response.send_message("최근 구매가 없습니다.", ephemeral=True); return
        name, qty, ts = val.split("||")
        ts_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(int(ts)))
        e = discord.Embed(title="구매 상세", description=f"- 제품: {name}\n- 수량: {qty}\n- 시간: {ts_str}", color=GRAY)
        set_footer_bot(e)
        await it.response.send_message(embed=e, ephemeral=True)

class MyInfoView(discord.ui.View):
    def __init__(self, owner_id:int, orders:list[dict]):
        super().__init__(timeout=None); self.add_item(RecentOrdersSelect(owner_id, orders))

# ===== 버튼 패널 =====
class ButtonPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        n=discord.ui.Button(label="공지사항", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMOJI_NOTICE), row=0)
        c=discord.ui.Button(label="충전", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMOJI_CHARGE), row=0)
        i=discord.ui.Button(label="내 정보", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMOJI_TICKET), row=1)
        b=discord.ui.Button(label="구매", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMOJI_BUTY if False else EMOJI_BUY), row=1)

        async def _notice(it):
            e = discord.Embed(title="공지사항", description="서버규칙 필독 부탁드립니다\n자충 오류시 티켓 열어주세요", color=GRAY)
            set_footer_bot(e)
            await it.response.send_message(embed=e, ephemeral=True)

        async def _charge(it):
            if ban_is_blocked(it.guild.id, it.user.id):
                e=discord.Embed(title="이용 불가", description="차단 상태입니다. /유저_설정으로 해제하세요.", color=RED)
                set_footer_bot(e)
                await it.response.send_message(embed=e, ephemeral=True); return
            view = PaymentMethodView()
            if len(view.children)==0:
                e = discord.Embed(title="결제수단 선택하기", description="현재 지원되는 결제수단이 없습니다.", color=ORANGE)
                set_footer_bot(e)
                await it.response.send_message(embed=e, ephemeral=True)
            else:
                e = discord.Embed(title="결제수단 선택하기", description="원하시는 결제수단 버튼을 클릭해주세요", color=GRAY)
                set_footer_bot(e)
                await it.response.send_message(embed=e, view=view, ephemeral=True)

        async def _info(it):
            gid=it.guild.id; uid=it.user.id
            ords=orders_get(gid, uid)
            # 누적 금액/거래횟수 전건 기준
            spent = 0
            for o in ords:
                p=next((pp for pp in DB["products"] if pp["name"]==o["product"]), None)
                if p: spent += p["price"]*o["qty"]
            bal=bal_get(gid, uid); pts=pt_get(gid, uid)
            line = "ㅡ"*18
            desc = f"보유 금액 : {bal}\n누적 금액 : {spent}\n포인트 : {pts}\n거래 횟수 : {len(ords)}\n{line}\n역할등급 : 아직 없습니다\n역할혜택 : 아직 없습니다"
            e = discord.Embed(title="내 정보", description=desc, color=GRAY)
            # 썸네일에 유저 프사 노출
            try: e.set_thumbnail(url=it.user.display_avatar.url)
            except: pass
            set_footer_bot(e)
            await it.response.send_message(embed=e, view=MyInfoView(uid, ords), ephemeral=True)

        async def _buy(it):
            if ban_is_blocked(it.guild.id, it.user.id):
                e=discord.Embed(title="이용 불가", description="차단 상태입니다. /유저_설정으로 해제하세요.", color=RED)
                set_footer_bot(e)
                await it.response.send_message(embed=e, ephemeral=True); return
            e = discord.Embed(title="카테고리 선택하기", description="구매할 카테고리를 선택해주세요", color=GRAY)
            set_footer_bot(e)
            await it.response.send_message(embed=e, ephemeral=True)
            msg=await it.original_response()
            await msg.edit(view=CategorySelectForBuyView(it.user.id, msg.id))

        n.callback=_notice; c.callback=_charge; i.callback=_info; b.callback=_buy
        self.add_item(n); self.add_item(c); self.add_item(i); self.add_item(b)

# ===== 카테고리/제품/재고/로그 설정(슬래시 10개) =====
class CategoryDeleteView(discord.ui.View):
    def __init__(self, owner_id:int):
        super().__init__(timeout=None)
        class CategoryDeleteSelect(discord.ui.Select):
            def __init__(self, owner_id:int):
                cats=DB["categories"]; opts=[]
                for c in cats[:25]:
                    opt={"label":c["name"], "value":c["name"], "description":(c.get("desc")[:80] if c.get("desc") else None)}
                    em=safe_emoji(c.get("emoji_raw")); 
                    if em: opt["emoji"]=em
                    opts.append(discord.SelectOption(**opt))
                super().__init__(placeholder="삭제할 카테고리를 선택하세요", min_values=1, max_values=1, options=opts or [discord.SelectOption(label="삭제할 카테고리가 없습니다", value="__none__")], custom_id=f"cat_del_{owner_id}")
                self.owner_id=owner_id
            async def callback(self, it: discord.Interaction):
                if it.user.id!=self.owner_id:
                    await it.response.send_message("작성자만 선택할 수 있어.", ephemeral=True); return
                val=self.values[0]
                if val=="__none__":
                    await it.response.send_message("삭제할 카테고리가 없습니다.", ephemeral=True); return
                DB["categories"]=[c for c in DB["categories"] if c["name"]!=val]
                DB["products"]=[p for p in DB["products"] if p["category"]!=val]; db_save()
                e=discord.Embed(title="카테고리 삭제 완료", description=f"삭제된 카테고리: {val}", color=GRAY)
                set_footer_bot(e)
                await it.response.send_message(embed=e, ephemeral=True)
        self.add_item(CategoryDeleteSelect(owner_id))

class CategorySetupModal(discord.ui.Modal, title="카테고리 추가"):
    name_input = discord.ui.TextInput(label="카테고리 이름", required=True, max_length=60)
    desc_input = discord.ui.TextInput(label="카테고리 설명", style=discord.TextStyle.paragraph, required=False, max_length=200)
    emoji_input = discord.ui.TextInput(label="카테고리 이모지", required=False, max_length=100)
    def __init__(self, owner_id:int):
        super().__init__(); self.owner_id=owner_id
    async def on_submit(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
        name=str(self.name_input.value).strip()
        desc=str(self.desc_input.value).strip() if self.desc_input.value else ""
        emoji=str(self.emoji_input.value).strip() if self.emoji_input.value else ""
        i=next((k for k,c in enumerate(DB["categories"]) if c["name"]==name), -1)
        row={"name":name,"desc":desc,"emoji_raw":emoji}
        if i>=0: DB["categories"][i]=row
        else: DB["categories"].append(row)
        db_save()
        e=discord.Embed(title="카테고리 등록 완료", description=f"{name}\n{desc}", color=GRAY)
        set_footer_bot(e)
        await it.response.send_message(embed=e, ephemeral=True)

class ProductSetupModal(discord.ui.Modal, title="제품 추가"):
    name_input = discord.ui.TextInput(label="제품 이름", required=True, max_length=60)
    category_input = discord.ui.TextInput(label="카테고리 이름", required=True, max_length=60)
    price_input = discord.ui.TextInput(label="제품 가격(원)", required=True, max_length=10)
    emoji_input = discord.ui.TextInput(label="제품 이모지", required=False, max_length=100)
    def __init__(self, owner_id:int):
        super().__init__(); self.owner_id=owner_id
    async def on_submit(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        name=str(self.name_input.value).strip()
        cat=str(self.category_input.value).strip()
        price_s=str(self.price_input.value).strip()
        if not any(c["name"]==cat for c in DB["categories"]):
            await it.response.send_message("해당 카테고리가 존재하지 않습니다.", ephemeral=True); return
        if not price_s.isdigit():
            await it.response.send_message("가격은 숫자만 입력해줘.", ephemeral=True); return
        price=int(price_s)
        emoji=str(self.emoji_input.value).strip() if self.emoji_input.value else ""
        prod_upsert(name, cat, price, emoji)
        e=discord.Embed(title="제품 등록 완료", description=f"{name}\n카테고리: {cat}\n{product_desc_line(prod_get(name, cat))}", color=GRAY)
        set_footer_bot(e)
        await it.response.send_message(embed=e, ephemeral=True)

class ProductDeleteView(discord.ui.View):
    def __init__(self, owner_id:int):
        super().__init__(timeout=None)
        class ProductDeleteSelect(discord.ui.Select):
            def __init__(self, owner_id:int):
                prods=prod_list_all(); opts=[]
                for p in prods[:25]:
                    opt={"label":p["name"], "value":f"{p['name']}||{p['category']}", "description":product_desc_line(p)}
                    em=safe_emoji(p.get("emoji_raw"))
                    if em: opt["emoji"]=em
                    opts.append(discord.SelectOption(**opt))
                super().__init__(placeholder="삭제할 제품을 선택하세요", min_values=1, max_values=1, options=opts or [discord.SelectOption(label="삭제할 제품이 없습니다", value="__none__")], custom_id=f"prod_del_{owner_id}")
                self.owner_id=owner_id
            async def callback(self, it: discord.Interaction):
                if it.user.id!=self.owner_id:
                    await it.response.send_message("작성자만 선택할 수 있어.", ephemeral=True); return
                val=self.values[0]
                if val=="__none__":
                    await it.response.send_message("삭제할 제품이 없습니다.", ephemeral=True); return
                name,cat=val.split("||",1)
                prod_delete(name, cat)
                e=discord.Embed(title="제품 삭제 완료", description=f"삭제된 제품: {name} (카테고리: {cat})", color=GRAY)
                set_footer_bot(e)
                await it.response.send_message(embed=e, ephemeral=True)
        self.add_item(ProductDeleteSelect(owner_id))

# ===== 슬래시 명령어 10개 =====
class ControlCog(commands.Cog):
    def __init__(self, bot_:commands.Bot):
        self.bot=bot_

    @app_commands.command(name="버튼패널", description="버튼 패널을 표시합니다.")
    @app_commands.guilds(GUILD)
    async def 버튼패널(self, it: discord.Interaction):
        e=discord.Embed(title="윈드 OTT", description="아래 버튼으로 이용해주세요!", color=GRAY)
        set_footer_bot(e)
        await it.response.send_message(embed=e, view=ButtonPanel())

    @app_commands.command(name="카테고리_설정", description="구매 카테고리를 설정합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 카테고리_설정(self, it:discord.Interaction):
        view=discord.ui.View(timeout=None)
        class Root(discord.ui.Select):
            def __init__(self, owner_id:int):
                super().__init__(placeholder="카테고리 설정하기", min_values=1, max_values=1,
                                 options=[discord.SelectOption(label="카테고리 추가", value="add"),
                                          discord.SelectOption(label="카테고리 삭제", value="del")],
                                 custom_id=f"cat_root_{owner_id}")
                self.owner_id=owner_id
            async def callback(self, inter:discord.Interaction):
                if inter.user.id!=self.owner_id:
                    await inter.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
                if self.values[0]=="add":
                    await inter.response.send_modal(CategorySetupModal(self.owner_id))
                else:
                    e=discord.Embed(title="카테고리 삭제", description="삭제할 카테고리를 선택하세요.", color=GRAY)
                    set_footer_bot(e)
                    await inter.response.send_message(embed=e, view=CategoryDeleteView(self.owner_id), ephemeral=True)
        view.add_item(Root(it.user.id))
        e=discord.Embed(title="카테고리 설정하기", description="카테고리 설정해주세요", color=GRAY)
        set_footer_bot(e)
        await it.response.send_message(embed=e, view=view, ephemeral=True)

    @app_commands.command(name="제품_설정", description="제품을 추가/삭제로 관리합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 제품_설정(self, it:discord.Interaction):
        view=discord.ui.View(timeout=None)
        class Root(discord.ui.Select):
            def __init__(self, owner_id:int):
                super().__init__(placeholder="제품 설정하기", min_values=1, max_values=1,
                                 options=[discord.SelectOption(label="제품 추가", value="add"),
                                          discord.SelectOption(label="제품 삭제", value="del")],
                                 custom_id=f"prod_root_{owner_id}")
                self.owner_id=owner_id
            async def callback(self, inter:discord.Interaction):
                if inter.user.id!=self.owner_id:
                    await inter.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
                if self.values[0]=="add":
                    await inter.response.send_modal(ProductSetupModal(self.owner_id))
                else:
                    e=discord.Embed(title="제품 삭제", description="삭제할 제품을 선택하세요.", color=GRAY)
                    set_footer_bot(e)
                    await inter.response.send_message(embed=e, view=ProductDeleteView(self.owner_id), ephemeral=True)
        view.add_item(Root(it.user.id))
        e=discord.Embed(title="제품 설정하기", description="제품 설정해주세요", color=GRAY)
        set_footer_bot(e)
        await it.response.send_message(embed=e, view=view, ephemeral=True)

    @app_commands.command(name="재고_설정", description="제품 재고를 추가합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 재고_설정(self, it:discord.Interaction):
        class StockSel(discord.ui.Select):
            def __init__(self, owner_id:int):
                prods=prod_list_all()
                if prods:
                    opts=[]
                    for p in prods[:25]:
                        opt={"label":f"{p['name']} ({p['category']})", "value":f"{p['name']}||{p['category']}", "description":product_desc_line(p)}
                        em=safe_emoji(p.get("emoji_raw")); 
                        if em: opt["emoji"]=em
                        opts.append(discord.SelectOption(**opt))
                else:
                    opts=[discord.SelectOption(label="등록된 제품이 없습니다", value="__none__")]
                super().__init__(placeholder="재고를 설정할 제품을 선택", min_values=1, max_values=1, options=opts, custom_id=f"stock_prod_{owner_id}")
                self.owner_id=owner_id
            async def callback(self, inter:discord.Interaction):
                if inter.user.id!=self.owner_id:
                    await inter.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
                val=self.values[0]
                if val=="__none__":
                    await inter.response.send_message("먼저 제품을 추가해주세요.", ephemeral=True); return
                name,cat=val.split("||",1)
                await inter.response.send_modal(StockAddModal(self.owner_id, name, cat))
        view=discord.ui.View(timeout=None); view.add_item(StockSel(it.user.id))
        e=discord.Embed(title="재고 설정하기", description="재고 설정해주세요", color=GRAY)
        set_footer_bot(e)
        await it.response.send_message(embed=e, view=view, ephemeral=True)

    @app_commands.command(name="로그_설정", description="구매로그/구매후기/관리자로그 채널을 설정합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 로그_설정(self, it:discord.Interaction):
        class LogChannelIdModal(discord.ui.Modal, title="로그 채널 설정"):
            channel_id_input = discord.ui.TextInput(label="채널 ID", required=True, max_length=25)
            def __init__(self, owner_id:int, log_key:str):
                super().__init__(); self.owner_id=owner_id; self.log_key=log_key
            async def on_submit(self, inter:discord.Interaction):
                if inter.user.id!=self.owner_id:
                    await inter.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
                raw=str(self.channel_id_input.value).strip()
                if not raw.isdigit():
                    e=discord.Embed(title="실패", description="채널 ID는 숫자여야 합니다.", color=RED)
                    set_footer_bot(e)
                    await inter.response.send_message(embed=e, ephemeral=True); return
                ch=inter.guild.get_channel(int(raw))
                if not isinstance(ch, discord.TextChannel):
                    e=discord.Embed(title="실패", description="유효한 텍스트 채널 ID가 아닙니다.", color=RED)
                    set_footer_bot(e)
                    await inter.response.send_message(embed=e, ephemeral=True); return
                DB["logs"].setdefault(self.log_key, {"enabled": False, "target_channel_id": None})
                DB["logs"][self.log_key]["target_channel_id"]=int(raw)
                DB["logs"][self.log_key]["enabled"]=True; db_save()
                pretty={"purchase":"구매로그","review":"구매후기","admin":"관리자로그"}[self.log_key]
                e=discord.Embed(title=f"{pretty} 채널 지정 완료", description=f"목적지: {ch.mention}", color=GRAY)
                set_footer_bot(e)
                await inter.response.send_message(embed=e, ephemeral=True)
        class Root(discord.ui.Select):
            def __init__(self, owner_id:int):
                options=[discord.SelectOption(label="구매로그 설정", value="purchase"),
                         discord.SelectOption(label="구매후기 설정", value="review"),
                         discord.SelectOption(label="관리자로그 설정", value="admin")]
                super().__init__(placeholder="설정할 로그 유형 선택", min_values=1, max_values=1, options=options, custom_id=f"log_root_{owner_id}")
                self.owner_id=owner_id
            async def callback(self, inter:discord.Interaction):
                if inter.user.id!=self.owner_id:
                    await inter.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
                await inter.response.send_modal(LogChannelIdModal(self.owner_id, self.values[0]))
        view=discord.ui.View(timeout=None); view.add_item(Root(it.user.id))
        e=discord.Embed(title="로그 설정하기", description="로그 설정해주세요", color=GRAY)
        set_footer_bot(e)
        await it.response.send_message(embed=e, view=view, ephemeral=True)

    @app_commands.command(name="잔액_설정", description="유저 잔액을 추가/차감합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    @app_commands.describe(유저="대상 유저", 금액="정수 금액", 여부="추가/차감")
    @app_commands.choices(여부=[app_commands.Choice(name="추가", value="추가"),
                               app_commands.Choice(name="차감", value="차감")])
    async def 잔액_설정(self, it:discord.Interaction, 유저:discord.Member, 금액:int, 여부:app_commands.Choice[str]):
        if 금액<0:
            await it.response.send_message("금액은 음수가 될 수 없어.", ephemeral=True); return
        gid=it.guild.id; uid=유저.id; prev=bal_get(gid, uid)
        if 여부.value=="차감":
            bal_sub(gid, uid, 금액); after=bal_get(gid, uid); color=RED; title=f"{유저} 금액 차감"
        else:
            bal_add(gid, uid, 금액); after=bal_get(gid, uid); color=GREEN; title=f"{유저} 금액 추가"
        e=discord.Embed(title=title, description=f"원래 금액 : {prev}\n변경 금액 : {금액}\n변경 후 금액 : {after}", color=color)
        set_footer_bot(e)
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
    async def 결제수단_설정(self, it:discord.Interaction,
                        계좌이체:app_commands.Choice[str],
                        코인충전:app_commands.Choice[str],
                        문상충전:app_commands.Choice[str]):
        DB["payments"]["bank"] = (계좌이체.value == "지원")
        DB["payments"]["coin"] = (코인충전.value == "지원")
        DB["payments"]["culture"] = (문상충전.value == "지원")
        db_save()
        e=discord.Embed(title="결제수단 설정 완료",
                        description=f"계좌이체: {계좌이체.value}\n코인충전: {코인충전.value}\n문상충전: {문상충전.value}",
                        color=GRAY)
        set_footer_bot(e)
        await it.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="계좌번호_설정", description="은행명/계좌번호/예금주를 설정합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 계좌번호_설정(self, it:discord.Interaction):
        await it.response.send_modal(AccountSetupModal(it.user.id))

    @app_commands.command(name="유저_설정", description="유저 차단/차단풀기")
    @app_commands.guilds(GUILD)
    @is_admin()
    @app_commands.describe(유저="대상 유저", 여부="차단하기/차단풀기")
    @app_commands.choices(여부=[app_commands.Choice(name="차단하기", value="ban"),
                               app_commands.Choice(name="차단풀기", value="unban")])
    async def 유저_설정(self, it:discord.Interaction, 유저:discord.Member, 여부:app_commands.Choice[str]):
        gid=str(it.guild.id); uid=str(유저.id)
        DB["bans"].setdefault(gid, {})
        if 여부.value=="ban":
            DB["bans"][gid][uid]=True; db_save()
            e=discord.Embed(title="차단하기", description=f"{유저}님은 자판기 이용 불가능합니다\n- 차단해제는 /유저_설정", color=RED)
            set_footer_bot(e)
            await it.channel.send(embed=e)
            await it.response.send_message("처리 완료", ephemeral=True)
        else:
            DB["bans"][gid].pop(uid, None); db_save()
            e=discord.Embed(title="차단풀기", description=f"{유저}님은 다시 자판기 이용 가능합니다", color=GREEN)
            set_footer_bot(e)
            await it.channel.send(embed=e)
            await it.response.send_message("처리 완료", ephemeral=True)

    @app_commands.command(name="유저_조회", description="유저 보유/누적/포인트 조회")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 유저_조회(self, it:discord.Interaction, 유저:discord.Member):
        gid=it.guild.id; uid=유저.id
        ords=orders_get(gid, uid)
        spent=0
        for o in ords:
            p=next((pp for pp in DB["products"] if pp["name"]==o["product"]), None)
            if p: spent += p["price"]*o["qty"]
        bal=bal_get(gid, uid); pts=pt_get(gid, uid)
        e=discord.Embed(title=f"{유저} 정보",
                        description=f"보유 금액 : `{bal}`\n누적 금액 : `{spent}`\n포인트 : `{pts}`\n거래 횟수 : `{len(ords)}`",
                        color=GRAY)
        set_footer_bot(e)
        await it.response.send_message(embed=e, ephemeral=True)

# ===== FastAPI 웹훅 =====
app = FastAPI()

@app.post("/kbank-webhook")
async def kbank_webhook(req: Request):
    try:
        token=(req.headers.get("Authorization") or "").replace("Bearer","").strip()
        if token!=WEBHOOK_SECRET:
            return {"ok": False, "error":"unauthorized"}
        body=await req.json()
        gid = int(body.get("guildId") or body.get("server_id") or 0)
        msg = body.get("msg")
        amount = body.get("amount")
        depositor = body.get("depositor")
        if (amount is None or depositor is None) and isinstance(msg, str):
            a,d = parse_sms(msg)
            if amount is None: amount=a
            if depositor is None: depositor=d
        if not gid:
            return {"ok": False, "error":"guild_required"}
        guild = bot.get_guild(gid)
        if not guild:
            return {"ok": False, "error":"guild_not_found"}
        if amount is None or depositor is None:
            await send_log_text(guild, "admin", f"[자동충전] 파싱 실패 msg='{str(msg)[:120]}'")
            return {"ok": False, "result":"parse_failed"}
        ok, msg2 = await handle_deposit(guild, int(amount), str(depositor))
        return {"ok": ok, "result": msg2}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT","8787")), log_level="warning")

# ===== 등록/싱크/기동 =====
async def guild_sync(b: commands.Bot):
    try:
        synced = await b.tree.sync(guild=GUILD)
        print(f"[setup_hook] 길드 싱크 완료({GUILD_ID}): {len(synced)}개")
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
