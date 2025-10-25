import discord
from discord import PartialEmoji, ui, app_commands
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient

# 토큰과 MongoDB 연결 문자열 직접 지정 (보안상 주의하세요)
TOKEN = ""
MONGO_URI = ""

client = AsyncIOMotorClient(MONGO_URI)
db = client["boost_db"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # display_name 등 사용자 정보 접근용
bot = commands.Bot(command_prefix="!", intents=intents)

# MongoDB 비동기 클라이언트 설정
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["boost_vending"]
users_collection = db["users"]

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
        container.add_item(ui.TextDisplay(f"EMOJI_3 등록된 사용자 수: {user_count}명"))
        
    except Exception as e:
        container.add_item(ui.TextDisplay("❌ 연결 오류"))
        container.add_item(ui.TextDisplay(f"오류 내용: {e}"))
        container.add_item(ui.TextDisplay("**MONGO_URI 및 네트워크 설정을 확인하세요.**"))

    status_view.add_item(container)
    await ctx.send(view=status_view)

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
