# main.py (MongoDB + motor 사용 버전)
import discord
from discord import PartialEmoji, ui, SelectOption, TextStyle
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
from datetime import datetime
import asyncio
from functools import partial

# Mongo
from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId

# .env 로드
load_dotenv()

# 기본 MONGO_URI (테스트용/직접 하드코딩)
# 튜어오오오옹님이 주신 값 예시:
DEFAULT_MONGO_URI = ""
MONGO_URI = os.getenv("MONGO_URI") or DEFAULT_MONGO_URI

intents = discord.Intents.all()
command_prefix = "!"
bot = commands.Bot(command_prefix=command_prefix, intents=intents)

# 역할 ID (서버에 맞게 수정)
NOTIFY_ROLE_ID = 1429436071539773561

# MongoDB 클라이언트와 컬렉션을 on_ready에서 설정합니다.
# 컬렉션 네임: users, transactions, products, subscriptions, bans

# ------------------ 기존 레이아웃(변경 최소화) ------------------
class MyLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.c = ui.Container(ui.TextDisplay("**누락 보상 받기**"))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.c.add_item(ui.TextDisplay("-# 아래 누락보상 버튼을 누르시면 보상 받을 수 있습니다.\n-# 다만 제품 보증 없는거는 보상 받으실 수 없습니다."))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
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
        c = ui.Container(ui.TextDisplay("**24시간 OTT 자판기**\n-# 버튼을 눌러 이용해주세요 !"))
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        sessao = ui.Section(ui.TextDisplay("**총 판매 금액\n-# 실시간으로 올라갑니다.**"), accessory=ui.Button(label="0원", disabled=True))
        c.add_item(sessao)
        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        custom_emoji1 = PartialEmoji(name="3", id=1426934636428394678)
        custom_emoji2 = PartialEmoji(name="6", id=1426943544928505886)
        custom_emoji3 = PartialEmoji(name="5", id=1426936503635939428)
        custom_emoji4 = PartialEmoji(name="4", id=1426936460149395598)
        button_1 = ui.Button(label="충전", custom_id="button_1", emoji=custom_emoji1)
        button_2 = ui.Button(label="입고알림", custom_id="button_2", emoji=custom_emoji2)
        button_3 = ui.Button(label="내 정보", custom_id="button_3", emoji=custom_emoji3)
        button_4 = ui.Button(label="구매", custom_id="button_4", emoji=custom_emoji4)
        linha = ui.ActionRow(button_1, button_2)
        linha2 = ui.ActionRow(button_3, button_4)
        c.add_item(linha)
        c.add_item(linha2)
        self.add_item(c)

        # 콜백 연결
        button_2.callback = self.on_notify_click
        button_3.callback = self.on_my_info_click
        button_4.callback = self.on_purchase_click

    # 입고알림 토글
    async def on_notify_click(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("서버에서만 사용 가능합니다.", ephemeral=True)
            return
        try:
            new_state = await bot.db_toggle_subscription(guild.id, member.id)
        except Exception:
            await interaction.response.send_message("구독 처리 중 오류가 발생했습니다.", ephemeral=True)
            return
        role = guild.get_role(NOTIFY_ROLE_ID)
        if new_state:
            if role:
                try:
                    await member.add_roles(role, reason="입고알림 구독")
                except:
                    pass
            msg_lines = [
                "**알림받기**",
                "",
                "────────────",  # 요청하신 '컨테이너 막대기' 형태 (가독성 유지)
                "이제 재고 올때마다 알림 받으실 수 있습니다",
                "버튼 한번더 누르시면 알림받기 취소됩니다"
            ]
        else:
            if role:
                try:
                    await member.remove_roles(role, reason="입고알림 구독 취소")
                except:
                    pass
            msg_lines = [
                "**알림받기 취소**",
                "",
                "────────────",
                "이제 재고 알림을 받지 않습니다",
                "다시 누르면 알림을 다시 받습니다."
            ]
        view = ui.LayoutView(timeout=60)
        cont = ui.Container(ui.TextDisplay("\n".join(msg_lines)))
        cont.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        view.add_item(cont)
        await interaction.response.send_message(view=view, ephemeral=True)

    # 내 정보
    async def on_my_info_click(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        try:
            if guild is None:
                await interaction.response.send_message("이 명령은 서버에서만 사용할 수 있습니다.", ephemeral=True)
                return
            user_doc = await bot.db_get_user(guild.id, member.id)
            balance = user_doc.get("balance", 0)
            total = user_doc.get("total", 0)
            tx_count = user_doc.get("tx_count", 0)
            tx_list = await bot.db_get_recent_tx(guild.id, member.id, limit=10)
        except Exception:
            await interaction.response.send_message("DB 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.", ephemeral=True)
            return

        view = ui.LayoutView(timeout=120)
        cont = ui.Container(ui.TextDisplay(f"**{member.display_name}님 정보**"))
        cont.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        cont.add_item(ui.TextDisplay(f"**보유 금액** = __{balance}__원"))
        cont.add_item(ui.TextDisplay(f"**누적 금액** = __{total}__원"))
        cont.add_item(ui.TextDisplay(f"**거래 횟수** = __{tx_count}__번"))
        cont.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        cont.add_item(ui.TextDisplay("항상 이용해주시어 감사합니다."))
        view.add_item(cont)

        # 거래 내역이 있으면, 컨테이너 안에 드롭다운 추가 (ActionRow로)
        if tx_list:
            opts = [SelectOption(label=f"{t['created_at']} | {t.get('type','거래')} | {t.get('amount',0)}원", value=str(t["_id"])) for t in tx_list]
            select = ui.Select(placeholder="거래 내역 보기", options=opts, min_values=1, max_values=1)
            async def sel_cb(sel_inter: discord.Interaction):
                try:
                    selected = sel_inter.data["values"][0]
                    tx = await bot.db_get_tx_by_id(selected)
                    if not tx:
                        await sel_inter.response.send_message("거래 내역을 불러오지 못했습니다.", ephemeral=True)
                        return
                    dview = ui.LayoutView(timeout=60)
                    dc = ui.Container(ui.TextDisplay("**거래 내역 상세**"))
                    dc.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    dc.add_item(ui.TextDisplay(f"거래 ID: {tx['_id']}"))
                    dc.add_item(ui.TextDisplay(f"종류: {tx.get('type','알수없음')}"))
                    dc.add_item(ui.TextDisplay(f"금액: {tx.get('amount',0)}원"))
                    dc.add_item(ui.TextDisplay(f"설명: {tx.get('note','-')}"))
                    dc.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    dview.add_item(dc)
                    await sel_inter.response.send_message(view=dview, ephemeral=True)
                except Exception:
                    await sel_inter.response.send_message("상호작용 처리 중 오류가 발생했습니다.", ephemeral=True)
            select.callback = sel_cb
            row = ui.ActionRow(select)
            view.add_item(row)

        await interaction.response.send_message(view=view, ephemeral=True)

    # 구매 흐름 (간단히 유지)
    async def on_purchase_click(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        if guild is None:
            await interaction.response.send_message("서버에서만 사용 가능합니다.", ephemeral=True)
            return
        # 사용 제한 체크
        user_doc = await bot.db_get_user(guild.id, member.id)
        if user_doc.get("banned", 0) == 1 or user_doc.get("can_use",1) == 0:
            view = ui.LayoutView(timeout=30)
            c = ui.Container(ui.TextDisplay("**사용불가**"))
            c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(ui.TextDisplay("현재 자판기 이용이 제한되었습니다\n자세한 이유를 알고 싶으면 문의해주세요"))
            view.add_item(c)
            await interaction.response.send_message(view=view, ephemeral=True)
            return

        categories = await bot.db_get_categories()
        if not categories:
            await interaction.response.send_message("등록된 제품이 없습니다. 관리자에게 문의하세요.", ephemeral=True)
            return

        opts = [SelectOption(label=c, value=c) for c in categories]
        select = ui.Select(placeholder="카테고리 선택", options=opts, min_values=1, max_values=1)
        async def cat_cb(sel_inter: discord.Interaction):
            try:
                cat = sel_inter.data["values"][0]
                products = await bot.db_get_products_by_category(cat)
                if not products:
                    await sel_inter.response.send_message("해당 카테고리에 제품이 없습니다.", ephemeral=True)
                    return
                prod_opts = [SelectOption(label=f"{p['name']} | {p['price']}원 | 재고:{p.get('stock',0)}", value=str(p['_id'])) for p in products]
                prod_select = ui.Select(placeholder="제품 선택", options=prod_opts, min_values=1, max_values=1)
                async def prod_cb(prod_inter: discord.Interaction):
                    try:
                        pid = prod_inter.data["values"][0]
                        # 간단 수량 모달
                        class QtyModal(ui.Modal):
                            def __init__(self):
                                super().__init__(title="구매 수량 입력")
                                self.qty = ui.TextInput(label="구매 수량", style=TextStyle.short, placeholder="숫자만 입력", required=True)
                                self.add_item(self.qty)
                            async def on_submit(self, modal_inter: discord.Interaction):
                                try:
                                    qty = int(self.qty.value)
                                    if qty <= 0:
                                        raise ValueError
                                except:
                                    await modal_inter.response.send_message("올바른 수량을 입력해주세요.", ephemeral=True)
                                    return
                                prod = await bot.db_get_product_by_id(pid)
                                if prod is None:
                                    await modal_inter.response.send_message("제품 정보를 불러오지 못했습니다.", ephemeral=True)
                                    return
                                if prod.get("stock",0) < qty:
                                    await modal_inter.response.send_message("재고가 부족합니다.", ephemeral=True)
                                    return
                                total_price = prod["price"] * qty
                                user_doc2 = await bot.db_get_user(guild.id, member.id)
                                if user_doc2.get("balance",0) < total_price:
                                    await modal_inter.response.send_message("보유 금액이 부족합니다.", ephemeral=True)
                                    return
                                # 차감 및 기록, 재고업데이트
                                await bot.db_record_transaction(guild.id, member.id, -total_price, ttype="구매", note=f"{prod['name']} x{qty}")
                                await bot.db_update_stock(pid, -qty)
                                # DM, 성공 메시지
                                try:
                                    dm_view = ui.LayoutView(timeout=30)
                                    dc = ui.Container(ui.TextDisplay("구매 제품"))
                                    dc.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                                    dc.add_item(ui.TextDisplay(f"구매한 제품 = {prod['name']} x{qty}"))
                                    dc.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                                    dc.add_item(ui.TextDisplay("구매해주셔서 감사합니다."))
                                    dm_view.add_item(dc)
                                    await member.send(view=dm_view)
                                except:
                                    pass
                                success_view = ui.LayoutView(timeout=30)
                                sc = ui.Container(ui.TextDisplay("**구매 성공**"))
                                sc.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                                sc.add_item(ui.TextDisplay(f"**제품 이름** = {prod['name']}"))
                                sc.add_item(ui.TextDisplay(f"**구매 개수** = {qty}"))
                                sc.add_item(ui.TextDisplay(f"**차감 금액** = {total_price}원"))
                                sc.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                                sc.add_item(ui.TextDisplay("성공적으로 구매 완료되었습니다."))
                                success_view.add_item(sc)
                                await modal_inter.response.send_message(view=success_view, ephemeral=True)
                            async def on_error(self, modal_inter: discord.Interaction, error: Exception):
                                await modal_inter.response.send_message("처리 중 오류가 발생했습니다.", ephemeral=True)
                        await prod_inter.response.send_modal(QtyModal())
                    except Exception:
                        await prod_inter.response.send_message("제품 선택 처리 중 오류가 발생했습니다.", ephemeral=True)
                prod_select.callback = prod_cb
                new_view = ui.LayoutView(timeout=120)
                new_view.add_item(ui.Container(ui.TextDisplay("**제품**\n\n원하시는 제품 선택해주세요")))
                new_view.add_item(ui.ActionRow(prod_select))
                await sel_inter.response.edit_message(view=new_view)
            except Exception:
                await sel_inter.response.send_message("카테고리 선택 처리 중 오류가 발생했습니다.", ephemeral=True)
        select.callback = cat_cb
        v = ui.LayoutView(timeout=120)
        v.add_item(ui.Container(ui.TextDisplay("**카테고리**\n\n원하시는 카테고리 선택해주세요")))
        v.add_item(ui.ActionRow(select))
        await interaction.response.send_message(view=v, ephemeral=True)

# ------------------ MongoDB 연동 함수들 (bot에 주입) ------------------
async def db_connect():
    bot.mongo_client = AsyncIOMotorClient(MONGO_URI)
    db = bot.mongo_client.get_default_database() or bot.mongo_client["your_db"]
    bot.db = db
    # 컬렉션 이름
    bot.users_col = db["users"]
    bot.tx_col = db["transactions"]
    bot.products_col = db["products"]
    bot.sub_col = db["subscriptions"]
    bot.bans_col = db["bans"]
    # 인덱스(필요하면 추가)
    try:
        await bot.users_col.create_index([("guild_id",1),("user_id",1)], unique=True)
        await bot.tx_col.create_index([("guild_id",1),("user_id",1),("created_at",-1)])
        await bot.products_col.create_index([("product_id",1)], unique=True)
    except:
        pass

# helper: user doc 생성/조회
async def db_get_user(guild_id, user_id):
    doc = await bot.users_col.find_one({"guild_id": int(guild_id), "user_id": int(user_id)})
    if doc:
        # ensure fields
        return {
            "balance": doc.get("balance",0),
            "total": doc.get("total",0),
            "tx_count": doc.get("tx_count",0),
            "can_use": doc.get("can_use",1),
            "banned": doc.get("banned",0)
        }
    else:
        return {"balance":0,"total":0,"tx_count":0,"can_use":1,"banned":0}

async def db_record_transaction(guild_id, user_id, amount, ttype="거래", note=""):
    now = datetime.utcnow().isoformat(sep=' ', timespec='seconds')
    tx = {"guild_id":int(guild_id),"user_id":int(user_id),"amount":int(amount),"type":ttype,"note":note,"created_at":now}
    # 생성 _id by insert_one
    res = await bot.tx_col.insert_one(tx)
    # upsert users
    await bot.users_col.update_one(
        {"guild_id":int(guild_id),"user_id":int(user_id)},
        {"$inc":{"balance":amount,"total":amount,"tx_count":1}},
        upsert=True
    )
    return str(res.inserted_id)

async def db_get_recent_tx(guild_id, user_id, limit=10):
    cursor = bot.tx_col.find({"guild_id":int(guild_id),"user_id":int(user_id)}).sort("created_at",-1).limit(limit)
    docs = []
    async for d in cursor:
        d["_id"] = str(d.get("_id"))
        docs.append(d)
    return docs

async def db_get_tx_by_id(tx_id):
    try:
        obj = ObjectId(tx_id)
    except:
        # maybe string id generated differently
        return await bot.tx_col.find_one({"_id": tx_id})
    d = await bot.tx_col.find_one({"_id": obj})
    if d:
        d["_id"] = str(d.get("_id"))
    return d

# subscription toggle
async def db_toggle_subscription(guild_id, user_id):
    doc = await bot.sub_col.find_one({"guild_id":int(guild_id),"user_id":int(user_id)})
    if doc is None:
        await bot.sub_col.insert_one({"guild_id":int(guild_id),"user_id":int(user_id),"notify":1})
        return True
    else:
        new_val = 0 if doc.get("notify",1)==1 else 1
        await bot.sub_col.update_one({"guild_id":int(guild_id),"user_id":int(user_id)}, {"$set":{"notify":new_val}})
        return new_val==1

# products helpers
async def db_add_product(product_id, emoji, name, category, price, stock):
    await bot.products_col.update_one({"product_id":product_id},{"$set":{"emoji":emoji,"name":name,"category":category,"price":int(price),"stock":int(stock)}}, upsert=True)

async def db_remove_product(product_id):
    await bot.products_col.delete_one({"product_id":product_id})

async def db_get_categories():
    cursor = bot.products_col.distinct("category")
    return await bot.products_col.distinct("category")

async def db_get_products_by_category(category):
    cursor = bot.products_col.find({"category":category})
    docs = []
    async for d in cursor:
        d["_id"] = str(d.get("_id"))
        docs.append(d)
    return docs

async def db_get_product_by_id(product_id):
    doc = await bot.products_col.find_one({"_id": ObjectId(product_id)}) if ObjectId.is_valid(product_id) else await bot.products_col.find_one({"product_id":product_id})
    if doc:
        doc["_id"] = str(doc.get("_id"))
    return doc

async def db_update_stock(product_identifier, delta):
    # accept product_id or _id string
    if ObjectId.is_valid(product_identifier):
        await bot.products_col.update_one({"_id": ObjectId(product_identifier)}, {"$inc":{"stock":int(delta)}})
        doc = await bot.products_col.find_one({"_id": ObjectId(product_identifier)})
    else:
        await bot.products_col.update_one({"product_id":product_identifier}, {"$inc":{"stock":int(delta)}})
        doc = await bot.products_col.find_one({"product_id":product_identifier})
    return doc.get("stock") if doc else None

# bans
async def db_set_ban(guild_id, user_id, banned, reason=""):
    await bot.bans_col.update_one({"guild_id":int(guild_id),"user_id":int(user_id)}, {"$set":{"banned":int(banned),"reason":reason}}, upsert=True)
    await bot.users_col.update_one({"guild_id":int(guild_id),"user_id":int(user_id)}, {"$set":{"can_use":0 if banned else 1}}, upsert=True)

# 주입
bot.db_connect = db_connect
bot.db_get_user = db_get_user
bot.db_record_transaction = db_record_transaction
bot.db_get_recent_tx = db_get_recent_tx
bot.db_get_tx_by_id = db_get_tx_by_id
bot.db_toggle_subscription = db_toggle_subscription
bot.db_add_product = db_add_product
bot.db_remove_product = db_remove_product
bot.db_get_categories = db_get_categories
bot.db_get_products_by_category = db_get_products_by_category
bot.db_get_product_by_id = db_get_product_by_id
bot.db_update_stock = db_update_stock
bot.db_set_ban = db_set_ban

# ------------------ 명령(한글 옵션 포함) ------------------
def is_guild_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator

@bot.tree.command(name="금액관리", description="유저 금액을 추가하거나 차감합니다. (관리자 전용)")
@app_commands.describe(member="대상 유저", amount="변동 금액(양수)", action="추가 또는 차감")
@app_commands.choices(action=[
    app_commands.Choice(name="추가", value="add"),
    app_commands.Choice(name="차감", value="sub")
])
async def cmd_money_manage(interaction: discord.Interaction, member: discord.Member, amount: int, action: app_commands.Choice[str]):
    if not is_guild_admin(interaction):
        await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        return
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("서버에서만 사용 가능합니다.", ephemeral=True)
        return
    amt = abs(int(amount))
    if action.value == "sub":
        amt = -amt
    await bot.db_record_transaction(guild.id, member.id, amt, ttype=("관리자추가" if amt>0 else "관리자차감"), note=f"관리자:{interaction.user}")
    user_info = await bot.db_get_user(guild.id, member.id)
    new_balance = user_info.get("balance", 0)
    if amt > 0:
        title = "**금액추가**"
        lines = [
            f"**유저** = __{member.display_name}__",
            f"**추가 금액** = __{amt}__원",
            f"**추가 후 금액** = __{new_balance}__원"
        ]
    else:
        title = "**금액차감**"
        lines = [
            f"**유저** = __{member.display_name}__",
            f"**차감 금액** = __{abs(amt)}__원",
            f"**차감 후 금액** = __{new_balance}__원"
        ]
    view = ui.LayoutView(timeout=60)
    cont = ui.Container(ui.TextDisplay(f"{title}\n\n────────────\n" + "\n".join(lines)))
    cont.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    view.add_item(cont)
    await interaction.response.send_message(view=view, ephemeral=False)

@bot.tree.command(name="이용제한", description="유저의 자판기 사용을 차단하거나 허용합니다. (관리자 전용)")
@app_commands.describe(member="대상 유저", mode="사용 또는 차단")
@app_commands.choices(mode=[
    app_commands.Choice(name="사용", value="use"),
    app_commands.Choice(name="차단", value="ban")
])
async def cmd_ban_manage(interaction: discord.Interaction, member: discord.Member, mode: app_commands.Choice[str]):
    if not is_guild_admin(interaction):
        await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        return
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("서버에서만 사용 가능합니다.", ephemeral=True)
        return
    banned = 0 if mode.value == "use" else 1
    await bot.db_set_ban(guild.id, member.id, banned, reason=f"관리자:{interaction.user}")
    user_info = await bot.db_get_user(guild.id, member.id)
    can_use = "사용 가능" if user_info.get("can_use",1)==1 else "사용 불가"
    view = ui.LayoutView(timeout=60)
    cont = ui.Container(ui.TextDisplay("**자판기 사용 여부**\n\n────────────\n" + f"**유저** = __{member.display_name}__\n**사용 가능 여부** = __{can_use}__"))
    cont.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    view.add_item(cont)
    await interaction.response.send_message(view=view, ephemeral=False)

@bot.tree.command(name="제품설정", description="제품을 추가/삭제합니다. (관리자 전용)")
async def cmd_product_manage(interaction: discord.Interaction):
    if not is_guild_admin(interaction):
        await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        return
    opts = [SelectOption(label="제품추가", value="add"), SelectOption(label="제품삭제", value="remove")]
    select = ui.Select(placeholder="작업 선택", options=opts, min_values=1, max_values=1)
    async def sel_cb(sel_inter: discord.Interaction):
        try:
            choice = sel_inter.data["values"][0]
            if choice == "add":
                class AddModal(ui.Modal):
                    def __init__(self):
                        super().__init__(title="제품 추가")
                        self.emoji = ui.TextInput(label="이모지", required=True, placeholder="예: <:name:123456> 또는 EMOJI_0")
                        self.name = ui.TextInput(label="제품 이름", required=True, placeholder="예: 콜라")
                        self.category = ui.TextInput(label="카테고리", required=True, placeholder="예: 음료")
                        self.price = ui.TextInput(label="가격", required=True, placeholder="숫자만")
                        self.stock = ui.TextInput(label="초기 재고", required=True, placeholder="숫자만")
                        self.add_item(self.emoji); self.add_item(self.name); self.add_item(self.category); self.add_item(self.price); self.add_item(self.stock)
                    async def on_submit(self, modal_inter: discord.Interaction):
                        try:
                            price_v = int(self.price.value); stock_v = int(self.stock.value)
                        except:
                            await modal_inter.response.send_message("가격과 재고는 숫자로 입력해주세요.", ephemeral=True); return
                        pid = f"{int(datetime.utcnow().timestamp()*1000)}_{self.name.value}"
                        await bot.db_add_product(pid, self.emoji.value, self.name.value, self.category.value, price_v, stock_v)
                        view = ui.LayoutView(timeout=60)
                        c = ui.Container(ui.TextDisplay("**제품추가**\n\n────────────\n" + f"**이모지** = {self.emoji.value}\n**제품 이름** = {self.name.value}\n**카테고리** = {self.category.value}\n**가격** = {price_v}원"))
                        c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                        view.add_item(c)
                        await modal_inter.response.send_message(view=view, ephemeral=False)
                await sel_inter.response.send_modal(AddModal())
            else:
                cursor = bot.products_col.find({})
                rows = []
                async for r in cursor:
                    rows.append((r.get("product_id"), r.get("name")))
                if not rows:
                    await sel_inter.response.send_message("등록된 제품이 없습니다.", ephemeral=True); return
                opts2 = [SelectOption(label=r[1], value=r[0]) for r in rows]
                rem_sel = ui.Select(placeholder="삭제할 제품 선택", options=opts2, min_values=1, max_values=1)
                async def rem_cb(rem_inter: discord.Interaction):
                    try:
                        pid = rem_inter.data["values"][0]
                        await bot.db_remove_product(pid)
                        await rem_inter.response.send_message("제품을 삭제했습니다.", ephemeral=True)
                    except:
                        await rem_inter.response.send_message("제품 삭제 중 오류가 발생했습니다.", ephemeral=True)
                rem_sel.callback = rem_cb
                new_view = ui.LayoutView(timeout=60)
                new_view.add_item(ui.Container(ui.TextDisplay("제품을 선택하세요")))
                new_view.add_item(ui.ActionRow(rem_sel))
                await sel_inter.response.edit_message(view=new_view)
        except Exception:
            await sel_inter.response.send_message("작업 처리 중 오류가 발생했습니다.", ephemeral=True)
    select.callback = sel_cb
    view = ui.LayoutView(timeout=60)
    cont = ui.Container(ui.TextDisplay("**제품설정**\n\n────────────\n아래 드롭바를 눌러 제품 설정해주세요"))
    cont.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    view.add_item(cont)
    view.add_item(ui.ActionRow(select))
    await interaction.response.send_message(view=view, ephemeral=False)

@bot.tree.command(name="재고추가", description="제품 재고를 추가합니다. (관리자 전용)")
async def cmd_stock_add(interaction: discord.Interaction):
    if not is_guild_admin(interaction):
        await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True); return
    rows = []
    cursor = bot.products_col.find({})
    async for r in cursor:
        rows.append((r.get("product_id"), r.get("name")))
    if not rows:
        await interaction.response.send_message("등록된 제품이 없습니다.", ephemeral=True); return
    opts = [SelectOption(label=r[1], value=r[0]) for r in rows]
    sel = ui.Select(placeholder="재고 추가할 제품 선택", options=opts, min_values=1, max_values=1)
    async def sel_cb(sel_inter: discord.Interaction):
        try:
            pid = sel_inter.data["values"][0]
            class StockModal(ui.Modal):
                def __init__(self):
                    super().__init__(title="재고 추가")
                    self.qty = ui.TextInput(label="추가할 재고 수량", required=True, placeholder="숫자만")
                    self.add_item(self.qty)
                async def on_submit(self, modal_inter: discord.Interaction):
                    try:
                        q = int(self.qty.value)
                    except:
                        await modal_inter.response.send_message("숫자만 입력해주세요.", ephemeral=True); return
                    new_stock = await bot.db_update_stock(pid, q)
                    prod = await bot.db_get_product_by_id(pid)
                    name_v = prod.get("name") if prod else "알수없음"
                    view = ui.LayoutView(timeout=60)
                    c = ui.Container(ui.TextDisplay("**재고추가**\n\n────────────\n" + f"**제품 이름** = {name_v}\n**추가된 재고 개수** = {q}개"))
                    c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    view.add_item(c)
                    await modal_inter.response.send_message(view=view, ephemeral=False)
            await sel_inter.response.send_modal(StockModal())
        except:
            await sel_inter.response.send_message("재고 추가 처리 중 오류가 발생했습니다.", ephemeral=True)
    sel.callback = sel_cb
    new_view = ui.LayoutView(timeout=60)
    cont = ui.Container(ui.TextDisplay("**재고추가**\n\n────────────\n드롭바를 눌러 재고 추가해주세요"))
    cont.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    new_view.add_item(cont)
    new_view.add_item(ui.ActionRow(sel))
    await interaction.response.send_message(view=new_view, ephemeral=False)

# 기존 누락/자판기 패널 명령 유지
@bot.tree.command(name="누락패널", description="누락 보상 패널을 표시합니다")
async def button_panel_nurak(interaction: discord.Interaction):
    layout = MyLayout()
    await interaction.response.send_message(view=layout, ephemeral=False)

@bot.tree.command(name="자판기패널", description="자판기 패널을 표시합니다")
async def button_panel_vending(interaction: discord.Interaction):
    layout = MyLayoutVending()
    await interaction.response.send_message(view=layout, ephemeral=False)

# ------------------ on_ready에서 Mongo 연결 ------------------
@bot.event
async def on_ready():
    try:
        await bot.db_connect()
        print("MongoDB 연결 성공")
    except Exception as e:
        print("MongoDB 연결 실패:", e)
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 명령어가 동기화되었습니다.')
    except Exception as e:
        print("명령어 동기화 중 오류:", e)
    print(f"로벅스 자판기 봇이 {bot.user}로 로그인했습니다.")

# ------------------ 실행 ------------------
# DISCORD_TOKEN은 .env에 넣거나 아래에 직접 입력하세요
bot.run(os.getenv("DISCORD_TOKEN") or "")
