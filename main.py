from __future__ import annotations
import os, re, logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import discord
from discord import app_commands, PartialEmoji, Colour, Embed, Interaction, TextStyle
from discord.ext import commands

# 음성 확장 비활성화(불필요한 audioop 이슈 차단)
os.environ["DISCORD_NO_EXTENSIONS"] = "true"

# ===== 환경 =====
DISCORD_TOKEN = (os.getenv("DISCORD_TOKEN", "") or "").strip()
TARGET_GUILD_ID = 1419200424636055592
DEFAULT_TTL_SECONDS = 1800

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("robux-bot-nodb")

# ===== 이모지(원래 쓰던 것 유지) =====
E = {
    "thumbsuppp": PartialEmoji(name="thumbsuppp", id=1421336653389365289, animated=True),
    "info1": PartialEmoji(name="emoji1", id=1421336649656438906, animated=True),
    "upuoipipi": PartialEmoji(name="upuoipipi", id=1421392209089007718, animated=True),
    "ticket": PartialEmoji(name="ticket", id=1421383450975404085, animated=False),
    "buy_btn": PartialEmoji(name="emoji_18", id=1421388813288083486, animated=False),
    "charge_btn": PartialEmoji(name="charge", id=1421383449347887157, animated=False),
    "info_btn": PartialEmoji(name="info", id=1421383447515103302, animated=False),
    "bank_book": PartialEmoji(name="book", id=1421336655545106572, animated=True),
    "tiny_id": PartialEmoji(name="1306285145132892180", id=1421336642828111922, animated=False),
    "sak": PartialEmoji(name="sakfnmasfagfamg", id=1421336645084512537, animated=True),
    "warn_bell": PartialEmoji(name="YouTube_Bell", id=1421432009884172299, animated=True),
    "ok": PartialEmoji(name="1209511710545813526", id=1421430914373779618, animated=True),
    "no": PartialEmoji(name="1257004507125121105", id=1421430917049749506, animated=True),
    "role_glass": PartialEmoji(name="glashss", id=1421392211248939079, animated=True),
    "big_id": PartialEmoji(name="11845034938353746621", id=1421383445669613660, animated=True),
}
COLOR_GREY = Colour(0x2f3136)
COLOR_GREEN = Colour(0x2ecc71)
COLOR_RED = Colour(0xe74c3c)
COLOR_YELLOW = Colour(0xf1c40f)

# ===== 인메모리 저장 =====
class Store:
    def __init__(self):
        self.config = {
            "panel_channel_id": None,
            "panel_message_id": None,
            "price_per_unit": 0,
        }
        self.stock = 0
        self.recent_buyers = 0      # 구매자 수 표기
        self.weekly_sold = 0        # 주간 판매량 표기
        self.bank = {"bank": None, "number": None, "holder": None, "expire_at": None}
        self.logs = {"channel_id": None, "purchase_log_enabled": False, "review_log_enabled": False}
        self.wallets: Dict[int, Dict[str, Any]] = {}

    def now_ts(self) -> int:
        return int(datetime.now(timezone.utc).timestamp())

    def wallet(self, uid: int) -> Dict[str, Any]:
        if uid not in self.wallets:
            self.wallets[uid] = {"balance": 0, "total": 0, "rank": "일반"}
        return self.wallets[uid]

db = Store()

def fmt_mmss(expire_at: Optional[int]) -> str:
    if not expire_at: return "설정안됨"
    remain = max(expire_at - db.now_ts(), 0)
    m, s = divmod(remain, 60)
    return f"{m:02d}분 {s:02d}초 남음" if remain > 0 else "만료됨"

# ===== 봇/인텐트 =====
intents = discord.Intents.default()
intents.members = True             # 개발자 포털에서 SERVER MEMBERS INTENT ON
intents.message_content = True     # MESSAGE CONTENT INTENT ON (DM 수량 받기용)

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
        logger.info("슬래시 동기화 완료(인메모리)")

bot = RobuxBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"로그인 성공: {bot.user} ({bot.user.id})")

# ===== 패널 임베드(네가 준 원문 그대로) =====
async def build_panel_embed() -> Embed:
    price = int(db.config["price_per_unit"] or 0)
    stock = db.stock
    buyers = db.recent_buyers
    weekly = db.weekly_sold
    desc = (
        f"**{str(E['thumbsuppp'])}로벅스 가격**\n"
        f"1당 `{price if price>0 else '예시'}`로벅스\n"
        f"-# 가격은 실시간으로 시세 맞게 변동됩니다\n"
        f"ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ\n"
        f"**{str(E['info1'])}로벅스 재고**\n"
        f"`{stock if stock>0 else '예시'}` 로벅스\n"
        f"-# 재고는 1분마다 갱신됩니다\n"
        f"ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ\n"
        f"**{str(E['upuoipipi'])}로벅스 판매량**\n"
        f"구매자 : `{buyers if buyers>0 else '예시'}`명\n"
        f"이번주 총 `{weekly if weekly>0 else '예시'}`만큼 팔았습니다"
    )
    return Embed(title="로벅스 패널", description=desc, color=COLOR_GREY)

# ===== 버튼 뷰(2x2) =====
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # 1행
        self.add_item(discord.ui.Button(label="공지사항", style=discord.ButtonStyle.secondary, emoji=E["ticket"], custom_id="btn_notice", row=0))
        self.add_item(discord.ui.Button(label="로벅스 구매", style=discord.ButtonStyle.secondary, emoji=E["buy_btn"], custom_id="btn_buy", row=0))
        # 2행
        self.add_item(discord.ui.Button(label="충전", style=discord.ButtonStyle.secondary, emoji=E["charge_btn"], custom_id="btn_charge", row=1))
        self.add_item(discord.ui.Button(label="내 정보", style=discord.ButtonStyle.secondary, emoji=E["info_btn"], custom_id="btn_myinfo", row=1))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if not interaction.response.is_done():
            try: await interaction.response.defer(ephemeral=True, thinking=False)
            except: pass
        return True

# ===== 공통 =====
async def is_admin(inter: Interaction) -> bool:
    if not inter.user or not inter.guild: return False
    member = inter.guild.get_member(inter.user.id) or await inter.guild.fetch_member(inter.user.id)
    return member.guild_permissions.administrator

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
                    f"{str(E['sak'])}주의사항 ( 구매전 필독 부탁 )\n"
                    f"- 로벅스 가격은 언제든지 변동될 수 있습니다\n"
                    f"- 로벅스 재고는 1분마다 실시간으로 갱신됩니다\n"
                    f"- 재고 없을 때는 작동 안 합니다 ( 충전 하지마세요 )\n"
                    f"- 로벅스 재고 없는데 구매신청하면 돈 먹습니다"
                ),
                color=COLOR_GREY
            )
            await inter.followup.send(embed=emb, ephemeral=True); return

        if cid == "btn_myinfo":
            w = db.wallet(inter.user.id)
            emb = Embed(
                title=f"유저: @{inter.user.display_name}",
                description=(
                    f"{str(E['big_id'])} 남은 잔액 : `{w['balance']}`\n"
                    f"{str(E['upuoipipi'])} 누적 금액 : `{w['total']}`\n"
                    f"{str(E['role_glass'])} 역할 등급 : `{w['rank']}`\n"
                    f"구매 내역: 총 `미구현`번"
                ),
                color=COLOR_GREY
            )
            await inter.followup.send(embed=emb, ephemeral=True); return

        if cid == "btn_buy":
            try:
                await inter.response.send_modal(BuyModal())
            except:
                await inter.followup.send("모달을 열 수 없어요. 잠시 후 다시 시도해주세요.", ephemeral=True)
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
                    f"-# 이 시간 내에 보내셔야합니다"
                ),
                color=COLOR_GREY
            )
            await inter.followup.send(embed=emb, ephemeral=True); return

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        if not isinstance(message.channel, discord.DMChannel): return

        m = re.search(r"\d+", message.content or "")
        if not m:
            try: await message.channel.send("정확한 수량을 숫자만 입력해서 보내주세요.")
            except: pass
            return

        qty = int(m.group(0))
        try: await message.channel.send("조금만 기다려주세요.")
        except: pass

        admin_ch_id = db.logs.get("channel_id")
        if not admin_ch_id:
            try: await message.channel.send("관리자 채널이 아직 설정되지 않았어요.")
            except: pass
            return

        admin_ch = None
        for g in bot.guilds:
            ch = g.get_channel(admin_ch_id) or (await g.fetch_channel(admin_ch_id) if g else None)
            if ch: admin_ch = ch; break
        if not admin_ch:
            try: await message.channel.send("관리자 채널을 찾을 수 없어요.")
            except: pass
            return

        order_id = f"RBX-{int(datetime.now(timezone.utc).timestamp()*1000)}"
        db.recent_buyers += 1  # 구매자 수 집계(샘플)

        emb = Embed(
            description=(
                f"{str(E['sak'])}로벅스 구매량 : `{qty}`\n"
                f"{str(E['sak'])}로블록스 이름 : `미기재`\n"
                f"{str(E['sak'])}지급방식 : `미기재`"
            ),
            color=COLOR_GREY
        )
        view = discord.ui.View(timeout=None)

        async def approve_cb(inter: Interaction):
            if db.stock < qty:
                await inter.followup.send("재고가 부족합니다. 먼저 재고를 보충해주세요.", ephemeral=True); return
            db.stock -= qty
            db.weekly_sold += qty
            try: await message.author.send(embed=Embed(description="확인 완료되었습니다\n티켓 열고 대기해주세요", color=COLOR_GREEN))
            except: pass
            emb_g = Embed(description=emb.description, color=COLOR_GREEN)
            for c in view.children:
                if isinstance(c, discord.ui.Button): c.disabled = True
            await admin_msg.edit(embed=emb_g, view=view)
            await inter.followup.send("승인 처리 완료", ephemeral=True)

        async def deny_cb(inter: Interaction):
            try: await message.author.send(embed=Embed(description="거부되었습니다\n티켓으로 문의해주세요", color=COLOR_RED))
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
                embed=Embed(description=f"{str(E['warn_bell'])}DM 확인해주세요!", color=COLOR_YELLOW),
                ephemeral=True
            )
        except:
            if interaction.response.is_done():
                await interaction.followup.send(embed=Embed(description="DM 확인해주세요!", color=COLOR_YELLOW), ephemeral=True)
        try:
            user = interaction.user
            emb = Embed(
                description=f"{str(E['sak'])}로벅스 수량을 적어 보내주세요\n-# 로벅스 수량 보내주시고 조금 대기하시면 관리자가 올 것입니다",
                color=COLOR_GREY
            )
            await user.send(embed=emb)
        except discord.Forbidden:
            await interaction.followup.send("DM이 닫혀 있어 안내를 보낼 수 없어요. DM을 열어주세요.", ephemeral=True)
        except Exception:
            await interaction.followup.send("DM 전송 중 오류가 발생했어요. 잠시 후 다시 시도해주세요.", ephemeral=True)

# ===== 슬래시(이름/설명 원문 유지) =====
def admin_msg(text: str) -> str:
    return f"-# {text} ( 관리자 전용 )"

@bot.tree.command(name="재고설정", description="-# 재고 설정하기 ( 관리자 전용 )")
@app_commands.describe(수량="1 이상 정수", 방식="추가 또는 차감")
@app_commands.choices(방식=[app_commands.Choice(name="추가", value="추가"), app_commands.Choice(name="차감", value="차감")])
async def 재고설정(inter: Interaction, 수량: int, 방식: app_commands.Choice[str]):
    if not await is_admin(inter): await inter.response.send_message(admin_msg("재고 설정하기"), ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    if 수량 < 1: await inter.followup.send("수량은 1 이상 정수만 가능합니다.", ephemeral=True); return
    if 방식.value == "추가":
        db.stock += 수량
    else:
        if db.stock < 수량: await inter.followup.send("재고가 부족합니다.", ephemeral=True); return
        db.stock -= 수량
    await inter.followup.send(admin_msg("재고 설정하기"), ephemeral=True)
    await update_panel_message(inter.guild)

@bot.tree.command(name="가격설정", description="-# 가격 설정하기 ( 관리자 전용 )")
@app_commands.describe(가격="정수(소수점 불가)")
async def 가격설정(inter: Interaction, 가격: int):
    if not await is_admin(inter): await inter.response.send_message(admin_msg("가격 설정하기"), ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    if 가격 < 0: await inter.followup.send("0 이상 정수만 가능합니다.", ephemeral=True); return
    db.config["price_per_unit"] = 가격
    await inter.followup.send(admin_msg("가격 설정하기"), ephemeral=True)
    await update_panel_message(inter.guild)

@bot.tree.command(name="유저조회", description="-# 유저 조회하기 ( 관리자 전용 )")
@app_commands.describe(유저="대상 유저")
async def 유저조회(inter: Interaction, 유저: discord.User):
    if not await is_admin(inter): await inter.response.send_message(admin_msg("유저 조회하기"), ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    w = db.wallet(유저.id)
    emb = Embed(
        title=f"유저: @{유저.display_name}",
        description=(
            f"{str(E['big_id'])} 남은 잔액 : `{w['balance']}`\n"
            f"{str(E['upuoipipi'])} 누적 금액 : `{w['total']}`\n"
            f"{str(E['role_glass'])} 역할 등급 : `{w['rank']}`"
        ),
        color=COLOR_GREY
    )
    await inter.followup.send(embed=emb, ephemeral=True)

@bot.tree.command(name="잔액추가", description="-# 잔액 추가하기 ( 관리자 전용 )")
@app_commands.describe(유저="대상 유저", 금액="정수(1 이상)")
async def 잔액추가(inter: Interaction, 유저: discord.User, 금액: int):
    if not await is_admin(inter): await inter.response.send_message(admin_msg("잔액 추가하기"), ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    if 금액 < 1: await inter.followup.send("1 이상 정수만 가능합니다.", ephemeral=True); return
    w = db.wallet(유저.id); w["balance"] += 금액; w["total"] += 금액
    await inter.followup.send(admin_msg("잔액 추가하기"), ephemeral=True)

@bot.tree.command(name="잔액차감", description="-# 잔액 차감하기 ( 관리자 전용 )")
@app_commands.describe(유저="대상 유저", 금액="정수(1 이상)")
async def 잔액차감(inter: Interaction, 유저: discord.User, 금액: int):
    if not await is_admin(inter): await inter.response.send_message(admin_msg("잔액 차감하기"), ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    w = db.wallet(유저.id)
    if 금액 < 1 or w["balance"] < 금액:
        await inter.followup.send("잔액이 부족하거나 금액이 잘못되었습니다.", ephemeral=True); return
    w["balance"] -= 금액
    await inter.followup.send(admin_msg("잔액 차감하기"), ephemeral=True)

@bot.tree.command(name="봇자판기", description="-# 패널 보내기 ( 관리자 전용 )")
async def 봇자판기(inter: Interaction):
    if not await is_admin(inter): await inter.response.send_message(admin_msg("패널 보내기"), ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    msg = await inter.channel.send(embed=await build_panel_embed(), view=PanelView())
    db.config["panel_channel_id"] = inter.channel.id
    db.config["panel_message_id"] = msg.id
    await inter.followup.send(admin_msg("패널 보내기"), ephemeral=True)

@bot.tree.command(name="수익표시", description="-# 총 수익 표시하기 ( 관리자 전용 )")
async def 수익표시(inter: Interaction):
    if not await is_admin(inter): await inter.response.send_message(admin_msg("총 수익 표시하기"), ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    emb = Embed(
        description=f"이번주 총 `{db.weekly_sold}`만큼 팔았습니다\n-# 총 수익 표시하기 ( 관리자 전용 )",
        color=COLOR_GREY
    )
    await inter.followup.send(embed=emb, ephemeral=True)

@bot.tree.command(name="계좌수정", description="-# 계좌수정 ( 관리자 전용 )")
@app_commands.describe(은행명="은행명", 계좌번호="계좌번호", 예금주="예금주", 유효시간분="유효시간(분, 비우면 30분)")
async def 계좌수정(inter: Interaction, 은행명: str, 계좌번호: str, 예금주: str, 유효시간분: Optional[int] = None):
    if not await is_admin(inter): await inter.response.send_message(admin_msg("계좌수정"), ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    ttl = DEFAULT_TTL_SECONDS if not 유효시간분 or 유효시간분 <= 0 else 유효시간분 * 60
    expire = db.now_ts() + ttl
    db.bank.update({"bank": 은행명.strip(), "number": 계좌번호.strip(), "holder": 예금주.strip(), "expire_at": expire})
    await inter.followup.send(admin_msg("계좌수정"), ephemeral=True)

@bot.tree.command(name="로그설정", description="-# 로그 설정하기 ( 관리자 전용 )")
@app_commands.describe(관리자채널="로그 채널")
async def 로그설정(inter: Interaction, 관리자채널: discord.TextChannel):
    if not await is_admin(inter): await inter.response.send_message(admin_msg("로그 설정하기"), ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    db.logs["channel_id"] = 관리자채널.id
    await inter.followup.send(admin_msg("로그 설정하기"), ephemeral=True)

@bot.tree.command(name="관리자설정", description="-# 관리자 역할 설정하기 ( 관리자 전용 )")
@app_commands.describe(역할="관리자 역할")
async def 관리자설정(inter: Interaction, 역할: discord.Role):
    if not await is_admin(inter): await inter.response.send_message(admin_msg("관리자 역할 설정하기"), ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    # 인메모리 샘플: 실제 역할 저장/검증 로직은 생략(필요 시 확장)
    await inter.followup.send(admin_msg("관리자 역할 설정하기"), ephemeral=True)

@bot.tree.command(name="결제수단", description="-# 결제수단 설정하기 ( 관리자 전용 )")
@app_commands.describe(계좌="허용/거부", 코인="허용/거부", 문상="허용/거부")
@app_commands.choices(계좌=[app_commands.Choice(name="허용", value="허용"), app_commands.Choice(name="거부", value="거부")])
@app_commands.choices(코인=[app_commands.Choice(name="허용", value="허용"), app_commands.Choice(name="거부", value="거부")])
@app_commands.choices(문상=[app_commands.Choice(name="허용", value="허용"), app_commands.Choice(name="거부", value="거부")])
async def 결제수단(inter: Interaction, 계좌: app_commands.Choice[str], 코인: app_commands.Choice[str], 문상: app_commands.Choice[str]):
    if not await is_admin(inter): await inter.response.send_message(admin_msg("결제수단 설정하기"), ephemeral=True); return
    await inter.response.defer(ephemeral=True, thinking=False)
    # 필요하면 인메모리에 반영하도록 확장 가능
    await inter.followup.send(admin_msg("결제수단 설정하기"), ephemeral=True)

# ===== 실행 =====
def main():
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN 비어 있음")
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
