import os
import re
import statistics
import discord
from discord import app_commands
from discord.ext import commands

# ===== 기본 설정 =====
GUILD_ID = 1419200424636055592
GUILD = discord.Object(id=GUILD_ID)
GRAY = discord.Color.from_str("#808080")
RED = discord.Color.red()

# 버튼 이모지
EMOJI_NOTICE = "<:ticket:1422579515955085388>"
EMOJI_CHARGE = "<a:11845034938353746621:1421383445669613660>"
EMOJI_INFO   = "<:info:1422579514218905731>"
EMOJI_BUY    = "<a:NitroPremium:1422605740530471065>"

# 결제수단 이모지
EMOJI_TOSS    = "<:TOSS:1421430302684745748>"
EMOJI_COIN    = "<:emoji_68:1421430304706658347>"
EMOJI_CULTURE = "<:culture:1421430797604229150>"

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== 유틸 =====
CUSTOM_EMOJI_RE = re.compile(r"^<(?P<anim>a?):(?P<name>[a-zA-Z0-9_]+):(?P<id>\d+)>$")
def parse_partial_emoji(text: str) -> discord.PartialEmoji | None:
    if not text:
        return None
    m = CUSTOM_EMOJI_RE.match(text.strip())
    if not m:
        return None
    return discord.PartialEmoji(name=m.group("name"), id=int(m.group("id")), animated=(m.group("anim")=="a"))

def is_admin():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.guild_permissions.manage_guild:
            return True
        if not interaction.response.is_done():
            await interaction.response.send_message("관리자만 사용할 수 있어.", ephemeral=True)
        else:
            await interaction.followup.send("관리자만 사용할 수 있어.", ephemeral=True)
        return False
    return app_commands.check(predicate)

def star_bar(avg: float) -> str:
    n = max(0, min(int(round(avg)), 10))
    return "⭐️"*n if n > 0 else "⭐️"

# ===== 저장소: 카테고리 =====
class PurchaseCategoryStore:
    # [{name, desc, emoji_raw, emoji_obj}]
    categories: list[dict] = []
    @classmethod
    def upsert(cls, name: str, desc: str = "", emoji_text: str = ""):
        p = parse_partial_emoji(emoji_text)
        data = {"name": name, "desc": desc, "emoji_raw": emoji_text, "emoji_obj": p}
        i = next((k for k,c in enumerate(cls.categories) if c["name"] == name), -1)
        if i >= 0: cls.categories[i] = data
        else: cls.categories.append(data)
    @classmethod
    def delete(cls, name: str):
        cls.categories = [c for c in cls.categories if c["name"] != name]
    @classmethod
    def list(cls):
        return list(cls.categories)
    @classmethod
    def exists(cls, name: str) -> bool:
        return any(c["name"] == name for c in cls.categories)

# ===== 저장소: 제품 =====
class ProductStore:
    # [{name, category, price, stock, emoji_raw, emoji_obj, ratings:[int], sold_count:int}]
    products: list[dict] = []
    @classmethod
    def upsert(cls, name: str, category: str, price: int, emoji_text: str = ""):
        p = parse_partial_emoji(emoji_text)
        data = {
            "name": name,
            "category": category,
            "price": int(max(0, price)),
            "stock": 0,  # 재고 입력칸 제거 → 기본 0
            "emoji_raw": emoji_text,
            "emoji_obj": p,
            "ratings": [],
            "sold_count": 0
        }
        i = next((k for k,v in enumerate(cls.products) if v["name"] == name and v["category"] == category), -1)
        if i >= 0: cls.products[i] = {**cls.products[i], **data}
        else: cls.products.append(data)
    @classmethod
    def delete(cls, name: str, category: str):
        cls.products = [p for p in cls.products if not (p["name"] == name and p["category"] == category)]
    @classmethod
    def list_by_category(cls, category: str):
        return [p for p in cls.products if p["category"] == category]
    @classmethod
    def get(cls, name: str, category: str) -> dict | None:
        return next((p for p in cls.products if p["name"] == name and p["category"] == category), None)
    @classmethod
    def rating_avg(cls, product: dict) -> float:
        import statistics
        return round(statistics.mean(product["ratings"]), 1) if product["ratings"] else 0.0

# ===== 저장소: 로그 채널 =====
class LogConfigStore:
    data: dict[int, dict] = {}
    @classmethod
    def _ensure(cls, gid:int):
        if gid not in cls.data:
            cls.data[gid] = {
                "usage":  {"enabled": False, "target_channel_id": None},
                "review": {"enabled": False, "target_channel_id": None},
            }
    @classmethod
    def get(cls, gid:int) -> dict:
        cls._ensure(gid)
        return cls.data[gid]
    @classmethod
    def set_enabled(cls, gid:int, key:str, enabled:bool):
        cls._ensure(gid)
        cls.data[gid][key]["enabled"] = enabled
    @classmethod
    def set_channel(cls, gid:int, key:str, ch_id:int|None):
        cls._ensure(gid)
        cls.data[gid][key]["target_channel_id"] = ch_id

async def send_log_embed(guild: discord.Guild, key: str, embed: discord.Embed):
    cfg = LogConfigStore.get(guild.id)[key]
    if not cfg["enabled"] or not cfg["target_channel_id"]:
        return False
    ch = guild.get_channel(cfg["target_channel_id"])
    if not isinstance(ch, discord.TextChannel):
        return False
    try:
        await ch.send(embed=embed)
        return True
    except Exception:
        return False

# ===== 임베드 빌더 =====
def build_usage_purchase_embed(user: discord.User, product: str, qty: int) -> discord.Embed:
    desc = f"{user.mention}님이 {product} {qty}개 구매 감사합니다💝\n후기 작성 부탁드립니다"
    emb = discord.Embed(description=desc, color=GRAY)
    emb.set_footer(text="구매 시간")
    emb.timestamp = discord.utils.utcnow()
    return emb

def build_review_embed(product: str, stars: int, content: str) -> discord.Embed:
    stars_text = "⭐️" * max(0, min(stars, 10))
    line = "ㅡ" * 18
    desc = f"**구매 제품** {product}\n**별점** {stars_text}\n{line}\n{content}\n{line}\n이용해주셔서 감사합니다."
    emb = discord.Embed(title="구매후기", description=desc, color=GRAY)
    emb.set_footer(text="작성 시간")
    emb.timestamp = discord.utils.utcnow()
    return emb

def product_list_desc(p: dict) -> str:
    avg = ProductStore.rating_avg(p)
    return f"{p['price']}원 | 재고{p['stock']}개 | 평점{star_bar(avg)}"

def build_purchase_dm_embed(product: str, qty: int, price: int, detail_text: str) -> discord.Embed:
    total = int(price) * int(qty)
    line = "ㅡ" * 18
    desc = f"제품 이름 : {product}\n구매 개수 : {qty}개\n차감 금액 : {total}원\n{line}\n구매한 제품\n{detail_text}"
    emb = discord.Embed(title="구매 성공", description=desc, color=GRAY)
    emb.set_footer(text="구매 시간")
    emb.timestamp = discord.utils.utcnow()
    return emb

# ===== 구매 플로우 =====
class QuantityModal(discord.ui.Modal, title="수량 입력"):
    qty_input = discord.ui.TextInput(label="구매 수량", required=True, max_length=6)
    def __init__(self, owner_id: int, category: str, product_name: str):
        super().__init__()
        self.owner_id = owner_id
        self.category = category
        self.product_name = product_name
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await (interaction.response.send_message if not interaction.response.is_done() else interaction.followup.send)("작성자만 제출할 수 있어.", ephemeral=True); return
        qty_s = str(self.qty_input.value).strip()
        if not qty_s.isdigit() or int(qty_s) <= 0:
            await (interaction.response.send_message if not interaction.response.is_done() else interaction.followup.send)("수량은 1 이상의 숫자여야 합니다.", ephemeral=True); return
        qty = int(qty_s)
        prod = ProductStore.get(self.product_name, self.category)
        if not prod:
            await (interaction.response.send_message if not interaction.response.is_done() else interaction.followup.send)("유효하지 않은 제품입니다.", ephemeral=True); return
        if prod["stock"] < qty:
            await (interaction.response.send_message if not interaction.response.is_done() else interaction.followup.send)("재고가 부족합니다.", ephemeral=True); return

        # 재고/판매 갱신
        prod["stock"] -= qty
        prod["sold_count"] += qty

        # 이용로그(공개)
        await send_log_embed(interaction.guild, "usage", build_usage_purchase_embed(interaction.user, self.product_name, qty))

        # DM 전송
        try:
            dm = await interaction.user.create_dm()
            detail = product_list_desc(prod)
            dm_embed = build_purchase_dm_embed(self.product_name, qty, prod["price"], detail)
            await dm.send(embed=dm_embed, view=ReviewOpenView(self.product_name, self.category, interaction.user.id))
        except Exception:
            pass

        await (interaction.response.send_message if not interaction.response.is_done() else interaction.followup.send)(
            embed=discord.Embed(title="구매 완료", description=f"{self.product_name} {qty}개 구매가 처리됐습니다. DM을 확인해주세요.", color=GRAY),
            ephemeral=True
        )

class ReviewModal(discord.ui.Modal, title="구매 후기 작성"):
    product_input = discord.ui.TextInput(label="구매 제품", required=True, max_length=60)
    stars_input   = discord.ui.TextInput(label="별점(1~10)", required=True, max_length=2)
    content_input = discord.ui.TextInput(label="후기 내용", style=discord.TextStyle.paragraph, required=True, max_length=500)
    def __init__(self, owner_id: int, product_name: str, category: str):
        super().__init__()
        self.owner_id = owner_id
        self.category = category
        self.product_input.default = product_name
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await (interaction.response.send_message if not interaction.response.is_done() else interaction.followup.send)("작성자만 제출할 수 있어.", ephemeral=True); return
        product = str(self.product_input.value).strip()
        stars_s = str(self.stars_input.value).strip()
        content = str(self.content_input.value).strip()
        if not stars_s.isdigit():
            await (interaction.response.send_message if not interaction.response.is_done() else interaction.followup.send)("별점은 숫자(1~10)만 입력해줘.", ephemeral=True); return
        stars = int(stars_s)
        if stars < 1 or stars > 10:
            await (interaction.response.send_message if not interaction.response.is_done() else interaction.followup.send)("별점은 1~10 사이여야 해.", ephemeral=True); return
        prod = ProductStore.get(product, self.category)
        if prod:
            prod["ratings"].append(stars)
        await send_log_embed(interaction.guild, "review", build_review_embed(product, stars, content))
        await (interaction.response.send_message if not interaction.response.is_done() else interaction.followup.send)("후기 고마워! 채널에 공유됐어.", ephemeral=True)

class ReviewOpenView(discord.ui.View):
    def __init__(self, product_name: str, category: str, owner_id: int):
        super().__init__(timeout=None)
        self.product_name = product_name
        self.category = category
        self.owner_id = owner_id
        btn = discord.ui.Button(label="후기 작성하기", style=discord.ButtonStyle.secondary, custom_id=f"review_open_{owner_id}")
        btn.callback = self.open_review
        self.add_item(btn)
    async def open_review(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
        await interaction.response.send_modal(ReviewModal(self.owner_id, self.product_name, self.category))

# ===== 구매용 셀렉트 =====
class ProductSelect(discord.ui.Select):
    def __init__(self, user_id: int, category: str):
        prods = ProductStore.list_by_category(category)
        if prods:
            options = []
            for p in prods[:25]:
                opt = {"label": p["name"], "value": p["name"], "description": product_list_desc(p)}
                if p["emoji_obj"] is not None: opt["emoji"] = p["emoji_obj"]
                elif p["emoji_raw"]:          opt["emoji"] = p["emoji_raw"]
                options.append(discord.SelectOption(**opt))
            placeholder = "제품을 선택하세요"
        else:
            options = [discord.SelectOption(label="해당 카테고리에 제품이 없습니다", value="__none__")]
            placeholder = "제품이 없습니다"
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, custom_id=f"prod_sel_{user_id}")
        self.owner_id = user_id
        self.category = category
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
        val = self.values[0]
        if val == "__none__":
            await interaction.response.send_message("먼저 제품을 추가해주세요.", ephemeral=True); return
        await interaction.response.send_modal(QuantityModal(self.owner_id, self.category, val))

class ProductSelectView(discord.ui.View):
    def __init__(self, user_id: int, category: str):
        super().__init__(timeout=None)
        self.add_item(ProductSelect(user_id, category))

class CategorySelectForBuy(discord.ui.Select):
    def __init__(self, user_id: int):
        cats = PurchaseCategoryStore.list()
        if cats:
            options = []
            for c in cats[:25]:
                opt = {"label": c["name"], "value": c["name"], "description": (c["desc"][:80] if c["desc"] else None)}
                if c["emoji_obj"] is not None: opt["emoji"] = c["emoji_obj"]
                elif c["emoji_raw"]:          opt["emoji"] = c["emoji_raw"]
                options.append(discord.SelectOption(**opt))
            placeholder = "카테고리를 선택하세요"
        else:
            options = [discord.SelectOption(label="등록된 카테고리가 없습니다", value="__none__")]
            placeholder = "카테고리가 없습니다"
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, custom_id=f"cat_buy_{user_id}")
        self.owner_id = user_id
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
        val = self.values[0]
        if val == "__none__":
            await interaction.response.send_message("먼저 카테고리를 추가해주세요.", ephemeral=True); return
        embed = discord.Embed(title="제품 선택하기", description=f"{val} 카테고리의 제품을 선택해주세요", color=GRAY)
        await interaction.response.send_message(embed=embed, view=ProductSelectView(self.owner_id, val), ephemeral=True)

class CategorySelectForBuyView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.add_item(CategorySelectForBuy(user_id))

# ===== 결제수단 =====
class PaymentModal(discord.ui.Modal, title="충전 신청"):
    amount_input    = discord.ui.TextInput(label="충전할 금액", required=True, max_length=12)
    depositor_input = discord.ui.TextInput(label="입금자명",   required=True, max_length=20)
    def __init__(self, method_label: str):
        super().__init__()
        self.method_label = method_label
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(title="충전 신청 접수", description=f"결제수단: {self.method_label}\n금액: {str(self.amount_input.value).strip()}원\n입금자명: {str(self.depositor_input.value).strip()}", color=GRAY),
            ephemeral=True
        )

class PaymentMethodView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        b1 = discord.ui.Button(label="계좌이체", style=discord.ButtonStyle.secondary, emoji=EMOJI_TOSS)
        b2 = discord.ui.Button(label="코인충전", style=discord.ButtonStyle.secondary, emoji=EMOJI_COIN)
        b3 = discord.ui.Button(label="문상충전", style=discord.ButtonStyle.secondary, emoji=EMOJI_CULTURE)
        b1.callback = lambda i: i.response.send_modal(PaymentModal("계좌이체"))
        b2.callback = lambda i: i.response.send_modal(PaymentModal("코인충전"))
        b3.callback = lambda i: i.response.send_modal(PaymentModal("문상충전"))
        self.add_item(b1); self.add_item(b2); self.add_item(b3)

# ===== 2x2 버튼 패널 =====
class ButtonPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        n = discord.ui.Button(label="공지사항", style=discord.ButtonStyle.secondary, emoji=EMOJI_NOTICE, row=0)
        c = discord.ui.Button(label="충전",   style=discord.ButtonStyle.secondary, emoji=EMOJI_CHARGE, row=0)
        i = discord.ui.Button(label="내 정보", style=discord.ButtonStyle.secondary, emoji=EMOJI_INFO,   row=1)
        b = discord.ui.Button(label="구매",   style=discord.ButtonStyle.secondary, emoji=EMOJI_BUY,    row=1)
        n.callback = self.on_notice
        c.callback = self.on_charge
        i.callback = self.on_info
        b.callback = self.on_buy
        self.add_item(n); self.add_item(c); self.add_item(i); self.add_item(b)
    async def on_notice(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(title="공지사항", description="서버규칙 필독 부탁드립니다\n구매후 이용후기는 필수입니다\n자충 오류시 티켓 열어주세요", color=GRAY),
            ephemeral=True
        )
    async def on_charge(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(title="결제수단 선택하기", description="원하시는 결제수단 버튼을 클릭해주세요", color=GRAY),
            view=PaymentMethodView(), ephemeral=True
        )
    async def on_info(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(title="내 정보", description="보유 금액 : `예시`원\n누적 금액 : `예시`원\n거래 횟수 : `예시`번", color=GRAY),
            ephemeral=True
        )
    async def on_buy(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(title="카테고리 선택하기", description="구매할 카테고리를 선택해주세요", color=GRAY),
            view=CategorySelectForBuyView(interaction.user.id), ephemeral=True
        )

# ===== 설정 UI =====
class CategorySetupModal(discord.ui.Modal, title="카테고리 추가"):
    name_input  = discord.ui.TextInput(label="카테고리 이름", required=True, max_length=60)
    desc_input  = discord.ui.TextInput(label="카테고리 설명", style=discord.TextStyle.paragraph, required=False, max_length=200)
    emoji_input = discord.ui.TextInput(label="카테고리 이모지", required=False, max_length=100)
    def __init__(self, owner_id: int):
        super().__init__()
        self.owner_id = owner_id
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        name = str(self.name_input.value).strip()
        desc = str(self.desc_input.value).strip() if self.desc_input.value else ""
        emoji= str(self.emoji_input.value).strip() if self.emoji_input.value else ""
        PurchaseCategoryStore.upsert(name, desc, emoji)
        prev = str(parse_partial_emoji(emoji)) if emoji else ""
        await interaction.response.send_message(
            embed=discord.Embed(title="카테고리 등록 완료", description=f"{(prev+' ') if prev else ''}{name}\n{desc}", color=GRAY),
            ephemeral=True
        )

class CategoryDeleteSelect(discord.ui.Select):
    def __init__(self, cats: list[dict], owner_id: int):
        opts = []
        for c in cats[:25]:
            opt = {"label": c["name"], "value": c["name"], "description": (c["desc"][:80] if c["desc"] else None)}
            if c["emoji_obj"] is not None: opt["emoji"] = c["emoji_obj"]
            elif c["emoji_raw"]:          opt["emoji"] = c["emoji_raw"]
            opts.append(discord.SelectOption(**opt))
        super().__init__(placeholder="삭제할 카테고리를 선택하세요", min_values=1, max_values=1, options=opts or [discord.SelectOption(label="삭제할 카테고리가 없습니다", value="__none__")], custom_id=f"cat_del_{owner_id}")
        self.owner_id = owner_id
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("작성자만 선택할 수 있어.", ephemeral=True); return
        val = self.values[0]
        if val == "__none__":
            await interaction.response.send_message("삭제할 카테고리가 없습니다.", ephemeral=True); return
        PurchaseCategoryStore.delete(val)
        await interaction.response.send_message(embed=discord.Embed(title="카테고리 삭제 완료", description=f"삭제된 카테고리: {val}", color=GRAY), ephemeral=True)

class CategoryDeleteView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.add_item(CategoryDeleteSelect(PurchaseCategoryStore.list(), owner_id))

class CategoryRootSelect(discord.ui.Select):
    def __init__(self, owner_id: int):
        options = [
            discord.SelectOption(label="카테고리 추가", value="add"),
            discord.SelectOption(label="카테고리 삭제", value="del"),
        ]
        super().__init__(placeholder="카테고리 설정하기", min_values=1, max_values=1, options=options, custom_id=f"cat_root_{owner_id}")
        self.owner_id = owner_id
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
        if self.values[0] == "add":
            await interaction.response.send_modal(CategorySetupModal(self.owner_id))
        else:
            await interaction.response.send_message(embed=discord.Embed(title="카테고리 삭제", description="삭제할 카테고리를 선택하세요.", color=GRAY), view=CategoryDeleteView(self.owner_id), ephemeral=True)

class CategoryRootView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.add_item(CategoryRootSelect(owner_id))

class ProductSetupModal(discord.ui.Modal, title="제품 추가"):
    name_input     = discord.ui.TextInput(label="제품 이름", required=True, max_length=60)
    category_input = discord.ui.TextInput(label="카테고리 이름", required=True, max_length=60)
    price_input    = discord.ui.TextInput(label="제품 가격(원)", required=True, max_length=10)
    emoji_input    = discord.ui.TextInput(label="제품 이모지", required=False, max_length=100)
    def __init__(self, owner_id: int):
        super().__init__()
        self.owner_id = owner_id
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        name = str(self.name_input.value).strip()
        cat  = str(self.category_input.value).strip()
        price_s = str(self.price_input.value).strip()
        if not PurchaseCategoryStore.exists(cat):
            await interaction.response.send_message("해당 카테고리가 존재하지 않습니다.", ephemeral=True); return
        if not price_s.isdigit():
            await interaction.response.send_message("가격은 숫자만 입력해줘.", ephemeral=True); return
        price = int(price_s)
        emoji = str(self.emoji_input.value).strip() if self.emoji_input.value else ""
        ProductStore.upsert(name=name, category=cat, price=price, emoji_text=emoji)
        p = parse_partial_emoji(emoji); prev = str(p) if p else emoji
        desc = f"{price}원 | 재고0개 | 평점{star_bar(0)}"
        await interaction.response.send_message(embed=discord.Embed(title="제품 등록 완료", description=f"{(prev+' ') if prev else ''}{name}\n카테고리: {cat}\n{desc}", color=GRAY), ephemeral=True)

class ProductDeleteSelect(discord.ui.Select):
    def __init__(self, owner_id: int):
        prods = ProductStore.products
        opts = []
        for p in prods[:25]:
            opt = {"label": p["name"], "value": f"{p['name']}||{p['category']}", "description": product_list_desc(p)}
            if p["emoji_obj"] is not None: opt["emoji"] = p["emoji_obj"]
            elif p["emoji_raw"]:          opt["emoji"] = p["emoji_raw"]
            opts.append(discord.SelectOption(**opt))
        super().__init__(placeholder="삭제할 제품을 선택하세요", min_values=1, max_values=1, options=opts or [discord.SelectOption(label="삭제할 제품이 없습니다", value="__none__")], custom_id=f"prod_del_{owner_id}")
        self.owner_id = owner_id
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("작성자만 선택할 수 있어.", ephemeral=True); return
        val = self.values[0]
        if val == "__none__":
            await interaction.response.send_message("삭제할 제품이 없습니다.", ephemeral=True); return
        pn, cat = val.split("||", 1)
        ProductStore.delete(pn, cat)
        await interaction.response.send_message(embed=discord.Embed(title="제품 삭제 완료", description=f"삭제된 제품: {pn} (카테고리: {cat})", color=GRAY), ephemeral=True)

class ProductDeleteView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.add_item(ProductDeleteSelect(owner_id))

class ProductRootSelect(discord.ui.Select):
    def __init__(self, owner_id: int):
        options = [
            discord.SelectOption(label="제품 추가", value="add"),
            discord.SelectOption(label="제품 삭제", value="del"),
        ]
        super().__init__(placeholder="제품 설정하기", min_values=1, max_values=1, options=options, custom_id=f"prod_root_{owner_id}")
        self.owner_id = owner_id
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
        if self.values[0] == "add":
            await interaction.response.send_modal(ProductSetupModal(self.owner_id))
        else:
            await interaction.response.send_message(embed=discord.Embed(title="제품 삭제", description="삭제할 제품을 선택하세요.", color=GRAY), view=ProductDeleteView(self.owner_id), ephemeral=True)

class ProductRootView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.add_item(ProductRootSelect(owner_id))

# ===== 슬래시 커맨드 =====
class ControlCog(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    @app_commands.command(name="버튼패널", description="윈드 OTT 버튼 패널을 표시합니다.")
    @app_commands.guilds(GUILD)
    async def 버튼패널(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(title="윈드 OTT", description="아래 원하시는 버튼을 눌러 이용해주세요!", color=GRAY), view=ButtonPanel())

    @app_commands.command(name="카테고리_설정", description="구매 카테고리를 설정합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 카테고리_설정(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(title="카테고리 설정하기", description="카테고리 설정해주세요", color=GRAY), view=CategoryRootView(interaction.user.id), ephemeral=True)

    @app_commands.command(name="제품_설정", description="제품을 추가/삭제로 관리합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 제품_설정(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(title="제품 설정하기", description="제품 설정해주세요", color=GRAY), view=ProductRootView(interaction.user.id), ephemeral=True)

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
