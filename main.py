from __future__ import annotations
import os, re, asyncio, logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import discord
from discord import app_commands, PartialEmoji, Colour, Embed, Interaction, TextStyle
from discord.ext import commands

# ===== 환경 =====
DISCORD_TOKEN = (os.getenv("DISCORD_TOKEN", "") or "").strip()
TARGET_GUILD_ID = 1419200424636055592
DEFAULT_TTL_SECONDS = 1800

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("robux-bot-nodb")

# ===== 이모지(PartialEmoji) =====
E = {
    "upuoipipi": PartialEmoji(name="upuoipipi", id=1421392209089007718, animated=True),
    "thumbsuppp": PartialEmoji(name="thumbsuppp", id=1421336653389365289, animated=True),
    "list": PartialEmoji(name="list", id=1421336647303172107, animated=True),
    "warn_bell": PartialEmoji(name="YouTube_Bell", id=1421432009884172299, animated=True),
    "bank_book": PartialEmoji(name="book", id=1421336655545106572, animated=True),
    "tiny_id": PartialEmoji(name="1306285145132892180", id=1421336642828111922, animated=False),
    "info1": PartialEmoji(name="emoji1", id=1421336649656438906, animated=True),
    "ok": PartialEmoji(name="1209511710545813526", id=1421430914373779618, animated=True),
    "no": PartialEmoji(name="1257004507125121105", id=1421430917049749506, animated=True),
    "culture": PartialEmoji(name="culture", id=1421430797604229150, animated=False),
    "TOSS": PartialEmoji(name="TOSS", id=1421430302684745748, animated=False),
    "emoji_68": PartialEmoji(name="emoji_68", id=1421430304706658347, animated=False),
    "role_glass": PartialEmoji(name="glashss", id=1421392211248939079, animated=True),
    "big_id": PartialEmoji(name="11845034938353746621", id=1421383445669613660, animated=True),
    "ticket": PartialEmoji(name="ticket", id=1421383450975404085, animated=False),
    "buy_btn": PartialEmoji(name="emoji_18", id=1421388813288083486, animated=False),
    "charge_btn": PartialEmoji(name="charge", id=1421383449347887157, animated=False),
    "info_btn": PartialEmoji(name="info", id=1421383447515103302, animated=False),
    "sak": PartialEmoji(name="sakfnmasfagfamg", id=1421336645084512537, animated=True),
    "__": PartialEmoji(name="__", id=1421336651929751562, animated=True),
}
COLOR_GREY = Colour(0x2f3136)
COLOR_GREEN = Colour(0x2ecc71)
COLOR_RED = Colour(0xe74c3c)
COLOR_YELLOW = Colour(0xf1c40f)

# ===== 인메모리 저장소 =====
class InMemoryStore:
    def __init__(self):
        self.config = {"panel_channel_id": None, "panel_message_id": None, "price_per_unit": 0, "robux_per_10k": 1300}
        self.stock = 0
        self.payments = {"account_transfer": False, "crypto": False, "culture_giftcard": False}
        self.bank = {"bank": None, "number": None, "holder": None, "expire_at": None}
        self.logs = {"channel_id": None, "purchase_log_enabled": False, "review_log_enabled": False}
        self.wallets: Dict[int, Dict[str, Any]] = {}
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.topups: Dict[str, Dict[str, Any]] = {}

    def now_ts(self) -> int:
        return int(datetime.now(timezone.utc).timestamp())

    def get_wallet(self, uid: int) -> Dict[str, Any]:
        if uid not in self.wallets:
            self.wallets[uid] = {"balance": 0, "total": 0, "rank": "일반"}
        return self.wallets[uid]

    def add_balance(self, uid: int, amount: int):
        w = self.get_wallet(uid); old = w["balance"]; w["balance"] += amount; w["total"] += amount
        return old, amount, w["balance"]

    def sub_balance(self, uid: int, amount: int):
        w = self.get_wallet(uid)
        if w["balance"] < amount: raise ValueError("잔액 부족")
        old = w["balance"]; w["balance"] -= amount
        return old, amount, w["balance"]

    def add_stock(self, delta: int): self.stock += delta; return self.stock
    def sub_stock(self, delta: int):
        if self.stock < delta: raise ValueError("재고 부족")
        self.stock -= delta; return self.stock

db = InMemoryStore()

def fmt_mmss(expire_at: Optional[int]) -> str:
    if not expire_at: return "설정안됨"
    remain = max(expire_at - db.now_ts(), 0); m, s = divmod(remain, 60)
    return f"{m:02d}분 {s:02d}초 남음" if remain > 0 else "만료됨"

def make_id(prefix: str) -> str: return f"{prefix}-{int(datetime.now(timezone.utc).timestamp()*1000)}"
def bool_label(v: bool) -> str: return "허용" if v else "거부"
def mention_channel(cid: Optional[int]) -> str: return f"<#{cid}>" if cid else "미지정"

# ===== 봇 =====
intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True

class RobuxBot(commands.Bot):
    async def setup_hook(self):
        await self.add_cog(RobuxCog(self))
        try:
            tg = discord.Object(id=TARGET_GUILD_ID)
            synced = await self.tree.sync(guild=tg)
            logger.info(f"길드 싱크 완료({TARGET_GUILD_ID}): {len(synced)}개")
        except Exception as e:
            logger.warning(f"길드 싱크 실패: {e}")
        try:
            all_synced = await self.tree.sync()
            logger.info(f"글로벌 싱크 완료: {len(all_synced)}개")
        except Exception as e:
            logger.warning(f"글로벌 싱크 실패: {e}")
        logger.info("슬래시 동기화 완료 (인메모리)")

bot = RobuxBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"로그인 성공: {bot.user} ({bot.user.id})")

# ===== 패널 뷰 =====
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="공지사항", style=discord.ButtonStyle.secondary, emoji=E["ticket"], custom_id="btn_notice"))
        self.add_item(discord.ui.Button(label="로벅스 구매", style=discord.ButtonStyle.secondary, emoji=E["buy_btn"], custom_id="btn_buy"))
        self.add_item(discord.ui.Button(label="충전", style=discord.ButtonStyle.secondary, emoji=E["charge_btn"], custom_id="btn_charge"))
        self.add_item(discord.ui.Button(label="내 정보", style=discord.ButtonStyle.secondary, emoji=E["info_btn"], custom_id="btn_myinfo"))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if not interaction.response.is_done():
            try: await interaction.response.defer(ephemeral=True, thinking=False)
            except: pass
        return True

# ===== 공통 =====
async def is_admin_interaction(inter: Interaction) -> bool:
    if not inter.user or not inter.guild: return False
    member = inter.guild.get_member(inter.user.id) or await inter.guild.fetch_member(inter.user.id)
    return member.guild_permissions.administrator

async def build_panel_embed() -> Embed:
    price = int(db.config["price_per_unit"] or 0)
    stock = db.stock
    desc = f"{str(E['thumbsuppp'])} 1당 `{price}`로 설정됨\n{str(E['info1'])} 재고: `{stock}` 로벅스"
    return Embed(title="로벅스 패널", description=desc, color=COLOR_GREY)

async def update_panel_message(guild: discord.Guild):
    ch_id = db.config["panel_channel_id"]; msg_id = db.config["panel_message_id"]
    if not ch_id or not msg_id: return
    try:
        ch = guild.get_channel(ch_id) or await guild.fetch_channel(ch_id)
        msg = await ch.fetch_message(msg_id)
        await msg.edit(embed=await build_panel_embed(), view=PanelView())
    except Exception as e:
        logger.warning(f"패널 업데이트 실패: {e}")

# ===== Cog =====
class RobuxCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, inter: Interaction):
        if inter.type != discord.InteractionType.component: return
        cid = inter.data.get("custom_id")

        if cid == "btn_notice":
            emb = Embed(
                description=(
                    f"{str(E['__'])}주의사항 ( 구매전 필독 )\n"
                    f"- 로벅스 가격 변동 가능\n"
                    f"- 재고는 수시 갱신\n"
                    f"- 재고 없을 땐 구매/충전 금지\n"
                    f"- 재고 없는데 구매하면 돈만 나감"
                ),
                color=COLOR_GREY
            )
            await inter.followup.send(embed=emb, ephemeral=True); return

        if cid == "btn_myinfo":
            w = db.get_wallet(inter.user.id)
            emb = Embed(
                title=f"유저: @{inter.user.display_name}",
                description=(
                    f"{str(E['big_id'])} 남은 잔액 : `{w['balance']}`\n"
                    f"{str(E['upuoipipi'])} 누적 금액 : `{w['total']}`\n"
                    f"{str(E['role_glass'])} 역할 등급 : `{w['rank']}`\n"
                    f"구매 내역: `미구현`"
                ),
                color=COLOR_GREY
            )
            await inter.followup.send(embed=emb, ephemeral=True); return

        if cid == "btn_buy":
            try:
                await inter.response.send_modal(BuyModal())
            except:
                await inter.followup.send("모달을 열 수 없어요. 잠시 후 다시 시도해줘.", ephemeral=True)
            return

        if cid == "btn_charge":
            new_exp = db.now_ts() + DEFAULT_TTL_SECONDS
            db.bank["expire_at"] = new_exp
            bank = db.bank.get("bank") or "미설정"
            number = db.bank.get("number") or "미설정"
            holder = db.bank.get("holder") or "미설정"
            emb = Embed(
                description=(
                    f"{str(E['bank_book'])}은행명 : `{bank}`\n"
                    f"{str(E['sak'])}계좌번호 : `{number}`\n"
                    f"{str(E['tiny_id'])}예금주 : `{holder}`\n"
                    f"{str(E['info1'])}유효시간 : `{fmt_mmss(new_exp)}`\n"
                    f"-# 이 시간 내에 보내줘"
                ),
                color=COLOR_GREY
            )
            await inter.followup.send(embed=emb, ephemeral=True)
            return

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        if not isinstance(message.channel, discord.DMChannel): return

        m = re.search(r"\d+", message.content)
        if not m:
            try: await message.channel.send("수량을 숫자만 입력해서 보내줘.")
            except: pass
            return

        qty = int(m.group(0))
        try: await message.channel.send("조금만 기다려줘.")
        except: pass

        admin_ch_id = db.logs.get("channel_id")
        if not admin_ch_id:
            try: await message.channel.send("관리자 채널이 아직 설정되지 않았어.")
            except: pass
            return

        admin_ch = None
        for g in bot.guilds:
            ch = g.get_channel(admin_ch_id) or (await g.fetch_channel(admin_ch_id) if g else None)
            if ch: admin_ch = ch; break
        if not admin_ch:
            try: await message.channel.send("관리자 채널을 찾을 수 없었어.")
            except: pass
            return

        order_id = make_id("RBX")
        db.orders[order_id] = {
            "user_id": message.author.id, "roblox_name": "미기재", "method": "미기재",
            "quantity": qty, "status": "대기", "created_at": datetime.now(timezone.utc).isoformat()
        }

        emb = Embed(
            description=(f"{str(E['sak'])}로벅스 구매량 : `{qty}`\n"
                         f"{str(E['sak'])}로블록스 이름 : `미기재`\n"
                         f"{str(E['sak'])}지급방식 : `미기재`"),
            color=COLOR_GREY
        )
        view = discord.ui.View(timeout=None)

        async def approve_cb(inter: Interaction):
            try: db.sub_stock(qty)
            except ValueError:
                await inter.followup.send("재고 부족. 먼저 재고 보충해줘.", ephemeral=True); return
            db.orders[order_id]["status"] = "거래완료"
            try: await message.author.send(embed=Embed(description="확인 완료. 티켓 열고 대기해줘", color=COLOR_GREEN))
            except: pass
            emb_g = Embed(description=emb.description, color=COLOR_GREEN)
            for c in view.children:
                if isinstance(c, discord.ui.Button): c.disabled = True
            await admin_msg.edit(embed=emb_g, view=view)
            await inter.followup.send("승인 처리 완료", ephemeral=True)

        async def deny_cb(inter: Interaction):
            db.orders[order_id]["status"] = "거래불가"
            try: await message.author.send(embed=Embed(description="거부됨. 티켓으로 문의해줘", color=COLOR_RED))
            except: pass
            emb_r = Embed(description=emb.description, color=COLOR_RED)
            for c in view.children:
                if isinstance(c, discord.ui.Button): c.disabled = True
            await admin_msg.edit(embed=emb_r, view=view)
            await inter.followup.send("거부 처리 완료", ephemeral=True)

        b1 = discord.ui.Button(label="승인", style=discord.ButtonStyle.success, emoji=E["ok"])
        b2 = discord.ui.Button(label="거부", style=discord.ButtonStyle.danger, emoji=E["no"])
        b1.callback = approve_cb; b2.callback = deny_cb
        view.add_item(b1); view.add_item(b2)
        admin_msg = await admin_ch.send(embed=emb, view=view)

# ===== 모달 =====
class BuyModal(discord.ui.Modal, title="로벅스 구매"):
    def __init__(self):
        super().__init__()
        self.roblox_name = discord.ui.TextInput(label="로블록스 닉", placeholder="예) rbx_player", style=TextStyle.short, required=True, max_length=50)
        self.method = discord.ui.TextInput(label="지급방식", placeholder="예) 그룹 지급 / 코드 지급", style=TextStyle.short, required=True, max_length=30)
        self.add_item(self.roblox_name); self.add_item(self.method)

    async def on_submit(self, interaction: Interaction):
        try:
            await interaction.response.send_message(
                embed=Embed(description=f"{str(E['warn_bell'])}DM 확인해줘!", color=COLOR_YELLOW),
                ephemeral=True
            )
        except:
            if interaction.response.is_done():
                await interaction.followup.send(embed=Embed(description="DM 확인해줘!", color=COLOR_YELLOW), ephemeral=True)
        try:
            user = interaction.user
            emb = Embed(
                description=f"{str(E['sak'])}로벅스 수량을 숫자만 적어서 DM으로 보내줘\n-# 보내고 잠시만 대기",
                color=COLOR_GREY
            )
            await user.send(embed=emb)
        except discord.Forbidden:
            await interaction.followup.send("DM이 닫혀있어. DM 열고 다시 시도해줘.", ephemeral=True)
        except Exception:
            await interaction.followup.send("DM 전송 오류. 잠시 후 다시 시도해줘.", ephemeral=True)

# ===== 슬래시(전부) =====
@bot.tree.command(name="봇자판기", description="패널을 전송합니다")
async def cmd_send_panel(inter: Interaction):
    if not await is_admin_interaction(inter): await inter.response.send_message("관리자만 가능", ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    msg = await inter.channel.send(embed=await build_panel_embed(), view=PanelView())
    db.config["panel_channel_id"] = inter.channel.id; db.config["panel_message_id"] = msg.id
    await inter.followup.send("패널 전송 완료", ephemeral=True)

@bot.tree.command(name="봇자판기_패널", description="패널 임베드/버튼 전송(관리자)")
async def cmd_panel_dup(inter: Interaction):
    if not await is_admin_interaction(inter): await inter.response.send_message("관리자만 가능", ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    msg = await inter.channel.send(embed=await build_panel_embed(), view=PanelView())
    db.config["panel_channel_id"] = inter.channel.id; db.config["panel_message_id"] = msg.id
    await inter.followup.send("패널 전송 완료", ephemeral=True)

@bot.tree.command(name="가격설정", description="1당 가격(정수) 설정")
@app_commands.describe(가격="정수(소수점 불가)")
async def cmd_set_price(inter: Interaction, 가격: int):
    if not await is_admin_interaction(inter): await inter.response.send_message("관리자만 가능", ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    if 가격 < 0: await inter.followup.send("0 이상 정수만 가능", ephemeral=True); return
    db.config["price_per_unit"] = 가격
    await inter.followup.send(embed=Embed(description=f"{str(E['thumbsuppp'])}1당 `{가격}` 설정됨", color=COLOR_GREY), ephemeral=True)
    await update_panel_message(inter.guild)

@bot.tree.command(name="재고설정", description="재고 추가/차감")
@app_commands.describe(수량="1 이상 정수", 방식="추가 또는 차감")
@app_commands.choices(방식=[app_commands.Choice(name="추가", value="추가"), app_commands.Choice(name="차감", value="차감")])
async def cmd_set_stock(inter: Interaction, 수량: int, 방식: app_commands.Choice[str]):
    if not await is_admin_interaction(inter): await inter.response.send_message("관리자만 가능", ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    if 수량 < 1: await inter.followup.send("수량은 1 이상", ephemeral=True); return
    try:
        if 방식.value == "추가":
            db.add_stock(수량); emb = Embed(description=f"{str(E['thumbsuppp'])}`{수량}` 로벅스 추가", color=COLOR_GREEN)
        else:
            db.sub_stock(수량); emb = Embed(description=f"{str(E['thumbsuppp'])}`{수량}` 로벅스 차감", color=COLOR_RED)
    except ValueError:
        await inter.followup.send("재고 부족", ephemeral=True); return
    await inter.followup.send(embed=emb, ephemeral=True)
    await update_panel_message(inter.guild)

@bot.tree.command(name="유저조회", description="유저 요약 조회")
@app_commands.describe(유저="대상 유저")
async def cmd_user_info(inter: Interaction, 유저: discord.User):
    if not await is_admin_interaction(inter): await inter.response.send_message("관리자만 가능", ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    w = db.get_wallet(유저.id)
    desc = f"{str(E['big_id'])}남은 잔액:`{w['balance']}`\n\n{str(E['upuoipipi'])}누적:`{w['total']}`\n\n{str(E['role_glass'])}등급:`{w['rank']}`"
    await inter.followup.send(embed=Embed(title=f"유저: @{유저.display_name}", description=desc, color=COLOR_GREY), ephemeral=True)

@bot.tree.command(name="결제수단", description="결제수단 일괄 설정")
@app_commands.describe(계좌="허용/거부", 코인="허용/거부", 문상="허용/거부")
@app_commands.choices(계좌=[app_commands.Choice(name="허용", value="허용"), app_commands.Choice(name="거부", value="거부")])
@app_commands.choices(코인=[app_commands.Choice(name="허용", value="허용"), app_commands.Choice(name="거부", value="거부")])
@app_commands.choices(문상=[app_commands.Choice(name="허용", value="허용"), app_commands.Choice(name="거부", value="거부")])
async def cmd_payment_methods(inter: Interaction, 계좌: app_commands.Choice[str], 코인: app_commands.Choice[str], 문상: app_commands.Choice[str]):
    if not await is_admin_interaction(inter): await inter.response.send_message("관리자만 가능", ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    db.payments["account_transfer"] = (계좌.value == "허용")
    db.payments["crypto"] = (코인.value == "허용")
    db.payments["culture_giftcard"] = (문상.value == "허용")
    desc = (f"{str(E['TOSS'])}계좌이체:`{계좌.value}`\n\n{str(E['emoji_68'])}코인:`{코인.value}`\n\n{str(E['culture'])}문상:`{문상.value}`\n-# 설정 완료")
    await inter.followup.send(embed=Embed(description=desc, color=COLOR_GREY), ephemeral=True)

@bot.tree.command(name="잔액추가", description="유저 잔액 추가")
@app_commands.describe(유저="대상 유저", 금액="정수(1 이상)")
async def cmd_add_balance(inter: Interaction, 유저: discord.User, 금액: int):
    if not await is_admin_interaction(inter): await inter.response.send_message("관리자만 가능", ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    if 금액 < 1: await inter.followup.send("1 이상만 가능", ephemeral=True); return
    old, added, new = db.add_balance(유저.id, 금액)
    desc = f"금액:`{금액}`\n\n{str(E['list'])}기존:`{old}`\n\n{str(E['list'])}추가:`{added}`\n\n{str(E['list'])}이후:`{new}`"
    await inter.followup.send(embed=Embed(description=desc, color=COLOR_GREEN), ephemeral=True)

@bot.tree.command(name="잔액차감", description="유저 잔액 차감")
@app_commands.describe(유저="대상 유저", 금액="정수(1 이상)")
async def cmd_sub_balance(inter: Interaction, 유저: discord.User, 금액: int):
    if not await is_admin_interaction(inter): await inter.response.send_message("관리자만 가능", ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    if 금액 < 1: await inter.followup.send("1 이상만 가능", ephemeral=True); return
    try:
        old, sub, new = db.sub_balance(유저.id, 금액)
    except ValueError:
        await inter.followup.send("잔액 부족", ephemeral=True); return
    desc = f"금액:`{금액}`\n\n{str(E['list'])}기존:`{old}`\n\n{str(E['list'])}차감:`{sub}`\n\n{str(E['list'])}이후:`{new}`"
    await inter.followup.send(embed=Embed(description=desc, color=COLOR_RED), ephemeral=True)

@bot.tree.command(name="계좌수정", description="계좌 정보/유효시간 수정")
@app_commands.describe(은행명="은행명", 계좌번호="계좌번호", 예금주="예금주", 유효시간분="유효시간(분, 비우면 30분)")
async def cmd_edit_account(inter: Interaction, 은행명: str, 계좌번호: str, 예금주: str, 유효시간분: Optional[int] = None):
    if not await is_admin_interaction(inter): await inter.response.send_message("관리자만 가능", ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    ttl = DEFAULT_TTL_SECONDS if not 유효시간분 or 유효시간분 <= 0 else 유효시간분 * 60
    expire = db.now_ts() + ttl
    db.bank.update({"bank": 은행명.strip(), "number": 계좌번호.strip(), "holder": 예금주.strip(), "expire_at": expire})
    desc = (f"{str(E['__'])}은행명:`{은행명}`\n\n{str(E['__'])}계좌번호:`{계좌번호}`\n\n{str(E['__'])}예금주:`{예금주}`\n\n{str(E['__'])}유효시간:`{fmt_mmss(expire)}`")
    await inter.followup.send(embed=Embed(description=desc, color=COLOR_GREY), ephemeral=True)

@bot.tree.command(name="로그설정", description="이용로그/이용후기/관리자채널 설정")
@app_commands.describe(관리자채널="로그 채널", 후기로그="허용/거부", 구매로그="허용/거부")
@app_commands.choices(후기로그=[app_commands.Choice(name="허용", value="허용"), app_commands.Choice(name="거부", value="거부")])
@app_commands.choices(구매로그=[app_commands.Choice(name="허용", value="허용"), app_commands.Choice(name="거부", value="거부")])
async def cmd_log_setting(inter: Interaction, 관리자채널: discord.TextChannel, 후기로그: app_commands.Choice[str], 구매로그: app_commands.Choice[str]):
    if not await is_admin_interaction(inter): await inter.response.send_message("관리자만 가능", ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    db.logs["channel_id"] = 관리자채널.id
    db.logs["purchase_log_enabled"] = (구매로그.value == "허용")
    db.logs["review_log_enabled"] = (후기로그.value == "허용")
    desc = (f"{str(E['warn_bell'])}이용로그:`{bool_label(db.logs['purchase_log_enabled'])}`\n\n"
            f"{str(E['warn_bell'])}이용후기:`{bool_label(db.logs['review_log_enabled'])}`\n\n"
            f"{str(E['warn_bell'])}관리자채널:`{mention_channel(db.logs['channel_id'])}`\n\n-# 설정 완료")
    await inter.followup.send(embed=Embed(description=desc, color=COLOR_GREY), ephemeral=True)

@bot.tree.command(name="수익설정", description="수익/판매량 조회(표시 전용)")
async def cmd_revenue_view(inter: Interaction):
    if not await is_admin_interaction(inter): await inter.response.send_message("관리자만 가능", ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    desc = (f"{str(E['upuoipipi'])}이번주 총 `0`\n\n{str(E['upuoipipi'])}한달 총 `0`\n\n{str(E['upuoipipi'])}종합 총 `0`\n"
            f"ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ\n{str(E['upuoipipi'])}이번주 판매 `0`\n\n{str(E['upuoipipi'])}한달 판매 `0`\n\n{str(E['upuoipipi'])}종합 판매 `0`\n-# 표시용")
    await inter.followup.send(embed=Embed(description=desc, color=COLOR_GREY), ephemeral=True)

# ===== 실행 =====
def main():
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN이 비어 있어요.")
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
