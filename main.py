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

# 버튼 이모지들
EMOJI_NOTICE = "<:ticket:1422579515955085388>"
EMOJI_CHARGE = "<a:11845034938353746621:1421383445669613660>"  # 요청대로 충전 이모지 교체
EMOJI_INFO   = "<:info:1422579514218905731>"
EMOJI_BUY    = "<a:NitroPremium:1422605740530471065>"

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

# ===== 중앙 저장소: 구매 카테고리(메모리) =====
class PurchaseCategoryStore:
    # 시작은 비어 있음
    categories: list[dict] = []

    @classmethod
    def set_category(cls, name: str, desc: str = "", emoji_text: str = ""):
        # 중복 이름이면 갱신, 아니면 추가
        idx = next((i for i, c in enumerate(cls.categories) if c["name"] == name), -1)
        pemoji = parse_partial_emoji(emoji_text)
        emoji_display = str(pemoji) if pemoji else (emoji_text if emoji_text else "")
        data = {"name": name, "desc": desc, "emoji": emoji_display}
        if idx >= 0:
            cls.categories[idx] = data
        else:
            cls.categories.append(data)

    @classmethod
    def delete_category(cls, name: str):
        cls.categories = [c for c in cls.categories if c["name"] != name]

    @classmethod
    def list_categories(cls):
        return list(cls.categories)

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
            if mode == "last5":  return base[:5]
            if mode == "days7":  return base[:3]
            if mode == "days30": return base[:5]
            if mode == "days90": return base
            return base[:5]

        mode = self.values[0]
        txns = get_example_txns(mode)
        title_map = {"last5": "최근 거래 5건", "days7": "최근 7일 거래", "days30": "최근 30일 거래", "days90": "최근 90일 거래"}
        lines = [f"- [{t['id']}] {t['item']} | {t['amount']}원 | {t['status']}" for t in txns]
        desc = "\n".join(lines) if lines else "거래내역이 없습니다."
        await interaction.response.send_message(embed=discord.Embed(title=title_map.get(mode, "거래내역"), description=desc, color=GRAY), ephemeral=True)

class MyInfoView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=None)
        self.add_item(TransactionSelect(user))

class DynamicCategorySelect(discord.ui.Select):
    def __init__(self, user: discord.User):
        cats = PurchaseCategoryStore.list_categories()
        if cats:
            options = [discord.SelectOption(label=f"{c['name']}", value=c['name'], description=(c['desc'][:80] if c['desc'] else None)) for c in cats[:25]]
            placeholder = "카테고리를 선택하세요"
        else:
            # 비어 있으면 선택 못 하게 더미 옵션
            options = [discord.SelectOption(label="등록된 카테고리가 없습니다", value="__none__", description="관리자가 /카테고리_설정으로 추가하세요")]
            placeholder = "카테고리가 없습니다"
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, custom_id=f"buy_cat_dynamic_{user.id}")
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True)
            return
        val = self.values[0]
        if val == "__none__":
            await interaction.response.send_message("지금은 선택할 카테고리가 없어요. 잠시 후 다시 시도해줘.", ephemeral=True)
            return
        await interaction.response.send_message(embed=discord.Embed(title=f"카테고리 선택됨: {val}", description="이 카테고리의 상품을 곧 보여줄게.", color=GRAY), ephemeral=True)

class BuyCategoryView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=None)
        self.add_item(DynamicCategorySelect(user))

class ButtonPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.notice_btn = discord.ui.Button(label="공지사항", style=discord.ButtonStyle.secondary, emoji=EMOJI_NOTICE, custom_id="panel_notice", row=0)
        self.charge_btn = discord.ui.Button(label="충전",   style=discord.ButtonStyle.secondary, emoji=EMOJI_CHARGE, custom_id="panel_charge", row=0)
        self.info_btn   = discord.ui.Button(label="내 정보", style=discord.ButtonStyle.secondary, emoji=EMOJI_INFO,   custom_id="panel_info",   row=1)
        self.buy_btn    = discord.ui.Button(label="구매",   style=discord.ButtonStyle.secondary, emoji=EMOJI_BUY,    custom_id="panel_buy",    row=1)

        self.add_item(self.notice_btn); self.notice_btn.callback = self.on_notice
        self.add_item(self.charge_btn); self.charge_btn.callback = self.on_charge
        self.add_item(self.info_btn);   self.info_btn.callback   = self.on_info
        self.add_item(self.buy_btn);    self.buy_btn.callback    = self.on_buy

    async def on_notice(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(title="공지사항", description="서버규칙 필독 부탁드립니다\n구매후 이용후기는 필수입니다\n자충 오류시 티켓 열어주세요", color=GRAY), ephemeral=True)

    async def on_charge(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{EMOJI_CHARGE} 충전 페이지로 안내할게!", ephemeral=True)

    async def on_info(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(title="내 정보", description="보유 금액 : `예시`원\n누적 금액 : `예시`원\n거래 횟수 : `예시`번", color=GRAY), view=MyInfoView(interaction.user), ephemeral=True)

    async def on_buy(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(title="카테고리 선택하기", description="구매할 카테고리를 선택해주세요", color=GRAY), view=BuyCategoryView(interaction.user), ephemeral=True)

# ===== 카테고리 설정 모달 =====
class CategorySetupModal(discord.ui.Modal, title="카테고리 설정"):
    name_input = discord.ui.TextInput(label="카테고리 이름", placeholder="예) OTT 이용권", required=True, max_length=60)
    desc_input = discord.ui.TextInput(label="카테고리 설명", style=discord.TextStyle.paragraph, placeholder="예) OTT 관련 상품 카테고리", required=False, max_length=200)
    emoji_input = discord.ui.TextInput(label="카테고리 이모지", placeholder="예) 😀 또는 <:name:id> 또는 <a:name:id>", required=False, max_length=100)

    def __init__(self, author: discord.User):
        super().__init__()
        self.author = author

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("작성자만 제출할 수 있어.", ephemeral=True)
            return

        name = str(self.name_input.value).strip()
        desc = str(self.desc_input.value).strip() if self.desc_input.value else ""
        emoji_text = str(self.emoji_input.value).strip() if self.emoji_input.value else ""

        PurchaseCategoryStore.set_category(name=name, desc=desc, emoji_text=emoji_text)

        preview = f"{emoji_text + ' ' if emoji_text else ''}{name}\n{desc}" if (desc or emoji_text) else name
        await interaction.response.send_message(embed=discord.Embed(title="구매 카테고리 등록 완료", description=preview, color=GRAY), ephemeral=True)

# ===== Cog 구조 =====
class ControlCog(commands.Cog):
    def __init__(self, bot_: commands.Bot):
        self.bot = bot_

    # /버튼패널
    @app_commands.command(name="버튼패널", description="윈드 OTT 버튼 패널을 표시합니다.")
    @app_commands.guilds(GUILD)
    async def 버튼패널(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(title="윈드 OTT", description="아래 원하시는 버튼을 눌러 이용해주세요!", color=GRAY), view=ButtonPanel())

    # /카테고리_설정: 바로 모달
    @app_commands.command(name="카테고리_설정", description="구매 카테고리를 추가/수정합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 카테고리_설정(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CategorySetupModal(author=interaction.user))

    # /카테고리_삭제: 현재 등록된 ‘구매 카테고리’만
    @app_commands.command(name="카테고리_삭제", description="구매 카테고리를 삭제합니다.")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 카테고리_삭제(self, interaction: discord.Interaction):
        cats = PurchaseCategoryStore.list_categories()
        if not cats:
            await interaction.response.send_message("삭제할 ‘구매 카테고리’가 없습니다.", ephemeral=True)
            return

        class CatDeleteSelect(discord.ui.Select):
            def __init__(self, categories, author):
                options = [discord.SelectOption(label=(c['name']), value=c['name'], description=(c['desc'][:80] if c['desc'] else None)) for c in categories[:25]]
                super().__init__(placeholder="삭제할 ‘구매 카테고리’를 선택하세요", min_values=1, max_values=1, options=options, custom_id=f"buycat_del_{author.id}")
                self.author = author

            async def callback(self, inter: discord.Interaction):
                if inter.user.id != self.author.id:
                    await inter.response.send_message("작성자만 선택할 수 있어.", ephemeral=True)
                    return
                name = self.values[0]
                PurchaseCategoryStore.delete_category(name)
                await inter.response.send_message(embed=discord.Embed(title="카테고리 삭제 완료", description=f"삭제된 카테고리: {name}", color=GRAY), ephemeral=True)

        view = discord.ui.View(timeout=None)
        view.add_item(CatDeleteSelect(cats, interaction.user))
        await interaction.response.send_message(embed=discord.Embed(title="구매 카테고리 삭제", description="삭제할 카테고리를 선택하세요.", color=GRAY), view=view, ephemeral=True)

# ===== setup_hook에서 깔끔 등록/동기화 =====
async def guild_sync(bot_: commands.Bot):
    try:
        synced = await bot_.tree.sync(guild=GUILD)
        print(f"[setup_hook] 길드 싱크 완료({GUILD_ID}): {len(synced)}개 -> {', '.join('/'+c.name for c in synced)}")
    except Exception as e:
        print(f"[setup_hook] 길드 싱크 실패: {e}")

@bot.event
async def setup_hook():
    await bot.add_cog(ControlCog(bot))
    await guild_sync(bot)

@bot.event
async def on_ready():
    print(f"로그인: {bot.user} (준비 완료) | 연결 길드: {[g.name for g in bot.guilds if g.id == GUILD_ID] or [GUILD_ID]}")

# ===== 실행 =====
TOKEN = os.getenv("DISCORD_TOKEN", "여기에_토큰_넣기")
bot.run(TOKEN)
