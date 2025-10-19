import discord
from discord import PartialEmoji, ui
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from datetime import datetime

# .env 로드
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")  # 반드시 .env에 설정하세요

intents = discord.Intents.all()
command_prefix = "!"
bot = commands.Bot(command_prefix=command_prefix, intents=intents)

ROLE_ID = 1419336612956864712  # 예시: 필요하면 사용

# ------------------ 기존 레이아웃 (변경 최소화) ------------------
class MyLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        self.c = ui.Container(ui.TextDisplay("**누락 보상 받기**"))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.c.add_item(ui.TextDisplay("-# 아래 누락보상 버튼을 누르시면 보상 받을 수 있습니다.\n-# 다만 제품 보증 없는거는 보상 받으실 수 없습니다."))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 기존에 사용하던 커스텀 이모지를 그대로 두었으나, 필요시 유니코드로 바꾸세요.
        custom_emoji1 = PartialEmoji(name="__", id=1429373065116123190)
        custom_emoji2 = PartialEmoji(name="1_7", id=1429373066588454943)

        self.button_1 = ui.Button(label="누락 보상 받기", custom_id="button_1", emoji=custom_emoji1)
        self.button_2 = ui.Button(label="누락 제품 확인", custom_id="button_2", emoji=custom_emoji2)

        linha = ui.ActionRow(self.button_1, self.button_2)

        self.c.add_item(linha)
        self.add_item(self.c)

active_views = {}

class MyLayoutVending(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        
        c = ui.Container(ui.TextDisplay(
            "**24시간 OTT 자판기**\n-# 버튼을 눌러 이용해주세요 !"
        ))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        sessao = ui.Section(ui.TextDisplay("**총 판매 금액\n-# 실시간으로 올라갑니다.**"), accessory=ui.Button(label="0원", disabled=True))
        c.add_item(sessao)
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 이모지 (예시 ID)
        custom_emoji1 = PartialEmoji(name="3", id=1426934636428394678)
        custom_emoji2 = PartialEmoji(name="6", id=1426943544928505886)
        custom_emoji3 = PartialEmoji(name="5", id=1426936503635939428)
        custom_emoji4 = PartialEmoji(name="4", id=1426936460149395598)

        # 메인 버튼들
        button_1 = ui.Button(label="충전", custom_id="button_1", emoji=custom_emoji1)
        button_2 = ui.Button(label="입고알림", custom_id="button_2", emoji=custom_emoji2)
        button_3 = ui.Button(label="내 정보", custom_id="button_3", emoji=custom_emoji3)
        button_4 = ui.Button(label="구매", custom_id="button_4", emoji=custom_emoji4)

        linha = ui.ActionRow(button_1, button_2)
        linha2 = ui.ActionRow(button_3, button_4)

        c.add_item(linha)
        c.add_item(linha2)
        self.add_item(c)

        # "내 정보" 버튼에 콜백 연결 (이 클래스 내부에서 연결)
        button_3.callback = self.on_my_info_click

    # "내 정보" 버튼 콜백: 사용자 DB에서 정보 조회 후 에페메럴 컨테이너로 전송
    async def on_my_info_click(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild

        # DB가 준비되어 있는지 확인
        if not hasattr(bot, "mongo_db"):
            await interaction.response.send_message("DB가 아직 연결되지 않았습니다. 잠시 후 다시 시도해주세요.", ephemeral=True)
            return

        users_col = bot.mongo_db["users"]
        tx_col = bot.mongo_db["transactions"]

        # 사용자 데이터 조회(없으면 기본값)
        user_doc = await users_col.find_one({"user_id": int(member.id), "guild_id": int(guild.id)}) if guild else None
        if user_doc is None:
            # 기본값: 보유=0, 누적=0, 거래횟수=0
            balance = 0
            total = 0
            tx_count = 0
        else:
            balance = user_doc.get("balance", 0)
            total = user_doc.get("total", 0)
            tx_count = user_doc.get("tx_count", 0)

        # 거래 내역 존재 여부 조회 (최근 10건만)
        tx_cursor = tx_col.find({"user_id": int(member.id), "guild_id": int(guild.id)}).sort("created_at", -1).limit(10)
        tx_list = await tx_cursor.to_list(length=10)

        # 에페메럴 뷰(누른 사용자만 보임)
        ephemeral_view = ui.LayoutView(timeout=120)

        info_container = ui.Container(ui.TextDisplay(f"**{member.display_name}님 정보**"))
        info_container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        info_container.add_item(ui.TextDisplay(f"**보유 금액** = __{balance}__원"))
        info_container.add_item(ui.TextDisplay(f"**누적 금액** = __{total}__원"))
        info_container.add_item(ui.TextDisplay(f"**거래 횟수** = __{tx_count}__번"))
        info_container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        info_container.add_item(ui.TextDisplay("항상 이용해주셔서 감사합니다."))
        ephemeral_view.add_item(info_container)

        # 거래 목록이 하나라도 있으면 드롭다운(셀렉트) 추가
        if tx_list and len(tx_list) > 0:
            # Select 옵션 생성 (최근 거래들을 option으로 표시)
            options = []
            for tx in tx_list:
                # 각 거래 문서에서 간단히 날짜+타입+금액을 라벨로 표시
                created = tx.get("created_at")
                if isinstance(created, datetime):
                    ts = created.strftime("%Y-%m-%d %H:%M")
                else:
                    ts = str(created)
                amount = tx.get("amount", 0)
                ttype = tx.get("type", "거래")
                label = f"{ts} | {ttype} | {amount}원"
                # value에는 tx_id 또는 인덱스를 넣어 후속 조회에 사용
                options.append(ui.SelectOption(label=label, value=str(tx.get("_id"))))

            select = ui.Select(placeholder="거래 내역 보기", options=options, min_values=1, max_values=1)

            async def select_callback(select_interaction: discord.Interaction):
                # 선택된 거래의 _id로 상세 조회
                selected_id = select_interaction.data["values"][0]
                # MongoDB의 ObjectId 비교를 위해 문자열로 저장한 경우 직접 조회
                # 안전하게는 문자열 형태로 tx의 _id를 저장했으므로 문자열로 조회
                tx_doc = await tx_col.find_one({"_id": selected_id})
                if tx_doc is None:
                    # 가능성: _id 형식이 ObjectId인 경우라면 str이 아닌 ObjectId로 조회해야 함
                    # 이 경우, 사용자가 tx_doc 조회 실패 시 대체 메시지 출력
                    await select_interaction.response.send_message("선택한 거래 내역을 불러오지 못했습니다.", ephemeral=True)
                    return

                # 상세 컨테이너 생성 및 전송 (에페메럴)
                detail_view = ui.LayoutView(timeout=60)
                d_c = ui.Container(ui.TextDisplay("**거래 내역 상세**"))
                d_c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                d_c.add_item(ui.TextDisplay(f"거래 ID: {tx_doc.get('_id')}"))
                d_c.add_item(ui.TextDisplay(f"종류: {tx_doc.get('type', '알수없음')}"))
                d_c.add_item(ui.TextDisplay(f"금액: {tx_doc.get('amount', 0)}원"))
                d_c.add_item(ui.TextDisplay(f"설명: {tx_doc.get('note', '-') }"))
                d_c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                d_c.add_item(ui.TextDisplay("감사합니다."))
                detail_view.add_item(d_c)
                await select_interaction.response.send_message(view=detail_view, ephemeral=True)

            select.callback = select_callback
            # 셀렉트는 액션로우에 넣어야 함
            row = ui.ActionRow(select)
            ephemeral_view.add_item(row)

        # 응답: 에페메럴로 정보창 전송
        await interaction.response.send_message(view=ephemeral_view, ephemeral=True)

# ------------------ DB 연결 및 봇 이벤트 ------------------
@bot.event
async def on_ready():
    # MongoDB 연결 (한 번만)
    if not hasattr(bot, "mongo_client"):
        if not MONGO_URI:
            print("MONGO_URI가 설정되어 있지 않습니다. .env 파일을 확인하세요.")
        else:
            bot.mongo_client = AsyncIOMotorClient(MONGO_URI)
            # 기본 DB명을 URI에서 가져오거나 명시적으로 지정 가능
            try:
                bot.mongo_db = bot.mongo_client.get_default_database()
                if bot.mongo_db is None:
                    # 예: 명시적 DB명 사용 (원하시면 바꿔 쓰세요)
                    bot.mongo_db = bot.mongo_client["my_database"]
            except Exception:
                bot.mongo_db = bot.mongo_client["my_database"]

            # 컬렉션 인덱스 설정(선택적)
            try:
                # users 컬렉션에 user_id+guild_id 인덱스 생성(중복 방지/빠른 조회)
                bot.mongo_db["users"].create_index([("user_id", 1), ("guild_id", 1)], unique=True)
                bot.mongo_db["transactions"].create_index([("user_id", 1), ("guild_id", 1), ("created_at", -1)])
            except Exception:
                pass

    print(f"로벅스 자판기 봇이 {bot.user}로 로그인했습니다.")
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'슬래시 명령어 동기화 중 오류 발생.: {e}')

# ------------------ 슬래시 명령 (기존 유지) ------------------
@bot.tree.command(name="누락패널", description="누락 보상 패널을 표시합니다")
async def button_panel_nurak(interaction: discord.Interaction):
    layout = MyLayout()
    await interaction.response.send_message(view=layout, ephemeral=False)

@bot.tree.command(name="자판기패널", description="자판기 패널을 표시합니다")
async def button_panel_vending(interaction: discord.Interaction):
    layout = MyLayoutVending()
    await interaction.response.send_message(view=layout, ephemeral=False)

# ------------------ 예시: 거래 저장 함수 (다른 곳에서 호출 가능) ------------------
# 거래가 발생할 때마다 아래 함수를 호출하여 users 컬렉션 및 transactions 컬렉션을 업데이트하세요.
async def record_transaction(guild_id: int, user_id: int, amount: int, ttype: str = "구매", note: str = ""):
    """
    사용 예: await record_transaction(guild.id, user.id, 3000, ttype="구매", note="상품A")
    """
    users_col = bot.mongo_db["users"]
    tx_col = bot.mongo_db["transactions"]

    # 트랜잭션 문서 생성 (여기서는 _id를 문자열로 저장해 셀렉트에서 편히 사용하도록 함)
    tx_doc = {
        "_id": f"{int(datetime.utcnow().timestamp()*1000)}_{user_id}",  # 간단한 문자열 ID
        "guild_id": int(guild_id),
        "user_id": int(user_id),
        "amount": int(amount),
        "type": ttype,
        "note": note,
        "created_at": datetime.utcnow()
    }
    await tx_col.insert_one(tx_doc)

    # users 컬렉션 업서트: 보유(balance), 누적(total), 거래횟수(tx_count) 업데이트
    await users_col.update_one(
        {"user_id": int(user_id), "guild_id": int(guild_id)},
        {"$inc": {"balance": amount, "total": amount, "tx_count": 1}},
        upsert=True
    )

# ------------------ 봇 실행 (토큰 빈칸으로 유지) ------------------
bot.run("")  # 여기에 봇 토큰 입력
