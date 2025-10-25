import discord
from discord import PartialEmoji, ui, app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# .env 파일 로드
load_dotenv()

TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

if not TOKEN:
    print("오류: .env 파일에 디스코드 봇 TOKEN이 설정되지 않았습니다.")
    exit(1)
if not MONGO_URI:
    print("오류: .env 파일에 MongoDB URI가 설정되지 않았습니다.")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
# 멤버 인텐트도 추가하여 interaction.user.name 사용 시 누락 방지 (선택 사항이지만 안전함)
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# MongoDB 비동기 클라이언트 설정
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["boost_vending"]  # 데이터베이스 이름 (원하는 이름으로 변경 가능)
users_collection = db["users"]  # 사용자 정보 컬렉션 (컬렉션 이름도 변경 가능)

class MyLayoutVending(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        # Container 생성 (최상위 컨테이너)
        c = ui.Container(ui.TextDisplay("**최저가 부스트**\n-# 버튼을 눌러 이용해주세요"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 부스트 재고 섹션
        # ui.Section은 ui.Container의 subclass이며, label과 accessory를 가질 수 있습니다.
        boost = ui.Section(ui.TextDisplay("**부스트 재고\n-# 60초마다 갱신됩니다**"), 
                            accessory=ui.Button(label="1000 부스트", disabled=True, style=discord.ButtonStyle.primary))
        c.add_item(boost)
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 커스텀 이모지 설정 (실제 서버에 해당 ID의 이모지가 존재해야 합니다)
        custom_emoji1 = PartialEmoji(name="d3", id=1431500583415713812)
        custom_emoji2 = PartialEmoji(name="d8", id=1431500580198682676)
        custom_emoji3 = PartialEmoji(name="d4", id=1431500582295965776)
        custom_emoji4 = PartialEmoji(name="d19", id=1431500579162554511)

        # 버튼 생성
        button_1 = ui.Button(label="충전", custom_id="button_1", emoji=custom_emoji1, style=discord.ButtonStyle.secondary) # 스타일 추가
        button_2 = ui.Button(label="후기", custom_id="button_2", emoji=custom_emoji2, style=discord.ButtonStyle.secondary) # 스타일 추가
        button_3 = ui.Button(label="정보", custom_id="button_3", emoji=custom_emoji3, style=discord.ButtonStyle.secondary) # 스타일 추가
        button_4 = ui.Button(label="구매", custom_id="button_4", emoji=custom_emoji4, style=discord.ButtonStyle.primary) # 스타일 추가
        
        # 버튼을 ActionRow에 추가
        linha = ui.ActionRow(button_1, button_2)
        linha2 = ui.ActionRow(button_3, button_4)
        
        # ActionRow를 메인 컨테이너에 추가
        c.add_item(linha)
        c.add_item(linha2)
        
        # LayoutView에 메인 컨테이너 추가
        self.add_item(c)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        자판기 버튼 클릭 시 사용자 DB 등록 또는 업데이트
        자판기 기능을 이용한 사람만 DB에 저장되도록 합니다.
        """
        user_id = interaction.user.id
        user_name = interaction.user.display_name # display_name 사용으로 서버 닉네임 고려
        
        # 사용자가 이미 DB에 있는지 확인
        user_data = await users_collection.find_one({"user_id": user_id})
        
        if not user_data:
            # 새 사용자 등록 (초기 값 설정)
            new_user = {
                "user_name": user_name,
                "user_id": user_id,
                "balance": 0,          # 남은 금액
                "total_spent": 0,      # 누적 금액
                "transaction_count": 0 # 거래 횟수
            }
            await users_collection.insert_one(new_user)
            print(f"새 사용자 {user_name} ({user_id})가 DB에 등록되었습니다.")
        
        # 여기서는 단순히 DB 등록/업데이트만 하고 상호작용 자체는 계속 진행합니다.
        # 버튼 상호작용에 따른 추가 로직은 각 버튼의 콜백 함수에서 구현해야 합니다.
        return True # True를 반환해야 버튼 클릭 상호작용이 계속 처리됩니다.

@bot.tree.command(name="부스트_자판기", description="부스트 자판기 패널을 표시합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def panel_vending(interaction: discord.Interaction):
    """
    관리자만 사용할 수 있는 부스트 자판기 패널 생성 슬래시 커맨드
    """
    view = MyLayoutVending()
    await interaction.response.send_message(view=view) # ephemeral=False가 기본값

@bot.tree.command(name="디비_상태", description="MongoDB 연결 상태를 확인하고 정보를 표시합니다 (관리자 전용).")
@app_commands.checks.has_permissions(administrator=True)
async def check_db_status_slash(interaction: discord.Interaction):
    """
    관리자만 사용할 수 있는 MongoDB 상태 확인 슬래시 커맨드
    응답은 Container 형태로 표시됩니다.
    """
    status_view = ui.LayoutView(timeout=60) # 60초 후 자동으로 비활성화
    container = ui.Container()
    
    container.add_item(ui.TextDisplay("## 데이터베이스 상태 확인 결과"))
    container.add_item(ui.Separator())

    try:
        # MongoDB 연결 확인
        await mongo_client.admin.command('ping')
        
        # 사용자 수 확인 (컬렉션에 있는 문서 수)
        user_count = await users_collection.count_documents({})
        
        container.add_item(ui.TextDisplay("✅ **연결 상태**: 성공적으로 연결되었습니다."))
        container.add_item(ui.TextDisplay(f"EMOJI_0 **등록된 사용자 수**: {user_count}명"))
        container.add_item(ui.TextDisplay("EMOJI_1 **데이터베이스 이름**: `boost_vending`"))
        container.add_item(ui.TextDisplay("EMOJI_2 **사용자 컬렉션 이름**: `users`"))
        
        status_view.add_item(container)
        await interaction.response.send_message(view=status_view, ephemeral=True) # 관리자에게만 보이도록 ephemeral=True
        
    except Exception as e:
        container.add_item(ui.TextDisplay("❌ **연결 상태**: 오류 발생"))
        container.add_item(ui.TextDisplay(f"**오류 내용**: {e}"))
        container.add_item(ui.TextDisplay("---"))
        container.add_item(ui.TextDisplay("**.env 파일의 `MONGO_URI`를 확인하거나, MongoDB Atlas 대시보드에서 IP 접근 목록 및 데이터베이스 사용자 권한을 확인해주세요.**"))
        
        status_view.add_item(container)
        await interaction.response.send_message(view=status_view, ephemeral=True) # 관리자에게만 보이도록 ephemeral=True


@bot.command(name="디비상태")
@commands.has_permissions(administrator=True)
async def check_db_status_prefix(ctx: commands.Context):
    """
    관리자만 사용할 수 있는 MongoDB 상태 확인 접두사 커맨드 (!디비상태)
    응답은 Container 형태로 표시됩니다.
    """
    status_view = ui.LayoutView(timeout=60) # 60초 후 자동으로 비활성화
    container = ui.Container()
    
    container.add_item(ui.TextDisplay("## 데이터베이스 상태 확인 결과"))
    container.add_item(ui.Separator())

    try:
        await mongo_client.admin.command('ping')
        user_count = await users_collection.count_documents({})
        
        container.add_item(ui.TextDisplay("✅ **연결 상태**: 성공적으로 연결되었습니다."))
        container.add_item(ui.TextDisplay(f"EMOJI_3 **등록된 사용자 수**: {user_count}명"))
        container.add_item(ui.TextDisplay("EMOJI_4 **데이터베이스 이름**: `boost_vending`"))
        container.add_item(ui.TextDisplay("EMOJI_5 **사용자 컬렉션 이름**: `users`"))
        
        status_view.add_item(container)
        await ctx.send(view=status_view)
        
    except Exception as e:
        container.add_item(ui.TextDisplay("❌ **연결 상태**: 오류 발생"))
        container.add_item(ui.TextDisplay(f"**오류 내용**: {e}"))
        container.add_item(ui.TextDisplay("---"))
        container.add_item(ui.TextDisplay("**.env 파일의 `MONGO_URI`를 확인하거나, MongoDB Atlas 대시보드에서 IP 접근 목록 및 데이터베이스 사용자 권한을 확인해주세요.**"))
        
        status_view.add_item(container)
        await ctx.send(view=status_view)


@bot.event
async def on_ready():
    """
    봇이 준비되었을 때 실행되는 이벤트 핸들러
    슬래시 커맨드를 동기화하고 MongoDB 연결을 시도합니다.
    """
    print(f"✅ {bot.user}로 로그인 성공")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)}개의 슬래시 명령이 동기화 완료")
    except Exception as e:
        print(f"❌ 명령 동기화 오류: {e}")

    # 봇 시작 시 MongoDB 연결 테스트 (필수는 아니지만, 초기 연결 확인에 유용)
    try:
        await mongo_client.admin.command('ping')
        print("✅ MongoDB Atlas에 성공적으로 연결되었습니다!")
    except Exception as e:
        print(f"❌ MongoDB Atlas 연결 실패: {e}")
        print("MongoDB Atlas 연결 문자열(MONGO_URI) 또는 네트워크 설정을 확인해주세요.")


# 봇 실행 (TOKEN은 .env 파일에서 불러옵니다)
bot.run(TOKEN)
