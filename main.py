import os
import re
import asyncio
import discord
from discord import app_commands
from discord.ext import commands

# ===== 기본 설정 =====
GUILD_ID = 1419200424636055592
GUILD = discord.Object(id=GUILD_ID)
GRAY = discord.Color.from_str("#808080")

EMOJI_NOTICE = "<:ticket:1422579515955085388>"
EMOJI_CHARGE = "<:charge:1422579517679075448>"
EMOJI_INFO   = "<:info:1422579514218905731>"
EMOJI_BUY    = "<a:NitroPremium:1422605740530471065>"  # 교체본

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== 유틸: 커스텀 이모지 파서 =====
CUSTOM_EMOJI_RE = re.compile(r"^<(?P<anim>a?):(?P<name>[a-zA-Z0-9_]+):(?P<id>\d+)>$")

def parse_partial_emoji(text: str) -> discord.PartialEmoji | None:
    if not text:
        return None
    m = CUSTOM_EMOJI_RE.match(text.strip())
    if not m:
        return None
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

# ===== 컴포넌트들 =====
class TransactionSelect(discord.ui.Select):
    def __init__(self, user: discord.User):
        options = [
            discord.SelectOption(label="최근 5건", value="last5", description="가장 최근 거래 5개"),
            discord.SelectOption(label="최근 7일", value="days7", description="지난 7일간 거래"),
            discord.SelectOption(label="최근 30일", value="days30", description="지난 30일간 거래"),
            discord.SelectOption(label="최근 90일", value="days90", description="지난 90일간 거래"),
        ]
        super().__init__(placeholder="거래내역 조회 옵션을 선택하세요", min_values=1, max_values=1, options=options, custom_id=f"txn_select_{user.id}")
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True)
            return

        def get_example_txns(mode: str):
            base = [
                {"id": "A1032", "item": "프리미엄 구독 1개월", "amount": 5900, "status": "완료"},
                {"id": "A1031", "item": "포인트 1000",       "amount": 1000, "status": "완료"},
                {"id": "A1028", "item": "포인트 5000",       "amount": 5000, "status": "취소"},
                {"id": "A1025", "item": "OTT 이용권",         "amount": 9900, "status": "완료"},
                {"id": "A1019", "item": "포인트 2000",       "amount": 2000, "status": "완료"},
                {"id": "A1015", "item": "포인트 3000",       "amount": 3000, "status": "완료"},
            ]
            return base[:5] if mode in ("last5", "days30") else base[:3] if mode == "days7" else base

        sel = self.values[0]
        txns = get_example_txns(sel)
        title_map = {"last5": "최근 거래 5건", "days7": "최근 7일 거래", "days30": "최근 30일 거래", "days90": "최근 90일 거래"}
        lines = [f"- [{t['id']}] {t['item']} | {t['amount']}원 | {t['status']}" for t in txns]
        desc = "\n".join(lines) if lines else "거래내역이 없습니다."
        await interaction.response.send_message(
            embed=discord.Embed(title=title_map.get(sel, "거래내역"), description=desc, color=GRAY),
            ephemeral=True
        )

class MyInfoView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=180)
        self.add_item(TransactionSelect(user))

class CategorySelect(discord.ui.Select):
    def __init__(self, user: discord.User):
        options = [
            discord.SelectOption(label="OTT 이용권", value="ott", description="OTT 관련 상품"),
            discord.SelectOption(label="포인트 충전권", value="point", description="포인트 패키지"),
            discord.SelectOption(label="프리미엄 구독", value="premium", description="구독형 상품"),
        ]
        super().__init__(placeholder="카테고리를 선택하세요", min_values=1, max_values=1, options=options, custom_id=f"buy_cat_{user.id}")
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True)
            return
        name_map = {"ott": "OTT 이용권", "point": "포인트 충전권", "premium": "프리미엄 구독"}
        val = self.values[0]
        await interaction.response.send_message(
            embed=discord.Embed(title=f"카테고리 선택됨: {name_map.get(val, val)}", description="이 카테고리에서 구매 가능한 상품을 곧 보여줄게.", color=GRAY),
            ephemeral=True
        )

class BuyCategoryView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=180)
        self.add_item(CategorySelect(user))

class ButtonPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.notice_btn = discord.ui.Button(label="공지사항", style=discord.ButtonStyle.secondary, emoji=EMOJI_NOTICE, custom_id="panel_notice", row=0)
        self.charge_btn = discord.ui.Button(label="충전",   style=discord.ButtonStyle.secondary, emoji=EMOJI_CHARGE, custom_id="panel_charge", row=0)
        self.info_btn   = discord.ui.Button(label="내 정보", style=discord.ButtonStyle.secondary, emoji=EMOJI_INFO,   custom_id="panel_info",   row=1)
        self.buy_btn    = discord.ui.Button(label="구매",   style=discord.ButtonStyle.secondary, emoji=EMOJI_BUY,    custom_id="panel_buy",    row=1)

        self.add_item(self.notice_btn); self.notice_btn.callback = self.on_notice
        self.add_item(self.charge_btn); self.charge_btn.callback = self.on_charge
        self.add_item(self.info_btn);   self.info_btn.callback   = self.on_info
        self.add_item(self.buy_btn);    self.buy_btn.callback    = self.on_buy

    async def on_notice(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(title="공지사항",
                                description="서버규칙 필독 부탁드립니다\n구매후 이용후기는 필수입니다\n자충 오류시 티켓 열어주세요",
                                color=GRAY),
            ephemeral=True
        )

    async def on_charge(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{EMOJI_CHARGE} 충전 페이지로 안내할게!", ephemeral=True)

    async def on_info(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(title="내 정보",
                                description="보유 금액 : `예시`원\n누적 금액 : `예시`원\n거래 횟수 : `예시`번",
                                color=GRAY),
            view=MyInfoView(interaction.user),
            ephemeral=True
        )

    async def on_buy(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(title="카테고리 선택하기",
                                description="구매할 카테고리를 선택해주세요",
                                color=GRAY),
            view=BuyCategoryView(interaction.user),
            ephemeral=True
        )

# ===== 카테고리 모달 =====
class CategorySetupModal(discord.ui.Modal, title="카테고리 설정"):
    name_input = discord.ui.TextInput(label="카테고리 이름", placeholder="예) 구매센터", required=True, max_length=100)
    desc_input = discord.ui.TextInput(label="카테고리 설명", style=discord.TextStyle.paragraph, placeholder="예) 구매 관련 안내/공지", required=False, max_length=400)
    emoji_input = discord.ui.TextInput(label="카테고리 이모지", placeholder="예) 😀 또는 <:name:id> 또는 <a:name:id>", required=False, max_length=100)

    def __init__(self, author: discord.User, channel_name: str = "구매-안내"):
        super().__init__()
        self.author = author
        self.channel_name = channel_name

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("작성자만 제출할 수 있어.", ephemeral=True)
            return
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("길드에서만 사용할 수 있어.", ephemeral=True)
            return

        name = str(self.name_input.value).strip()
        desc = str(self.desc_input.value).strip() if self.desc_input.value else ""
        emoji_text = str(self.emoji_input.value).strip() if self.emoji_input.value else ""

        category = await guild.create_category(name, reason="카테고리 설정(모달)로 생성")

        ch_name = self.channel_name.replace(" ", "-")
        text_ch = discord.utils.get(category.text_channels, name=ch_name)
        if text_ch is None:
            text_ch = await guild.create_text_channel(ch_name, category=category, reason="구매 안내 채널 자동 생성")

        pemoji = parse_partial_emoji(emoji_text)
        emoji_display = str(pemoji) if pemoji else (emoji_text if emoji_text else "")

        lines = []
        if desc: lines.append(desc)
        if emoji_display: lines.append(f"카테고리 이모지: {emoji_display}")
        description = "\n".join(lines) if lines else "카테고리가 생성되었습니다."

        msg = await text_ch.send(embed=discord.Embed(title=f"카테고리 생성: {name}", description=description, color=GRAY))
        try:
            await msg.pin(reason="카테고리 안내 고정")
        except Exception:
            pass

        await interaction.response.send_message(
            embed=discord.Embed(title="카테고리 설정 완료",
                                description=f"카테고리: {category.name}\n안내 채널: {text_ch.mention}",
                                color=GRAY),
            ephemeral=True
        )

# ===== Cog로 명령 묶기 (새 방식) =====
class ControlCog(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    # /버튼패널
    @app_commands.command(name="버튼패널", description="윈드 OTT 버튼 패널을 표시합니다.")
    @app_commands.guilds(GUILD)
    async def 버튼패널(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(title="윈드 OTT", description="아래 원하시는 버튼을 눌러 이용해주세요!", color=GRAY),
            view=ButtonPanel()
        )

    # /카테고리_설정
    @app_commands.command(name="카테고리_설정", description="구매 카테고리를 모달로 설정합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    @app_commands.describe(안내채널_이름="안내 채널 이름 (기본: 구매-안내)")
    async def 카테고리_설정(self, interaction: discord.Interaction, 안내채널_이름: str | None = None):
        ch_name = (안내채널_이름 or "구매-안내").strip()
        await interaction.response.send_modal(CategorySetupModal(author=interaction.user, channel_name=ch_name))

    # /카테고리_삭제
    @app_commands.command(name="카테고리_삭제", description="구매 카테고리를 선택해 삭제합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 카테고리_삭제(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("길드에서만 사용할 수 있어.", ephemeral=True)
            return
        categories = list(guild.categories)
        if not categories:
            await interaction.response.send_message("삭제할 카테고리가 없어요.", ephemeral=True)
            return

        class CategoryDeleteSelect(discord.ui.Select):
            def __init__(self, cats, author):
                options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in cats[:25]] \
                          or [discord.SelectOption(label="카테고리 없음", value="none", description="먼저 카테고리를 생성하세요")]
                super().__init__(placeholder="삭제할 카테고리를 선택하세요", min_values=1, max_values=1, options=options, custom_id=f"cat_del_{author.id}")
                self.author = author

            async def callback(self, inter: discord.Interaction):
                if inter.user.id != self.author.id:
                    await inter.response.send_message("작성자만 선택할 수 있어.", ephemeral=True)
                    return
                if self.values[0] == "none":
                    await inter.response.send_message("삭제할 카테고리가 없어요.", ephemeral=True)
                    return
                cat_id = int(self.values[0])
                category = inter.guild.get_channel(cat_id)
                if not isinstance(category, discord.CategoryChannel):
                    await inter.response.send_message("유효하지 않은 카테고리야.", ephemeral=True)
                    return
                for ch in list(category.channels):
                    try:
                        await ch.delete(reason="카테고리 삭제에 따른 하위 채널 정리")
                    except Exception:
                        pass
                name_backup = category.name
                await category.delete(reason="관리자 요청으로 카테고리 삭제")
                await inter.response.send_message(
                    embed=discord.Embed(title="카테고리 삭제 완료", description=f"삭제된 카테고리: {name_backup}", color=GRAY),
                    ephemeral=True
                )

        view = discord.ui.View(timeout=180)
        view.add_item(CategoryDeleteSelect(categories, interaction.user))
        await interaction.response.send_message(
            embed=discord.Embed(title="카테고리 삭제", description="삭제할 카테고리를 선택하세요.", color=GRAY),
            view=view, ephemeral=True
        )

async def force_guild_sync(bot_: commands.Bot, guild_obj: discord.Object, retry: int = 3):
    # 글로벌은 건드리지 않고, 길드 명령만 재싱크
    for attempt in range(1, retry + 1):
        try:
            synced = await bot_.tree.sync(guild=guild_obj)
            print(f"[setup_hook] 길드 싱크 완료({guild_obj.id}): {len(synced)}개 -> {', '.join('/'+c.name for c in synced)}")
            return
        except discord.HTTPException as e:
            wait = 2 * attempt
            print(f"[setup_hook] 싱크 실패 {attempt}/{retry}: {e}. {wait}s 후 재시도")
            await asyncio.sleep(wait)
    print("[setup_hook] 길드 싱크 재시도 한계 초과")

@bot.event
async def setup_hook():
    # 새로운 방식: Cog 등록 → 길드 싱크
    await bot.add_cog(ControlCog(bot))
    # 과거 글로벌 커맨드가 남아 UI에 중복으로 보이는 걸 방지하려면(optional):
    try:
        # 글로벌 목록만 받아서 로깅(지우진 않음; 필요 시 주석 해제해 비움)
        g = await bot.tree.sync()
        print(f"[setup_hook] 글로벌 확인: {len(g)}개")
        # 글로벌 지우고 싶으면 아래 두 줄 주석 해제:
        # bot.tree.clear_commands(guild=None)
        # await bot.tree.sync()
    except Exception as e:
        print(f"[setup_hook] 글로벌 확인 실패: {e}")

    await force_guild_sync(bot, GUILD, retry=3)

@bot.event
async def on_ready():
    print(f"로그인: {bot.user} (준비 완료) | 연결 길드: {[g.name for g in bot.guilds if g.id == GUILD_ID] or [GUILD_ID]}")

TOKEN = os.getenv("DISCORD_TOKEN", "여기에_토큰_넣기")
bot.run(TOKEN)
