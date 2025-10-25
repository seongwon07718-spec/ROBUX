import discord
from discord import PartialEmoji, ui, app_commands
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient

# 직접 입력: 디스코드 봇 토큰과 몽고DB URI (보안주의)
TOKEN = ""
MONGO_URI = ""

# 몽고DB 클라이언트 설정
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["boost_db"]  # 데이터베이스 이름
users_collection = db["users"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # display_name 접근용
bot = commands.Bot(command_prefix="!", intents=intents)

class MyLayoutVending(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        container = ui.Container(ui.TextDisplay("**최저가 부스트**\n-# 버튼을 눌러 이용해주세요"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        boost_section = ui.Section(
            ui.TextDisplay("**부스트 재고\n-# 60초마다 갱신됩니다**"),
            accessory=ui.Button(label="1000 부스트", disabled=True, style=discord.ButtonStyle.primary)
        )
        container.add_item(boost_section)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        custom_emoji1 = PartialEmoji(name="d3", id=1431500583415713812)
        custom_emoji2 = PartialEmoji(name="d8", id=1431500580198682676)
        custom_emoji3 = PartialEmoji(name="d4", id=1431500582295965776)
        custom_emoji4 = PartialEmoji(name="d19", id=1431500579162554511)

        button_1 = ui.Button(label="충전", custom_id="button_1", emoji=custom_emoji1)
        button_2 = ui.Button(label="후기", custom_id="button_2", emoji=custom_emoji2)
        button_3 = ui.Button(label="정보", custom_id="button_3", emoji=custom_emoji3)
        button_4 = ui.Button(label="구매", custom_id="button_4", emoji=custom_emoji4)

        row1 = ui.ActionRow(button_1, button_2)
        row2 = ui.ActionRow(button_3, button_4)

        container.add_item(row1)
        container.add_item(row2)

        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        user_id = interaction.user.id
        user_name = interaction.user.display_name

        # 이용 제한 유저인지 확인
        blocked = await db["blocked_users"].find_one({"user_id": user_id})
        if blocked:
            # 이용 제한 컨테이너 답장
            view = ui.LayoutView(timeout=None)
            c = ui.Container()
            c.add_item(ui.TextDisplay(f"### 이용 제한\n---"))
            c.add_item(ui.TextDisplay(f"현재 {user_name}님은 __자판기 이용 제한__ 되었습니다"))
            c.add_item(ui.TextDisplay("이용 제한을 풀고 싶다면 문의해주세요"))
            view.add_item(c)
            await interaction.response.send_message(view=view, ephemeral=True)
            return False

        # 유저 최초 이용 시 DB 등록
        user_data = await users_collection.find_one({"user_id": user_id})
        if not user_data:
            new_user = {
                "user_name": user_name,
                "user_id": user_id,
                "balance": 0,
                "total_spent": 0,
                "transaction_count": 0
            }
            await users_collection.insert_one(new_user)
            print(f"새 사용자 {user_name} ({user_id}) DB 등록 완료")
        return True

    # 버튼 상호작용 콜백 예시 (버튼 id에 따른 처리)
    @ui.button(label="정보", custom_id="button_3", style=discord.ButtonStyle.secondary)
    async def info_button(self, interaction: discord.Interaction, button: ui.Button):
        user_id = interaction.user.id
        user_data = await users_collection.find_one({"user_id": user_id})
        if not user_data:
            # 혹시 DB 없을 경우 기본 메시지
            await interaction.response.send_message("등록된 정보가 없습니다.", ephemeral=True)
            return

        view = ui.LayoutView(timeout=None)
        c = ui.Container()
        c.add_item(ui.TextDisplay(f"### {interaction.user.display_name}님 정보\n---"))
        c.add_item(ui.TextDisplay(f"**남은 금액** = {user_data.get('balance', 0)}원"))
        c.add_item(ui.TextDisplay(f"**누적 금액** = {user_data.get('total_spent', 0)}원"))
        c.add_item(ui.TextDisplay("**역할 등급** = 아직 미정"))
        view.add_item(c)
        await interaction.response.send_message(view=view, ephemeral=True)

@bot.tree.command(name="부스트_자판기", description="부스트 자판기 패널을 표시합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def panel_vending(interaction: discord.Interaction):
    view = MyLayoutVending()
    await interaction.response.send_message(view=view)

@bot.tree.command(name="디비_상태", description="디비 상태를 확인합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def check_db_status_slash(interaction: discord.Interaction):
    status_view = ui.LayoutView(timeout=60)
    container = ui.Container()
    container.add_item(ui.TextDisplay("### 데이터베이스 상태 확인 결과"))
    container.add_item(ui.Separator())

    try:
        await mongo_client.admin.command('ping')
        user_count = await users_collection.count_documents({})
        container.add_item(ui.TextDisplay("✅ 연결 상태: 정상"))
        container.add_item(ui.TextDisplay(f"등록된 사용자 수: {user_count}명"))

    except Exception as e:
        container.add_item(ui.TextDisplay("❌ 연결 오류"))
        container.add_item(ui.TextDisplay(f"오류 내용: {e}"))
        container.add_item(ui.TextDisplay("**MONGO_URI 및 네트워크 설정을 확인하세요.**"))

    status_view.add_item(container)
    await interaction.response.send_message(view=status_view, ephemeral=True)

@bot.command(name="디비상태")
@commands.has_permissions(administrator=True)
async def check_db_status_prefix(ctx: commands.Context):
    status_view = ui.LayoutView(timeout=60)
    container = ui.Container()
    container.add_item(ui.TextDisplay("## 데이터베이스 상태 확인 결과"))
    container.add_item(ui.Separator())

    try:
        await mongo_client.admin.command('ping')
        user_count = await users_collection.count_documents({})
        container.add_item(ui.TextDisplay("✅ 연결 상태: 정상"))
        container.add_item(ui.TextDisplay(f"등록된 사용자 수: {user_count}명"))

    except Exception as e:
        container.add_item(ui.TextDisplay("❌ 연결 오류"))
        container.add_item(ui.TextDisplay(f"오류 내용: {e}"))
        container.add_item(ui.TextDisplay("**MONGO_URI 및 네트워크 설정을 확인하세요.**"))

    status_view.add_item(container)
    await ctx.send(view=status_view)

@bot.tree.command(
    name="이용_제한",
    description="특정 유저 자판기 이용 제한/해제",
)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    user="제한/해제 대상 유저를 선택하세요.",
    제한="자판기 이용 제한 여부를 선택하세요."
)
@app_commands.choices(
    제한=[
        app_commands.Choice(name="차단", value="block"),
        app_commands.Choice(name="풀기", value="unblock")
    ]
)
async def restriction_cmd(
    interaction: discord.Interaction,
    user: discord.Member,
    제한: app_commands.Choice[str]
):
    if 제한.value == "block":
        # DB에 차단 기록 저장 (중복 저장 방지)
        existing = await db["blocked_users"].find_one({"user_id": user.id})
        if existing:
            msg_container = ui.Container()
            msg_container.add_item(ui.TextDisplay(f"이미 {user.display_name}님은 차단 상태입니다."))
        else:
            await db["blocked_users"].update_one(
                {"user_id": user.id},
                {"$set": {"user_name": user.display_name, "blocked": True}},
                upsert=True
            )
            msg_container = ui.Container()
            msg_container.add_item(ui.TextDisplay("자판기 차단 완료되었습니다"))
        view = ui.LayoutView(timeout=None)
        view.add_item(msg_container)
        await interaction.response.send_message(view=view, ephemeral=True)

    elif 제한.value == "unblock":
        existing = await db["blocked_users"].find_one({"user_id": user.id})
        if existing:
            await db["blocked_users"].delete_one({"user_id": user.id})
            msg_container = ui.Container()
            msg_container.add_item(ui.TextDisplay("자판기 차단 풀기 완료되었습니다"))
        else:
            msg_container = ui.Container()
            msg_container.add_item(ui.TextDisplay(f"{user.display_name}님은 차단 상태가 아닙니다."))
        view = ui.LayoutView(timeout=None)
        view.add_item(msg_container)
        await interaction.response.send_message(view=view, ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} 로그인 성공")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)}개 슬래시 명령어 동기화 완료")
    except Exception as e:
        print(f"❌ 슬래시 명령어 동기화 오류: {e}")

    try:
        await mongo_client.admin.command('ping')
        print("✅ MongoDB 연결 성공")
    except Exception as e:
        print(f"❌ MongoDB 연결 실패: {e}")

bot.run(TOKEN)
