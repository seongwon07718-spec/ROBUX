import os, json, time, re, statistics
import discord
from discord import app_commands
from discord.ext import commands

# ===== 기본 =====
GUILD_ID = 1419200424636055592
GUILD = discord.Object(id=GUILD_ID)
GRAY   = discord.Color.from_str("#808080")
RED    = discord.Color.red()
GREEN  = discord.Color.green()
ORANGE = discord.Color.orange()

# 버튼 이모지
EMOJI_NOTICE = "<:Announcement:1422906665249800274>"  # 공지 버튼 교체
EMOJI_CHARGE = "<a:11845034938353746621:1421383445669613660>"
EMOJI_INFO   = "<:info:1422579514218905731>"
EMOJI_BUY    = "<:Nitro:1422614999804809226>"

# 결제수단 이모지
EMOJI_TOSS    = "<:TOSS:1421430302684745748>"
EMOJI_COIN    = "<:emoji_68:1421430304706658347>"
EMOJI_CULTURE = "<:culture:1421430797604229150>"

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== 파일 DB =====
DB_PATH = "data.json"
def _default_db():
    return {
        "categories": [],
        "products": [],
        "logs": {
            "purchase": {"enabled": False, "target_channel_id": None},
            "review":   {"enabled": False, "target_channel_id": None},
            "admin":    {"enabled": False, "target_channel_id": None},
        },
        "payments": {"bank": False, "coin": False, "culture": False},
        "balances": {},   # {guildId:{userId:int}}
        "orders":   {}    # {guildId:{userId:[{product,qty,ts}]}}
    }

def db_load():
    if not os.path.exists(DB_PATH): return _default_db()
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return _default_db()

def db_save():
    with open(DB_PATH, "w", encoding="utf-8") as f: json.dump(DB, f, ensure_ascii=False, indent=2)

DB = db_load()

# ===== 유틸 =====
CUSTOM_EMOJI_RE = re.compile(r'^<(?P<anim>a?):(?P<name>[A-Za-z0-9_]+):(?P<id>\d+)>$')
def parse_partial_emoji(text: str) -> discord.PartialEmoji | None:
    if not text: return None
    m = CUSTOM_EMOJI_RE.match(text.strip())
    if not m: return None
    return discord.PartialEmoji(
        name=m.group("name"),
        id=int(m.group("id")),
        animated=(m.group("anim") == "a")
    )

def is_admin():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.guild_permissions.manage_guild:
            return True
        await interaction.response.send_message("관리자만 사용할 수 있어.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# 별점(1~5)
def star_bar_or_none(avg: float | None) -> str:
    if avg is None: return "평점 없음"
    n = max(1, min(int(round(avg)), 5))
    return "⭐️" * n

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
    DB["products"]   = [p for p in DB["products"] if p["category"] != name]
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

def orders_get(gid: int, uid: int): return DB["orders"].get(str(gid), {}).get(str(uid), [])
def orders_add(gid: int, uid: int, product: str, qty: int):
    DB["orders"].setdefault(str(gid), {}).setdefault(str(uid), []).append(
        {"product": product, "qty": qty, "ts": int(time.time())}
    )
    db_save()

def bal_get(gid: int, uid: int) -> int:
    return DB["balances"].get(str(gid), {}).get(str(uid), 0)

def bal_set(gid: int, uid: int, val: int):
    DB["balances"].setdefault(str(gid), {})
    DB["balances"][str(gid)][str(uid)] = val
    db_save()

def bal_add(gid: int, uid: int, amt: int): bal_set(gid, uid, bal_get(gid, uid) + max(0, amt))
def bal_sub(gid: int, uid: int, amt: int): bal_set(gid, uid, bal_get(gid, uid) - max(0, amt))

# ===== 로그 전송(가드) =====
async def send_log_embed(guild: discord.Guild | None, key: str, embed: discord.Embed):
    if guild is None: return False
    cfg = DB["logs"].get(key) or {}
    if not cfg.get("enabled") or not cfg.get("target_channel_id"):
        return False
    ch = guild.get_channel(int(cfg["target_channel_id"]))
    if not isinstance(ch, discord.TextChannel): return False
    try:
        await ch.send(embed=embed)
        return True
    except Exception:
        return False

async def send_log_text(guild: discord.Guild | None, key: str, text: str):
    if guild is None: return False
    cfg = DB["logs"].get(key) or {}
    if not cfg.get("enabled") or not cfg.get("target_channel_id"):
        return False
    ch = guild.get_channel(int(cfg["target_channel_id"]))
    if not isinstance(ch, discord.TextChannel): return False
    try:
        await ch.send(text)
        return True
    except Exception:
        return False

# ===== 임베드 빌더 =====
def emb_purchase_log(user: discord.User, product: str, qty: int):
    e = discord.Embed(description=f"{user.mention}님이 {product} {qty}개 구매 감사합니다💝\n후기 작성 부탁드립니다", color=GRAY)
    e.set_footer(text="구매 시간"); e.timestamp = discord.utils.utcnow(); return e

def emb_review(product: str, stars: int, content: str):
    stars = max(1, min(stars, 5))
    stars_text = "⭐️" * stars
    line = "ㅡ" * 18
    e = discord.Embed(title="구매후기", description=f"**구매 제품** {product}\n**별점** {stars_text}\n{line}\n{content}\n{line}\n이용해주셔서 감사합니다.", color=GRAY)
    e.set_footer(text="작성 시간"); e.timestamp = discord.utils.utcnow(); return e

def emb_purchase_dm(product: str, qty: int, price: int, detail_text: str, stock_items: list[str]):
    total = int(price) * int(qty)
    line = "ㅡ" * 18
    visible = stock_items[:20]
    rest = len(stock_items) - len(visible)
    items_block = "\n".join(visible) + (f"\n외 {rest}개…" if rest > 0 else "")
    if not items_block: items_block = "표시할 항목이 없습니다"
    e = discord.Embed(title="구매 성공", description=f"제품 이름 : {product}\n구매 개수 : {qty}개\n차감 금액 : {total}원\n{line}\n구매한 제품\n{items_block}", color=GRAY)
    e.set_footer(text="구매 시간"); e.timestamp = discord.utils.utcnow(); return e

# ===== 후기/수량 모달 =====
class ReviewModal(discord.ui.Modal, title="구매 후기 작성"):
    product_input = discord.ui.TextInput(label="구매 제품", required=True, max_length=60)
    stars_input   = discord.ui.TextInput(label="별점(1~5)", required=True, max_length=1)
    content_input = discord.ui.TextInput(label="후기 내용", style=discord.TextStyle.paragraph, required=True, max_length=500)
    def __init__(self, owner_id: int, product_name: str, category: str):
        super().__init__(); self.owner_id = owner_id; self.category = category; self.product_input.default = product_name
    async def on_submit(self, it: discord.Interaction):
        try:
            if it.user.id != self.owner_id:
                await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
            product = str(self.product_input.value).strip()
            s = str(self.stars_input.value).strip()
            content = str(self.content_input.value).strip()
            if not s.isdigit():
                await it.response.send_message("별점은 1~5 사이 숫자만 입력해줘.", ephemeral=True); return
            stars = int(s)
            if stars < 1 or stars > 5:
                await it.response.send_message("별점은 1~5 사이여야 해.", ephemeral=True); return
            p = prod_get(product, self.category)
            if p:
                p["ratings"].append(stars); db_save()
            await send_log_embed(it.guild, "review", emb_review(product, stars, content))
            await it.response.send_message("후기 고마워! 채널에 공유됐어.", ephemeral=True)
        except Exception:
            # 어떤 예외여도 사용자 응답은 보장
            try:
                if not it.response.is_done():
                    await it.response.send_message("후기 접수 완료!", ephemeral=True)
            except Exception:
                pass

class ReviewOpenView(discord.ui.View):
    def __init__(self, product_name: str, category: str, owner_id: int):
        super().__init__(timeout=None)
        self.product_name = product_name; self.category = category; self.owner_id = owner_id
        btn = discord.ui.Button(label="💌 후기 작성", style=discord.ButtonStyle.secondary)
        async def _cb(i: discord.Interaction):
            if i.user.id != self.owner_id:
                await i.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
            await i.response.send_modal(ReviewModal(self.owner_id, self.product_name, self.category))
        btn.callback = _cb; self.add_item(btn)

class QuantityModal(discord.ui.Modal, title="수량 입력"):
    qty_input = discord.ui.TextInput(label="구매 수량", required=True, max_length=6)
    def __init__(self, owner_id: int, category: str, product_name: str, origin_message_id: int):
        super().__init__(); self.owner_id = owner_id; self.category = category; self.product_name = product_name; self.origin_message_id = origin_message_id
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
            embed = discord.Embed(title="재고 부족", description="재고가 부족합니다", color=ORANGE)
            await it.response.send_message(embed=embed, ephemeral=True); return

        # 재고 차감 및 판매 카운트
        taken = []
        cnt = qty
        while cnt > 0 and p["items"]:
            taken.append(p["items"].pop(0)); cnt -= 1
        p["stock"] -= qty
        p["sold_count"] += qty
        db_save()

        # 잔액 차감(음수 허용). 필요하면 부족 시 차단으로 바꿔줄게.
        bal_sub(it.guild.id, it.user.id, p["price"] * qty)

        # 로그
        await send_log_embed(it.guild, "purchase", emb_purchase_log(it.user, self.product_name, qty))

        # DM
        try:
            dm = await it.user.create_dm()
            await dm.send(embed=emb_purchase_dm(self.product_name, qty, p["price"], product_desc_line(p), taken),
                          view=ReviewOpenView(self.product_name, self.category, it.user.id))
        except Exception:
            pass

        # 같은 에페멀 메시지 → 구매 완료(초록)로 교체
        embed_done = discord.Embed(title="구매 완료", description=f"{self.product_name} 구매가 완료되었습니다.\nDM을 확인해주세요.", color=GREEN)
        try:
            # 대부분 환경에서 가능한 안전한 방법
            await it.response.edit_message(embed=embed_done, view=None)
        except discord.InteractionResponded:
            try:
                await it.followup.edit_message(message_id=self.origin_message_id, embed=embed_done, view=None)
            except Exception:
                pass

# ===== 구매 플로우(같은 에페멀에서 교체) =====
class ProductSelect(discord.ui.Select):
    def __init__(self, owner_id: int, category: str, origin_message_id: int):
        prods = prod_list_by_cat(category)
        if prods:
            opts = []
            for p in prods[:25]:
                opt = {"label": p["name"], "value": p["name"], "description": product_desc_line(p)}
                if p.get("emoji_raw"): opt["emoji"] = parse_partial_emoji(p["emoji_raw"]) or p["emoji_raw"]
                opts.append(discord.SelectOption(**opt))
        else:
            opts = [discord.SelectOption(label="해당 카테고리에 제품이 없습니다", value="__none__")]
        super().__init__(placeholder="제품을 선택하세요", min_values=1, max_values=1, options=opts, custom_id=f"prod_sel_{owner_id}")
        self.owner_id = owner_id; self.category = category; self.origin_message_id = origin_message_id
    async def callback(self, it: discord.Interaction):
        if it.user.id != self.owner_id:
            await it.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
        val = self.values[0]
        if val == "__none__":
            await it.response.send_message("먼저 제품을 추가해주세요.", ephemeral=True); return
        await it.response.send_modal(QuantityModal(self.owner_id, self.category, val, self.origin_message_id))

class BuyFlowView(discord.ui.View):
    def __init__(self, owner_id: int, category: str, origin_message_id: int):
        super().__init__(timeout=None); self.add_item(ProductSelect(owner_id, category, origin_message_id))

class CategorySelectForBuy(discord.ui.Select):
    def __init__(self, owner_id: int, origin_message_id: int):
        cats = DB["categories"]
        if cats:
            opts = []
            for c in cats[:25]:
                opt = {"label": c["name"], "value": c["name"], "description": (c["desc"][:80] if c.get("desc") else None)}
                if c.get("emoji_raw"): opt["emoji"] = parse_partial_emoji(c["emoji_raw"]) or c["emoji_raw"]
                opts.append(discord.SelectOption(**opt))
        else:
            opts = [discord.SelectOption(label="등록된 카테고리가 없습니다", value="__none__")]
        super().__init__(placeholder="카테고리를 선택하세요", min_values=1, max_values=1, options=opts, custom_id=f"cat_buy_{owner_id}")
        self.owner_id = owner_id; self.origin_message_id = origin_message_id
    async def callback(self, it: discord.Interaction):
        if it.user.id != self.owner_id:
            await it.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
        val = self.values[0]
        if val == "__none__":
            await it.response.send_message("먼저 카테고리를 추가해주세요.", ephemeral=True); return
        embed = discord.Embed(title="제품 선택하기", description=f"{val} 카테고리의 제품을 선택해주세요", color=GRAY)
        view  = BuyFlowView(self.owner_id, val, self.origin_message_id)
        try:
            await it.response.edit_message(embed=embed, view=view)
        except discord.InteractionResponded:
            await it.followup.edit_message(message_id=self.origin_message_id, embed=embed, view=view)

class CategorySelectForBuyView(discord.ui.View):
    def __init__(self, owner_id: int, origin_message_id: int):
        super().__init__(timeout=None); self.add_item(CategorySelectForBuy(owner_id, origin_message_id))

# ===== 결제수단 =====
class PaymentModal(discord.ui.Modal, title="충전 신청"):
    amount_input    = discord.ui.TextInput(label="충전할 금액", required=True, max_length=12)
    depositor_input = discord.ui.TextInput(label="입금자명",   required=True, max_length=20)
    def __init__(self, method_label: str):
        super().__init__(); self.method_label = method_label
    async def on_submit(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(title="충전 신청 접수", description=f"결제수단: {self.method_label}\n금액: {str(self.amount_input.value).strip()}원\n입금자명: {str(self.depositor_input.value).strip()}", color=GRAY), ephemeral=True)

class PaymentMethodView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        b1 = discord.ui.Button(label="계좌이체", style=discord.ButtonStyle.secondary, emoji=EMOJI_TOSS)
        b2 = discord.ui.Button(label="코인충전", style=discord.ButtonStyle.secondary, emoji=EMOJI_COIN)
        b3 = discord.ui.Button(label="문상충전", style=discord.ButtonStyle.secondary, emoji=EMOJI_CULTURE)
        async def _cb(i: discord.Interaction, label: str):
            key = {"계좌이체": "bank", "코인충전": "coin", "문상충전": "culture"}[label]
            if not DB["payments"].get(key, False):
                await i.response.send_message(embed=discord.Embed(title="실패", description="현재 미지원", color=RED), ephemeral=True); return
            await i.response.send_modal(PaymentModal(label))
        b1.callback = lambda i: _cb(i, "계좌이체")
        b2.callback = lambda i: _cb(i, "코인충전")
        b3.callback = lambda i: _cb(i, "문상충전")
        self.add_item(b1); self.add_item(b2); self.add_item(b3)

# ===== 최근 5건 드롭다운 =====
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
        n = discord.ui.Button(label="공지사항", style=discord.ButtonStyle.secondary, emoji=EMOJI_NOTICE, row=0)
        c = discord.ui.Button(label="충전",   style=discord.ButtonStyle.secondary, emoji=EMOJI_CHARGE, row=0)
        i = discord.ui.Button(label="내 정보", style=discord.ButtonStyle.secondary, emoji=EMOJI_INFO,   row=1)
        b = discord.ui.Button(label="구매",   style=discord.ButtonStyle.secondary, emoji=EMOJI_BUY,    row=1)
        async def _notice(it): await it.response.send_message(embed=discord.Embed(title="공지사항", description="서버규칙 필독 부탁드립니다\n구매후 이용후기는 필수입니다\n자충 오류시 티켓 열어주세요", color=GRAY), ephemeral=True)
        async def _charge(it): await it.response.send_message(embed=discord.Embed(title="결제수단 선택하기", description="원하시는 결제수단 버튼을 클릭해주세요", color=GRAY), view=PaymentMethodView(), ephemeral=True)
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
            sent = await it.response.send_message(embed=discord.Embed(title="카테고리 선택하기", description="구매할 카테고리를 선택해주세요", color=GRAY), ephemeral=True)
            msg = await it.original_response()
            await msg.edit(view=CategorySelectForBuyView(it.user.id, msg.id))
        n.callback = _notice; c.callback = _charge; i.callback = _info; b.callback = _buy
        self.add_item(n); self.add_item(c); self.add_item(i); self.add_item(b)

# ===== 설정/삭제/로그/재고 뷰 & 모달 =====
class LogChannelIdModal(discord.ui.Modal, title="로그 채널 설정"):
    channel_id_input = discord.ui.TextInput(label="채널 ID", required=True, max_length=25)
    def __init__(self, owner_id: int, log_key: str):
        super().__init__(); self.owner_id = owner_id; self.log_key = log_key
    async def on_submit(self, it: discord.Interaction):
        if it.user.id != self.owner_id: await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        raw = str(self.channel_id_input.value).strip()
        if not raw.isdigit(): await it.response.send_message(embed=discord.Embed(title="실패", description="채널 ID는 숫자여야 합니다.", color=RED), ephemeral=True); return
        ch = it.guild.get_channel(int(raw))
        if not isinstance(ch, discord.TextChannel): await it.response.send_message(embed=discord.Embed(title="실패", description="유효한 텍스트 채널 ID가 아닙니다.", color=RED), ephemeral=True); return
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
        if it.user.id != self.owner_id: await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        lines = [ln.strip() for ln in str(self.lines_input.value).splitlines() if ln.strip()]
        p = prod_get(self.product_name, self.category)
        if not p: await it.response.send_message("유효하지 않은 제품입니다.", ephemeral=True); return
        p["items"].extend(lines); p["stock"] += len(lines); db_save()
        await it.response.send_message(embed=discord.Embed(title="재고 추가 완료", description=f"제품: {self.product_name} ({self.category})\n추가 수량: {len(lines)}\n현재 재고: {p['stock']}", color=GRAY), ephemeral=True)

class CategorySetupModal(discord.ui.Modal, title="카테고리 추가"):
    name_input  = discord.ui.TextInput(label="카테고리 이름", required=True, max_length=60)
    desc_input  = discord.ui.TextInput(label="카테고리 설명", style=discord.TextStyle.paragraph, required=False, max_length=200)
    emoji_input = discord.ui.TextInput(label="카테고리 이모지", required=False, max_length=100)
    def __init__(self, owner_id: int): super().__init__(); self.owner_id = owner_id
    async def on_submit(self, it: discord.Interaction):
        if it.user.id != self.owner_id: await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        name  = str(self.name_input.value).strip()
        desc  = str(self.desc_input.value).strip() if self.desc_input.value else ""
        emoji = str(self.emoji_input.value).strip() if self.emoji_input.value else ""
        cat_upsert(name, desc, emoji)
        prev = str(parse_partial_emoji(emoji)) if emoji else ""
        await it.response.send_message(embed=discord.Embed(title="카테고리 등록 완료", description=f"{(prev+' ') if prev else ''}{name}\n{desc}", color=GRAY), ephemeral=True)

class CategoryDeleteSelect(discord.ui.Select):
    def __init__(self, owner_id: int):
        cats = DB["categories"]; opts = []
        for c in cats[:25]:
            opt = {"label": c["name"], "value": c["name"], "description": (c["desc"][:80] if c.get("desc") else None)}
            if c.get("emoji_raw"): opt["emoji"] = parse_partial_emoji(c["emoji_raw"]) or c["emoji_raw"]
            opts.append(discord.SelectOption(**opt))
        super().__init__(placeholder="삭제할 카테고리를 선택하세요", min_values=1, max_values=1, options=opts or [discord.SelectOption(label="삭제할 카테고리가 없습니다", value="__none__")], custom_id=f"cat_del_{owner_id}")
        self.owner_id = owner_id
    async def callback(self, it: discord.Interaction):
        if it.user.id != self.owner_id: await it.response.send_message("작성자만 선택할 수 있어.", ephemeral=True); return
        val = self.values[0]
        if val == "__none__": await it.response.send_message("삭제할 카테고리가 없습니다.", ephemeral=True); return
        cat_delete(val)
        await it.response.send_message(embed=discord.Embed(title="카테고리 삭제 완료", description=f"삭제된 카테고리: {val}", color=GRAY), ephemeral=True)

class CategoryDeleteView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None); self.add_item(CategoryDeleteSelect(owner_id))

class ProductSetupModal(discord.ui.Modal, title="제품 추가"):
    name_input     = discord.ui.TextInput(label="제품 이름", required=True, max_length=60)
    category_input = discord.ui.TextInput(label="카테고리 이름", required=True, max_length=60)
    price_input    = discord.ui.TextInput(label="제품 가격(원)", required=True, max_length=10)
    emoji_input    = discord.ui.TextInput(label="제품 이모지", required=False, max_length=100)
    def __init__(self, owner_id: int): super().__init__(); self.owner_id = owner_id
    async def on_submit(self, it: discord.Interaction):
        if it.user.id != self.owner_id: await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        name = str(self.name_input.value).strip()
        cat  = str(self.category_input.value).strip()
        ps   = str(self.price_input.value).strip()
        if not cat_exists(cat): await it.response.send_message("해당 카테고리가 존재하지 않습니다.", ephemeral=True); return
        if not ps.isdigit(): await it.response.send_message("가격은 숫자만 입력해줘.", ephemeral=True); return
        price = int(ps)
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
            if p.get("emoji_raw"): opt["emoji"] = parse_partial_emoji(p["emoji_raw"]) or p["emoji_raw"]
            opts.append(discord.SelectOption(**opt))
        super().__init__(placeholder="삭제할 제품을 선택하세요", min_values=1, max_values=1, options=opts or [discord.SelectOption(label="삭제할 제품이 없습니다", value="__none__")], custom_id=f"prod_del_{owner_id}")
        self.owner_id = owner_id
    async def callback(self, it: discord.Interaction):
        if it.user.id != self.owner_id: await it.response.send_message("작성자만 선택할 수 있어.", ephemeral=True); return
        val = self.values[0]
        if val == "__none__": await it.response.send_message("삭제할 제품이 없습니다.", ephemeral=True); return
        name, cat = val.split("||", 1)
        prod_delete(name, cat)
        await it.response.send_message(embed=discord.Embed(title="제품 삭제 완료", description=f"삭제된 제품: {name} (카테고리: {cat})", color=GRAY), ephemeral=True)

class ProductDeleteView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None); self.add_item(ProductDeleteSelect(owner_id))

# ===== 루트 셀렉트 =====
class CategoryRootSelect(discord.ui.Select):
    def __init__(self, owner_id: int):
        options = [discord.SelectOption(label="카테고리 추가", value="add"),
                   discord.SelectOption(label="카테고리 삭제", value="del")]
        super().__init__(placeholder="카테고리 설정하기", min_values=1, max_values=1, options=options, custom_id=f"cat_root_{owner_id}")
        self.owner_id = owner_id
    async def callback(self, inter: discord.Interaction):
        if inter.user.id != self.owner_id: await inter.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
        if self.values[0] == "add":
            await inter.response.send_modal(CategorySetupModal(self.owner_id))
        else:
            await inter.response.send_message(embed=discord.Embed(title="카테고리 삭제", description="삭제할 카테고리를 선택하세요.", color=GRAY), view=CategoryDeleteView(self.owner_id), ephemeral=True)

class ProductRootSelect(discord.ui.Select):
    def __init__(self, owner_id: int):
        options = [discord.SelectOption(label="제품 추가", value="add"),
                   discord.SelectOption(label="제품 삭제", value="del")]
        super().__init__(placeholder="제품 설정하기", min_values=1, max_values=1, options=options, custom_id=f"prod_root_{owner_id}")
        self.owner_id = owner_id
    async def callback(self, inter: discord.Interaction):
        if inter.user.id != self.owner_id: await inter.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
        if self.values[0] == "add":
            await inter.response.send_modal(ProductSetupModal(self.owner_id))
        else:
            await inter.response.send_message(embed=discord.Embed(title="제품 삭제", description="삭제할 제품을 선택하세요.", color=GRAY), view=ProductDeleteView(self.owner_id), ephemeral=True)

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
            async def callback(self, it: discord.Interaction):
                if it.user.id != self.owner_id: await it.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
                await it.response.send_modal(LogChannelIdModal(self.owner_id, self.values[0]))
        self.add_item(_Sel(owner_id))

class StockRootView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        class _Sel(discord.ui.Select):
            def __init__(self, owner_id: int):
                super().__init__(placeholder="재고 설정하기", min_values=1, max_values=1,
                                 options=[discord.SelectOption(label="재고 설정", value="set")],
                                 custom_id=f"stock_root_{owner_id}")
                self.owner_id = owner_id
            async def callback(self, it: discord.Interaction):
                if it.user.id != self.owner_id: await it.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
                embed = discord.Embed(title="제품 선택", description="재고를 설정할 제품을 선택해주세요", color=GRAY)
                view  = discord.ui.View(timeout=None); view.add_item(StockProductSelect(self.owner_id))
                try:
                    await it.response.edit_message(embed=embed, view=view)
                except discord.InteractionResponded:
                    await it.followup.edit_message(message_id=it.message.id, embed=embed, view=view)
        self.add_item(_Sel(owner_id))

class StockProductSelect(discord.ui.Select):
    def __init__(self, owner_id: int):
        prods = prod_list_all()
        if prods:
            opts = []
            for p in prods[:25]:
                opt = {"label": f"{p['name']} ({p['category']})", "value": f"{p['name']}||{p['category']}", "description": product_desc_line(p)}
                if p.get("emoji_raw"): opt["emoji"] = parse_partial_emoji(p["emoji_raw"]) or p["emoji_raw"]
                opts.append(discord.SelectOption(**opt))
        else:
            opts = [discord.SelectOption(label="등록된 제품이 없습니다", value="__none__")]
        super().__init__(placeholder="재고를 설정할 제품을 선택하세요", min_values=1, max_values=1, options=opts, custom_id=f"stock_prod_{owner_id}")
        self.owner_id = owner_id
    async def callback(self, it: discord.Interaction):
        if it.user.id != self.owner_id: await it.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
        val = self.values[0]
        if val == "__none__": await it.response.send_message("먼저 제품을 추가해주세요.", ephemeral=True); return
        name, cat = val.split("||", 1)
        await it.response.send_modal(StockAddModal(self.owner_id, name, cat))

# ===== 슬래시 커맨드 등록 Cog =====
class ControlCog(commands.Cog):
    def __init__(self, bot_: commands.Bot): self.bot = bot_

    @app_commands.command(name="버튼패널", description="버튼 패널을 표시합니다.")
    @app_commands.guilds(GUILD)
    async def 버튼패널(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(title="윈드 OTT", description="아래 원하시는 버튼을 눌러 이용해주세요!", color=GRAY), view=ButtonPanel())

    @app_commands.command(name="카테고리_설정", description="구매 카테고리를 설정합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 카테고리_설정(self, it: discord.Interaction):
        v = discord.ui.View(timeout=None); v.add_item(CategoryRootSelect(it.user.id))
        await it.response.send_message(embed=discord.Embed(title="카테고리 설정하기", description="카테고리 설정해주세요", color=GRAY), view=v, ephemeral=True)

    @app_commands.command(name="제품_설정", description="제품을 추가/삭제로 관리합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 제품_설정(self, it: discord.Interaction):
        v = discord.ui.View(timeout=None); v.add_item(ProductRootSelect(it.user.id))
        await it.response.send_message(embed=discord.Embed(title="제품 설정하기", description="제품 설정해주세요", color=GRAY), view=v, ephemeral=True)

    @app_commands.command(name="재고_설정", description="제품 재고를 추가합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 재고_설정(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(title="재고 설정하기", description="재고 설정해주세요", color=GRAY), view=StockRootView(it.user.id), ephemeral=True)

    @app_commands.command(name="로그_설정", description="구매로그/구매후기/관리자로그 채널을 설정합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 로그_설정(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(title="로그 설정하기", description="로그 설정해주세요", color=GRAY), view=LogRootView(it.user.id), ephemeral=True)

    @app_commands.command(name="잔액_설정", description="유저 잔액을 추가/차감합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    @app_commands.describe(유저="대상 유저", 금액="정수 금액", 여부="추가/차감")
    @app_commands.choices(여부=[app_commands.Choice(name="추가", value="추가"), app_commands.Choice(name="차감", value="차감")])
    async def 잔액_설정(self, it: discord.Interaction, 유저: discord.Member, 금액: int, 여부: app_commands.Choice[str]):
        if 금액 < 0:
            await it.response.send_message("금액은 음수가 될 수 없어.", ephemeral=True); return
        gid = it.guild.id; uid = 유저.id; prev = bal_get(gid, uid)
        if 여부.value == "차감":
            bal_sub(gid, uid, 금액); after = bal_get(gid, uid)
            e = discord.Embed(title=f"{유저} 금액 차감", description=f"원래 금액 : {prev}\n차감 할 금액 : {금액}\n차감 후 금액 : {after}", color=RED)
            e.set_footer(text="변경 시간"); e.timestamp = discord.utils.utcnow()
            await it.response.send_message(embed=e, ephemeral=True)
            await send_log_text(it.guild, "admin", f"[잔액 차감] {유저} | -{금액} → {after}")
        else:
            bal_add(gid, uid, 금액); after = bal_get(gid, uid)
            e = discord.Embed(title=f"{유저} 금액 추가", description=f"원래 금액 : {prev}\n추가 할 금액 : {금액}\n추가 후 금액 : {after}", color=GREEN)
            e.set_footer(text="변경 시간"); e.timestamp = discord.utils.utcnow()
            await it.response.send_message(embed=e, ephemeral=True)
            await send_log_text(it.guild, "admin", f"[잔액 추가] {유저} | +{금액} → {after}")

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
        DB["payments"]["bank"]    = (계좌이체.value == "지원")
        DB["payments"]["coin"]    = (코인충전.value == "지원")
        DB["payments"]["culture"] = (문상충전.value == "지원")
        db_save()
        await it.response.send_message(
            embed=discord.Embed(
                title="결제수단 설정 완료",
                description=f"{EMOJI_TOSS} 계좌이체: {계좌이체.value}\n{EMOJI_COIN} 코인충전: {코인충전.value}\n{EMOJI_CULTURE} 문상충전: {문상충전.value}",
                color=GRAY
            ),
            ephemeral=True
        )

# ===== 등록/싱크 =====
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

TOKEN = os.getenv("DISCORD_TOKEN", "여기에_토큰_넣기")
bot.run(TOKEN)
