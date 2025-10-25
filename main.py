import discord
from discord import PartialEmoji, ui, app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# .env 파일 로드
load_dotenv()

# 환경 변수에서 토큰과 MongoDB URI 가져오기
TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# MongoDB 비동기 클라이언트 설정
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["boost_vending"]  # 데이터베이스 이름
users_collection = db["users"]  # 사용자 정보 컬렉션

class MyLayoutVending(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        c = ui.Container(ui.TextDisplay("**최저가 부스트**\n-# 버튼을 눌러 이용해주세요"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        boost = ui.Section(ui.TextDisplay("**부스트 재고\n-# 60초마다 갱신됩니다**"), accessory=ui.Button(label="1000 부스트", disabled=True, style=discord.ButtonStyle.primary))
        c.add_item(boost)
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        custom_emoji1 = PartialEmoji(name="d3", id=1431500583415713812)
        custom_emoji2 = PartialEmoji(name="d8", id=1431500580198682676)
        custom_emoji3 = PartialEmoji(name="d4", id=1431500582295965776)
        custom_emoji4 = PartialEmoji(name="d19", id=1431500579162554511)

        button_1 = ui.Button(label="충전", custom_id="button_1", emoji=custom_emoji1)
        button_2 = ui.Button(label="후기", custom_id="button_2", emoji=custom_emoji2)
        button_3 = ui.Button(label="정보", custom_id="button_3", emoji=custom_emoji3)
        button_4 = ui.Button(label="구매", custom_id="button_4", emoji=custom_emoji4)
        
        linha = ui.ActionRow(button_1, button_2)
        linha2 = ui.ActionRow(button_3, button_4)
        
        c.add_item(linha)
        c.add_item(linha2)
        self.add_item(c)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """자판기 버튼 클릭 시 사용자 DB 등록 또는 업데이트"""
        user_id = interaction.user.id
        user_name = interaction.user.name
        
        # 사용자가 이미 DB에 있는지 확인
        user_data = await users_collection.find_one({"user_id": user_id})
        
        if not user_data:
            # 새 사용자 등록
            new_user = {
                "user_name": user_name,
                "user_id": user_id,
                "balance": 0,  # 남은 금액
                "total_spent": 0,  # 누적 금액
                "transaction_count": 0  # 거래 횟수
            }
            await users_collection.insert_one(new_user)
        
        # 버튼 상호작용에 따른 추가 로직은 여기에 구현
        return True

@bot.tree.command(name="부스트_자판기", description="부스트 자판기를 표시합니다")
@app_commands.checks.has_permissions(administrator=True)
async def panel_vending(interaction: discord.Interaction):
    view = MyLayoutVending()
    await interaction.response.send_message(view=view, ephemeral=False)

@bot.tree.command(name="디비_상태", description="MongoDB 연결 상태를 확인합니다")
@app_commands.checks.has_permissions(administrator=True)
async def check_db_status(interaction: discord.Interaction):
    try:
        # MongoDB 연결 확인
        await mongo_client.admin.command('ping')
        
        # 사용자 수 확인
        user_count = await users_collection.count_documents({})
        
        embed = discord.Embed(
            title="데이터베이스 상태",
            description="MongoDB 연결 상태 및 정보",
            color=discord.Color.green()
        )
        embed.add_field(name="연결 상태", value="✅ 정상", inline=False)
        embed.add_field(name="등록된 사용자 수", value=f"{user_count}명", inline=True)
        embed.add_field(name="데이터베이스", value="boost_vending", inline=True)
        embed.add_field(name="컬렉션", value="users", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        embed = discord.Embed(
            title="데이터베이스 상태",
            description=f"❌ 연결 오류: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def 디비상태(ctx):
    try:
        # MongoDB 연결 확인
        await mongo_client.admin.command('ping')
        
        # 사용자 수 확인
        user_count = await users_collection.count_documents({})
        
        embed = discord.Embed(
            title="데이터베이스 상태",
            description="MongoDB 연결 상태 및 정보",
            color=discord.Color.green()
        )
        embed.add_field(name="연결 상태", value="✅ 정상", inline=False)
        embed.add_field(name="등록된 사용자 수", value=f"{user_count}명", inline=True)
        embed.add_field(name="데이터베이스", value="boost_vending", inline=True)
        embed.add_field(name="컬렉션", value="users", inline=True)
        
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="데이터베이스 상태",
            description=f"❌ 연결 오류: {str(e)}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅{len(synced)}개의 슬래시 명령이 동기화 완료")
