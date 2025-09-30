import os
import discord
from discord import app_commands
from discord.ext import commands

# 네 서버 ID
GUILD_ID = 1419200424636055592
GUILD = discord.Object(id=GUILD_ID)

# 회색 컬러
GRAY = discord.Color.from_str("#808080")

# 커스텀 이모지
EMOJI_NOTICE = "<:ticket:1422579515955085388>"
EMOJI_CHARGE = "<:charge:1422579517679075448>"
EMOJI_INFO   = "<:info:1422579514218905731>"
EMOJI_BUY    = "<a:11845034938353746621:1421383445669613660>"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# 드롭다운 컴포넌트들
# =========================
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
        selection = self.values[0]
        def get_example_txns(mode: str):
            base = [
                {"id": "A1032", "item": "프리미엄 구독 1개월", "amount": 5900, "status": "완료"},
                {"id": "A1031", "item": "포인트 1000",       "amount": 1000, "status": "완료"},
                {"id": "A1028", "item": "포인트 5000",       "amount": 5000, "status": "취소"},
                {"id": "A1025", "item": "OTT 이용권",         "amount": 9900, "status": "완료"},
                {"id": "A1019", "item": "포인트 2000",       "amount": 2000, "status": "완료"},
                {"id": "A1015", "item": "포인트 3000",       "amount": 3000, "status": "완료"},
            ]
            if mode == "last5":  return base[:5]
            if mode == "days7":  return base[:3]
            if mode == "days30": return base[:5]
            if mode == "days90": return base
            return base[:5]
        txns = get_example_txns(selection)
        title_map = {"last5": "최근 거래 5건", "days7": "최근 7일 거래", "days30": "최근 30일 거래", "days90": "최근 90일 거래"}
        lines = [f"- [{t['id']}] {t['item']} | {t['amount']}원 | {t['status']}" for t in txns]
        desc = "\n".join(lines) if lines else "거래내역이 없습니다."
        embed = discord.Embed(title=title_map.get(selection, "거래내역"), description=desc, color=GRAY)
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
        embed = discord.Embed(title=f"카테고리 선택됨: {name_map.get(val, val)}", description="이 카테고리에서 구매 가능한 상품을 곧 보여줄게.", color=GRAY)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class BuyCategoryView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=180)
        self.add_item(CategorySelect(user))

# =========================
# 메인 버튼 패널
# =========================
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
        embed = discord.Embed(
            title="공지사항",
            description="서버규칙 필독 부탁드립니다\n구매후 이용후기는 필수입니다\n자충 오류시 티켓 열어주세요",
            color=GRAY
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_charge(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{EMOJI_CHARGE} 충전 페이지로 안내할게!", ephemeral=True)

    async def on_info(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="내 정보",
            description="보유 금액 : `예시`원\n누적 금액 : `예시`원\n거래 횟수 : `예시`번",
            color=GRAY
        )
        view = MyInfoView(interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def on_buy(self, interaction: discord.Interaction):
        embed = discord.Embed(title="카테고리 선택하기", description="구매할 카테고리를 선택해주세요", color=GRAY)
        view = BuyCategoryView(interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

# =========================
# 슬래시 커맨드(데코레이터로만 등록)
# =========================
@bot.tree.command(name="버튼패널", description="윈드 OTT 버튼 패널을 표시합니다.")
async def 버튼패널(interaction: discord.Interaction):
    embed = discord.Embed(title="윈드 OTT", description="아래 원하시는 버튼을 눌러 이용해주세요!", color=GRAY)
    view = ButtonPanel()
    await interaction.response.send_message(embed=embed, view=view)

def is_admin():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.guild_permissions.manage_guild:
            return True
        await interaction.response.send_message("관리자만 사용할 수 있어.", ephemeral=True)
        return False
    return app_commands.check(predicate)

class ExistingCategorySelect(discord.ui.Select):
    def __init__(self, categories: list[discord.CategoryChannel], author: discord.User):
        options = [discord.SelectOption(label=cat.name, value=str(cat.id)) for cat in categories[:25]] \
                  or [discord.SelectOption(label="카테고리가 없습니다", value="none", description="먼저 새 카테고리를 만드세요")]
        super().__init__(placeholder="기존 카테고리를 선택하세요", min_values=1, max_values=1, options=options, custom_id=f"exist_cat_{author.id}")
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("작성자만 선택할 수 있어.", ephemeral=True)
            return
        if self.values[0] == "none":
            await interaction.response.send_message("선택 가능한 카테고리가 없어요. 새 이름으로 다시 실행해줘.", ephemeral=True)
            return
        cat_id = int(self.values[0])
        guild = interaction.guild
        category = guild.get_channel(cat_id)
        if not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("유효하지 않은 카테고리야.", ephemeral=True)
            return
        channel_name = "구매-안내"
        text_ch = discord.utils.get(category.text_channels, name=channel_name.replace(" ", "-"))
        if text_ch is None:
            text_ch = await guild.create_text_channel(channel_name, category=category, reason="구매 안내 채널 자동 생성")
        embed = discord.Embed(title="카테고리 설정 완료", description=f"선택한 카테고리: {category.name}\n안내 채널: {text_ch.mention}", color=GRAY)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ExistingCategoryView(discord.ui.View):
    def __init__(self, categories: list[discord.CategoryChannel], author: discord.User):
        super().__init__(timeout=180)
        self.add_item(ExistingCategorySelect(categories, author))

@app_commands.command(name="카테고리_설정", description="구매 안내가 표시될 카테고리를 설정합니다.")
@is_admin()
@app_commands.describe(
    새_카테고리_이름="새 카테고리를 만들려면 이름을 입력 (미입력 시 기존 카테고리 선택)",
    안내채널_이름="안내 채널 이름 (기본: 구매-안내)"
)
async def 카테고리_설정(interaction: discord.Interaction, 새_카테고리_이름: str | None = None, 안내채널_이름: str | None = None):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("길드에서만 쓸 수 있어.", ephemeral=True)
        return
    channel_name = (안내채널_이름 or "구매-안내").strip()
    if 새_카테고리_이름:
        category = await guild.create_category(새_카테고리_이름.strip(), reason="카테고리 설정 커맨드로 생성")
        text_ch = discord.utils.get(category.text_channels, name=channel_name.replace(" ", "-"))
        if text_ch is None:
            text_ch = await guild.create_text_channel(channel_name, category=category, reason="구매 안내 채널 자동 생성")
        embed = discord.Embed(title="카테고리 설정 완료", description=f"새 카테고리 생성: {category.name}\n안내 채널: {text_ch.mention}", color=GRAY)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        categories = list(guild.categories)
        if not categories:
            await interaction.response.send_message("서버에 카테고리가 없어요. 새 이름을 입력해서 만들어줘.", ephemeral=True)
            return
        embed = discord.Embed(title="카테고리 선택", description="구매 안내를 표시할 기존 카테고리를 골라줘.", color=GRAY)
        view = ExistingCategoryView(categories, interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# 트리에 한 번만 등록
bot.tree.add_command(카테고리_설정, guild=GUILD)

# =========================
# on_ready: 길드 전용 싱크 1회
# =========================
@bot.event
async def on_ready():
    try:
        # 길드에 커맨드(길드 스코프) 등록 + 동기화
        await bot.tree.sync(guild=GUILD)
        # 버튼패널도 길드 스코프로 보장
        bot.tree.copy_global_to(guild=GUILD)
        synced = await bot.tree.sync(guild=GUILD)
        print(f"길드 슬래시 커맨드 동기화 완료({GUILD_ID}): {len(synced)}개")
    except Exception as e:
        print(f"동기화 오류: {e}")
    guild_names = [g.name for g in bot.guilds if g.id == GUILD_ID]
    print(f"로그인: {bot.user} (준비 완료) | 연결 길드: {guild_names or [GUILD_ID]}")

TOKEN = os.getenv("DISCORD_TOKEN", "여기에_토큰_넣기")
bot.run(TOKEN)
