# pip install -U discord.py

import os
import discord
from discord.ext import commands

# 서버 ID
GUILD_ID = 1419200424636055592

# 회색 컬러
GRAY = discord.Color.from_str("#808080")

# 커스텀 이모지
EMOJI_NOTICE = "<:ticket:1422579515955085388>"
EMOJI_CHARGE = "<:charge:1422579517679075448>"
EMOJI_INFO   = "<:info:1422579514218905731>"
EMOJI_BUY    = "<a:11845034938353746621:1421383445669613660>"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


# 거래내역 드롭다운(Select) 컴포넌트
class TransactionSelect(discord.ui.Select):
    def __init__(self, user: discord.User):
        # 옵션 예시: 최근 5건, 기간별 조회
        options = [
            discord.SelectOption(label="최근 5건", value="last5", description="가장 최근 거래 5개"),
            discord.SelectOption(label="최근 7일", value="days7", description="지난 7일간 거래"),
            discord.SelectOption(label="최근 30일", value="days30", description="지난 30일간 거래"),
            discord.SelectOption(label="최근 90일", value="days90", description="지난 90일간 거래"),
        ]
        super().__init__(
            placeholder="거래내역 조회 옵션을 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"txn_select_{user.id}"
        )
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        # 본인만 조회 가능하게 체크(원하면 제거 가능)
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("이 드롭다운은 작성자만 사용할 수 있어.", ephemeral=True)
            return

        selection = self.values[0]

        # 예시 데이터 생성 함수 (실제 연동 시 DB/시트 조회로 교체)
        def get_example_txns(mode: str):
            base = [
                {"id": "A1032", "item": "프리미엄 구독 1개월", "amount": 5900, "status": "완료"},
                {"id": "A1031", "item": "포인트 1000",       "amount": 1000, "status": "완료"},
                {"id": "A1028", "item": "포인트 5000",       "amount": 5000, "status": "취소"},
                {"id": "A1025", "item": "OTT 이용권",         "amount": 9900, "status": "완료"},
                {"id": "A1019", "item": "포인트 2000",       "amount": 2000, "status": "완료"},
                {"id": "A1015", "item": "포인트 3000",       "amount": 3000, "status": "완료"},
            ]
            if mode == "last5":
                return base[:5]
            elif mode == "days7":
                return base[:3]
            elif mode == "days30":
                return base[:5]
            elif mode == "days90":
                return base
            return base[:5]

        txns = get_example_txns(selection)

        # 임베드 구성
        title_map = {
            "last5": "최근 거래 5건",
            "days7": "최근 7일 거래",
            "days30": "최근 30일 거래",
            "days90": "최근 90일 거래",
        }
        lines = []
        for t in txns:
            lines.append(f"- [{t['id']}] {t['item']} | {t['amount']}원 | {t['status']}")

        desc = "\n".join(lines) if lines else "거래내역이 없습니다."
        embed = discord.Embed(
            title=title_map.get(selection, "거래내역"),
            description=desc,
            color=GRAY
        )

        # 나만 보이게 응답 (드롭다운 선택 시)
        await interaction.response.send_message(embed=embed, ephemeral=True)


# “내 정보” 뷰: 드롭다운 포함
class MyInfoView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=180)
        self.add_item(TransactionSelect(user))


# 메인 버튼 패널
class ButtonPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

        # 2x2 버튼 (회색)
        self.notice_btn = discord.ui.Button(
            label="공지사항",
            style=discord.ButtonStyle.secondary,
            emoji=EMOJI_NOTICE,
            custom_id="panel_notice",
            row=0
        )
        self.charge_btn = discord.ui.Button(
            label="충전",
            style=discord.ButtonStyle.secondary,
            emoji=EMOJI_CHARGE,
            custom_id="panel_charge",
            row=0
        )
        self.info_btn = discord.ui.Button(
            label="내 정보",
            style=discord.ButtonStyle.secondary,
            emoji=EMOJI_INFO,
            custom_id="panel_info",
            row=1
        )
        self.buy_btn = discord.ui.Button(
            label="구매",
            style=discord.ButtonStyle.secondary,
            emoji=EMOJI_BUY,
            custom_id="panel_buy",
            row=1
        )

        self.add_item(self.notice_btn)
        self.add_item(self.charge_btn)
        self.add_item(self.info_btn)
        self.add_item(self.buy_btn)

        # 콜백
        self.notice_btn.callback = self.on_notice
        self.charge_btn.callback = self.on_charge
        self.info_btn.callback = self.on_info
        self.buy_btn.callback = self.on_buy

    # 공지사항: 회색 임베드 + 나만 보이게
    async def on_notice(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="공지사항",
            description=(
                "서버규칙 필독 부탁드립니다\n"
                "구매후 이용후기는 필수입니다\n"
                "자충 오류시 티켓 열어주세요"
            ),
            color=GRAY
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # 충전
    async def on_charge(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{EMOJI_CHARGE} 충전 페이지로 안내할게!", ephemeral=True)

    # 내 정보: 임베드 + 드롭다운 뷰, 모두 나만 보이게
    async def on_info(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="내 정보",
            description=(
                "보유 금액 : `예시`원\n"
                "누적 금액 : `예시`원\n"
                "거래 횟수 : `예시`번"
            ),
            color=GRAY
        )
        view = MyInfoView(interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # 구매
    async def on_buy(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{EMOJI_BUY} 구매 절차를 시작할게!", ephemeral=True)

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


@bot.tree.command(name="버튼패널", description="윈드 OTT 버튼 패널을 표시합니다.")
async def button_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="윈드 OTT",
        description="아래 원하시는 버튼을 눌러 이용해주세요!",
        color=GRAY
    )
    view = ButtonPanel()
    await interaction.response.send_message(embed=embed, view=view)


@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"길드 슬래시 커맨드 동기화 완료({GUILD_ID}): {len(synced)}개")
    except Exception as e:
        print(f"동기화 오류: {e}")
    print(f"로그인: {bot.user} (준비 완료)")


TOKEN = os.getenv("DISCORD_TOKEN", "여기에_토큰_넣기")
bot.run(TOKEN)
