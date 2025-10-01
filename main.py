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
GREEN = discord.Color.green()

# 버튼 이모지
EMOJI_NOTICE = "<:ticket:1422579515955085388>"
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

# ===== 유틸 =====
CUSTOM_EMOJI_RE = re.compile(r"^<(?P<anim>a?):(?P<name>[a-zA-Z0-9_]+):(?P<id>\d+)>$")
def parse_partial_emoji(text: str) -> discord.PartialEmoji | None:
    if not text: return None
    m = CUSTOM_EMOJI_RE.match(text.strip())
    if not m: return None
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
    return "⭐️"*n if n>0 else "⭐️"

# ===== 저장소: 카테고리 =====
class PurchaseCategoryStore:
    # [{name, desc, emoji_raw, emoji_obj}]
    categories: list[dict] = []
    @classmethod
    def upsert(cls, name: str, desc: str = "", emoji_text: str = ""):
        p = parse_partial_emoji(emoji_text)
        data = {"name": name, "desc": desc, "emoji_raw": emoji_text, "emoji_obj": p}
        i = next((k for k,c in enumerate(cls.categories) if c["name"]==name), -1)
        if i>=0: cls.categories[i]=data
        else: cls.categories.append(data)
    @classmethod
    def delete(cls, name: str):
        cls.categories = [c for c in cls.categories if c["name"]!=name]
    @classmethod
    def list(cls):
        return list(cls.categories)
    @classmethod
    def exists(cls, name: str)->bool:
        return any(c["name"]==name for c in cls.categories)

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
            "stock": 0,
            "emoji_raw": emoji_text,
            "emoji_obj": p,
            "ratings": [],
            "sold_count": 0
        }
        i = next((k for k,v in enumerate(cls.products) if v["name"]==name and v["category"]==category), -1)
        if i>=0: cls.products[i] = {**cls.products[i], **data}
        else: cls.products.append(data)
    @classmethod
    def delete(cls, name: str, category: str):
        cls.products = [p for p in cls.products if not (p["name"]==name and p["category"]==category)]
    @classmethod
    def list_by_category(cls, category: str):
        return [p for p in cls.products if p["category"]==category]
    @classmethod
    def get(cls, name: str, category: str)->dict|None:
        return next((p for p in cls.products if p{"name"}==name and p{"category"}==category), None)
    @classmethod
    def rating_avg(cls, product: dict)->float:
        return round(statistics.mean(product["ratings"]), 1) if product["ratings"] else 0.0

# ===== 저장소: 로그(이용/후기) =====
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
    def get(cls, gid:int)->dict:
        cls._ensure(gid); return cls.data[gid]
    @classmethod
    def set_enabled(cls, gid:int, key:str, enabled:bool):
        cls._ensure(gid); cls.data[gid][key]["enabled"]=enabled
    @classmethod
    def set_channel(cls, gid:int, key:str, ch_id:int|None):
        cls._ensure(gid); cls.data[gid][key]["target_channel_id"]=ch_id

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

# ===== 저장소: 잔액 =====
class BalanceStore:
    balances: dict[int, dict[int, int]] = {}
    @classmethod
    def _ensure(cls, gid:int):
        if gid not in cls.balances:
            cls.balances[gid] = {}
    @classmethod
    def get(cls, gid:int, uid:int)->int:
        cls._ensure(gid); return cls.balances[gid].get(uid, 0)
    @classmethod
    def add(cls, gid:int, uid:int, amount:int)->tuple[int,int,int]:
        cls._ensure(gid); prev = cls.get(gid, uid); amt = max(0, amount); after = prev + amt
        cls.balances[gid][uid] = after; return prev, amt, after
    @classmethod
    def sub(cls, gid:int, uid:int, amount:int)->tuple[int,int,int]:
        cls._ensure(gid); prev = cls.get(gid, uid); amt = max(0, amount); after = prev - amt
        cls.balances[gid][uid] = after; return prev, amt, after

# ===== 임베드 빌더 =====
def usage_embed(user: discord.User, product: str, qty: int)->discord.Embed:
    desc = f"{user.mention}님이 {product} {qty}개 구매 감사합니다💝\n후기 작성 부탁드립니다"
    e = discord.Embed(description=desc, color=GRAY)
    e.set_footer(text="구매 시간"); e.timestamp = discord.utils.utcnow(); return e

def review_embed(product: str, stars: int, content: str)->discord.Embed:
    stars_text = "⭐️"*max(0, min(stars, 10))
    line = "ㅡ"*18
    desc = f"**구매 제품** {product}\n**별점** {stars_text}\n{line}\n{content}\n{line}\n이용해주셔서 감사합니다."
    e = discord.Embed(title="구매후기", description=desc, color=GRAY)
    e.set_footer(text="작성 시간"); e.timestamp = discord.utils.utcnow(); return e

def product_desc(p: dict)->str:
    avg = ProductStore.rating_avg(p)
    return f"{p['price']}원 | 재고{p['stock']}개 | 평점{star_bar(avg)}"

def purchase_dm_embed(product: str, qty: int, price: int, detail_text: str)->discord.Embed:
    total = int(price)*int(qty)
    line = "ㅡ"*18
    desc = f"제품 이름 : {product}\n구매 개수 : {qty}개\n차감 금액 : {total}원\n{line}\n구매한 제품\n{detail_text}"
    e = discord.Embed(title="구매 성공", description=desc, color=GRAY)
    e.set_footer(text="구매 시간"); e.timestamp = discord.utils.utcnow(); return e

# ===== 구매 플로우 =====
class QuantityModal(discord.ui.Modal, title="수량 입력"):
    qty_input = discord.ui.TextInput(label="구매 수량", required=True, max_length=6)
    def __init__(self, owner_id: int, category: str, product_name: str):
        super().__init__(); self.owner_id=owner_id; self.category=category; self.product_name=product_name
    async def on_submit(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        s=str(self.qty_input.value).strip()
        if not s.isdigit() or int(s)<=0:
            await it.response.send_message("수량은 1 이상의 숫자여야 해.", ephemeral=True); return
        qty=int(s)
        prod = ProductStore.get(self.product_name, self.category)
        if not prod:
            await it.response.send_message("유효하지 않은 제품입니다.", ephemeral=True); return
        if prod["stock"] < qty:
            await it.response.send_message("재고가 부족합니다.", ephemeral=True); return

        prod["stock"] -= qty
        prod["sold_count"] += qty

        await send_log_embed(it.guild, "usage", usage_embed(it.user, self.product_name, qty))

        try:
            dm = await it.user.create_dm()
            await dm.send(embed=purchase_dm_embed(self.product_name, qty, prod["price"], product_desc(prod)),
                          view=ReviewOpenView(self.product_name, self.category, it.user.id))
        except Exception:
            pass

        await it.response.send_message(embed=discord.Embed(title="구매 완료", description=f"{self.product_name} {qty}개 구매가 처리됐습니다. DM을 확인해주세요.", color=GRAY), ephemeral=True)

class ReviewModal(discord.ui.Modal, title="구매 후기 작성"):
    product_input = discord.ui.TextInput(label="구매 제품", required=True, max_length=60)
    stars_input   = discord.ui.TextInput(label="별점(1~10)", required=True, max_length=2)
    content_input = discord.ui.TextInput(label="후기 내용", style=discord.TextStyle.paragraph, required=True, max_length=500)
    def __init__(self, owner_id: int, product_name: str, category: str):
        super().__init__(); self.owner_id=owner_id; self.category=category
        self.product_input.default = product_name
    async def on_submit(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        product=str(self.product_input.value).strip()
        stars_s=str(self.stars_input.value).strip()
        content=str(self.content_input.value).strip()
        if not stars_s.isdigit():
            await it.response.send_message("별점은 숫자(1~10)만 입력해줘.", ephemeral=True); return
        stars=int(stars_s)
        if stars<1 or stars>10:
            await it.response.send_message("별점은 1~10 사이여야 해.", ephemeral=True); return
        prod = ProductStore.get(product, self.category)
        if prod: prod["ratings"].append(stars)
        await send_log_embed(it.guild, "review", review_embed(product, stars, content))
        await it.response.send_message("후기 고마워! 채널에 공유됐어.", ephemeral=True)

class ReviewOpenView(discord.ui.View):
    def __init__(self, product_name: str, category: str, owner_id: int):
        super().__init__(timeout=None)
        self.product_name=product_name; self.category=category; self.owner_id=owner_id
        btn=discord.ui.Button(label="후기 작성하기", style=discord.ButtonStyle.secondary)
        btn.callback=self.open_review
        self.add_item(btn)
    async def open_review(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 사용할 수 있어.", ephemeral=True); return
        await it.response.send_modal(ReviewModal(self.owner_id, self.product_name, self.category))

class ProductSelect(discord.ui.Select):
    def __init__(self, owner_id:int, category:str):
        prods=ProductStore.list_by_category(category)
        if prods:
            options=[]
            for p in prods[:25]:
                opt={"label":p["name"], "value":p["name"], "description":product_desc(p)}
                if p["emoji_obj"] is not None: opt["emoji"]=p["emoji_obj"]
                elif p["emoji_raw"]:          opt["emoji"]=p["emoji_raw"]
                options.append(discord.SelectOption(**opt))
            placeholder="제품을 선택하세요"
        else:
            options=[discord.SelectOption(label="해당 카테고리에 제품이 없습니다", value="__none__")]
            placeholder="제품이 없습니다"
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, custom_id=f"prod_sel_{owner_id}")
        self.owner_id=owner_id; self.category=category
    async def callback(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
        val=self.values[0]
        if val=="__none__":
            await it.response.send_message("먼저 제품을 추가해주세요.", ephemeral=True); return
        await it.response.send_modal(QuantityModal(self.owner_id, self.category, val))

class ProductSelectView(discord.ui.View):
    def __init__(self, owner_id:int, category:str):
        super().__init__(timeout=None); self.add_item(ProductSelect(owner_id, category))

class CategorySelectForBuy(discord.ui.Select):
    def __init__(self, owner_id:int):
        cats=PurchaseCategoryStore.list()
        if cats:
            options=[]
            for c in cats[:25]:
                opt={"label":c["name"], "value":c["name"], "description":(c["desc"][:80] if c["desc"] else None)}
                if c["emoji_obj"] is not None: opt["emoji"]=c["emoji_obj"]
                elif c["emoji_raw"]:          opt["emoji"]=c["emoji_raw"]
                options.append(discord.SelectOption(**opt))
            placeholder="카테고리를 선택하세요"
        else:
            options=[discord.SelectOption(label="등록된 카테고리가 없습니다", value="__none__")]
            placeholder="카테고리가 없습니다"
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, custom_id=f"cat_buy_{owner_id}")
        self.owner_id=owner_id
    async def callback(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
        val=self.values[0]
        if val=="__none__":
            await it.response.send_message("먼저 카테고리를 추가해주세요.", ephemeral=True); return
        await it.response.send_message(embed=discord.Embed(title="제품 선택하기", description=f"{val} 카테고리의 제품을 선택해주세요", color=GRAY), view=ProductSelectView(self.owner_id, val), ephemeral=True)

class CategorySelectForBuyView(discord.ui.View):
    def __init__(self, owner_id:int):
        super().__init__(timeout=None); self.add_item(CategorySelectForBuy(owner_id))

# ===== 결제수단 =====
class PaymentModal(discord.ui.Modal, title="충전 신청"):
    amount_input    = discord.ui.TextInput(label="충전할 금액", required=True, max_length=12)
    depositor_input = discord.ui.TextInput(label="입금자명",   required=True, max_length=20)
    def __init__(self, method_label:str):
        super().__init__(); self.method_label=method_label
    async def on_submit(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(title="충전 신청 접수", description=f"결제수단: {self.method_label}\n금액: {str(self.amount_input.value).strip()}원\n입금자명: {str(self.depositor_input.value).strip()}", color=GRAY), ephemeral=True)

class PaymentMethodView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        b1=discord.ui.Button(label="계좌이체", style=discord.ButtonStyle.secondary, emoji=EMOJI_TOSS)
        b2=discord.ui.Button(label="코인충전", style=discord.ButtonStyle.secondary, emoji=EMOJI_COIN)
        b3=discord.ui.Button(label="문상충전", style=discord.ButtonStyle.secondary, emoji=EMOJI_CULTURE)
        b1.callback=lambda i: i.response.send_modal(PaymentModal("계좌이체"))
        b2.callback=lambda i: i.response.send_modal(PaymentModal("코인충전"))
        b3.callback=lambda i: i.response.send_modal(PaymentModal("문상충전"))
        self.add_item(b1); self.add_item(b2); self.add_item(b3)

# ===== 2x2 버튼 패널 =====
class ButtonPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        n=discord.ui.Button(label="공지사항", style=discord.ButtonStyle.secondary, emoji=EMOJI_NOTICE, row=0)
        c=discord.ui.Button(label="충전",   style=discord.ButtonStyle.secondary, emoji=EMOJI_CHARGE, row=0)
        i=discord.ui.Button(label="내 정보", style=discord.ButtonStyle.secondary, emoji=EMOJI_INFO,   row=1)
        b=discord.ui.Button(label="구매",   style=discord.ButtonStyle.secondary, emoji=EMOJI_BUY,    row=1)
        n.callback=self.on_notice; c.callback=self.on_charge; i.callback=self.on_info; b.callback=self.on_buy
        self.add_item(n); self.add_item(c); self.add_item(i); self.add_item(b)
    async def on_notice(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(title="공지사항", description="서버규칙 필독 부탁드립니다\n구매후 이용후기는 필수입니다\n자충 오류시 티켓 열어주세요", color=GRAY), ephemeral=True)
    async def on_charge(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(title="결제수단 선택하기", description="원하시는 결제수단 버튼을 클릭해주세요", color=GRAY), view=PaymentMethodView(), ephemeral=True)
    async def on_info(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(title="내 정보", description="보유 금액 : `예시`원\n누적 금액 : `예시`원\n거래 횟수 : `예시`번", color=GRAY), ephemeral=True)
    async def on_buy(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(title="카테고리 선택하기", description="구매할 카테고리를 선택해주세요", color=GRAY), view=CategorySelectForBuyView(it.user.id), ephemeral=True)

# ===== 로그 설정 UI =====
LOG_TYPE_LABELS = {"usage":"이용로그", "review":"이용후기"}

class LogChannelIdModal(discord.ui.Modal, title="로그 채널 설정"):
    channel_id_input = discord.ui.TextInput(label="채널 ID", required=True, max_length=25)
    def __init__(self, owner_id:int, log_key:str):
        super().__init__(); self.owner_id=owner_id; self.log_key=log_key
    async def on_submit(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 제출할 수 있어.", ephemeral=True); return
        raw=str(self.channel_id_input.value).strip()
        if not raw.isdigit():
            await it.response.send_message(embed=discord.Embed(title="실패", description="채널 ID는 숫자여야 합니다.", color=RED), ephemeral=True); return
        ch=it.guild.get_channel(int(raw))
        if not isinstance(ch, discord.TextChannel):
            await it.response.send_message(embed=discord.Embed(title="실패", description="유효한 텍스트 채널 ID가 아닙니다.", color=RED), ephemeral=True); return
        LogConfigStore.set_channel(it.guild.id, self.log_key, ch.id)
        LogConfigStore.set_enabled(it.guild.id, self.log_key, True)
        await it.response.send_message(embed=discord.Embed(title=f"{LOG_TYPE_LABELS[self.log_key]} 채널 지정 완료", description=f"목적지: {ch.mention}", color=GRAY), ephemeral=True)

class LogRootSelect(discord.ui.Select):
    def __init__(self, owner_id:int):
        options=[discord.SelectOption(label="이용로그 설정", value="usage"),
                 discord.SelectOption(label="이용후기 설정", value="review")]
        super().__init__(placeholder="설정할 로그 유형을 선택하세요", min_values=1, max_values=1, options=options, custom_id=f"log_root_{owner_id}")
        self.owner_id=owner_id
    async def callback(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True); return
        await it.response.send_modal(LogChannelIdModal(self.owner_id, self.values[0]))

class LogRootView(discord.ui.View):
    def __init__(self, owner_id:int):
        super().__init__(timeout=None); self.add_item(LogRootSelect(owner_id))

# ===== 잔액 설정 명령 =====
def build_balance_embed(title: str, lines: list[str], color: discord.Color) -> discord.Embed:
    e = discord.Embed(title=title, description="\n".join(lines), color=color)
    e.set_footer(text="변경 시간"); e.timestamp = discord.utils.utcnow(); return e

# ===== 슬래시 커맨드 =====
class ControlCog(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot=bot_

    @app_commands.command(name="버튼패널", description="윈드 OTT 버튼 패널을 표시합니다.")
    @app_commands.guilds(GUILD)
    async def 버튼패널(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(title="윈드 OTT", description="아래 원하시는 버튼을 눌러 이용해주세요!", color=GRAY), view=ButtonPanel())

    @app_commands.command(name="카테고리_설정", description="구매 카테고리를 설정합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 카테고리_설정(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(title="카테고리 설정하기", description="카테고리 설정해주세요", color=GRAY), view=CategoryRootView(it.user.id), ephemeral=True)

    @app_commands.command(name="제품_설정", description="제품을 추가/삭제로 관리합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 제품_설정(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(title="제품 설정하기", description="제품 설정해주세요", color=GRAY), view=ProductRootView(it.user.id), ephemeral=True)

    @app_commands.command(name="로그_설정", description="이용로그/이용후기 채널을 설정합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 로그_설정(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(title="로그 설정하기", description="로그 설정해주세요", color=GRAY), view=LogRootView(it.user.id), ephemeral=True)

    @app_commands.command(name="잔액_설정", description="유저 잔액을 추가/차감합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    @app_commands.describe(유저="대상 유저", 금액="정수 금액", 여부="추가 또는 차감")
    @app_commands.choices(여부=[app_commands.Choice(name="추가", value="추가"),
                           app_commands.Choice(name="차감", value="차감")])
    async def 잔액_설정(self, it: discord.Interaction,
                    유저: discord.Member,
                    금액: int,
                    여부: app_commands.Choice[str]):
        if 금액 < 0:
            await it.response.send_message("금액은 음수가 될 수 없어.", ephemeral=True); return
        gid=it.guild.id; uid=유저.id
        if 여부.value == "차감":
            prev, amt, after = BalanceStore.sub(gid, uid, 금액)
            e = build_balance_embed(f"{유저} 금액 차감", [f"원래 금액 : {prev}", f"차감 할 금액 : {amt}", f"차감 후 금액 : {after}"], RED)
            await it.response.send_message(embed=e, ephemeral=True)
        else:
            prev, amt, after = BalanceStore.add(gid, uid, 금액)
            e = build_balance_embed(f"{유저} 금액 추가", [f"원래 금액 : {prev}", f"추가 할 금액 : {amt}", f"추가 후 금액 : {after}"], GREEN)
            await it.response.send_message(embed=e, ephemeral=True)

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
