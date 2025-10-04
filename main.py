import os
import json
import time
import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from dotenv import load_dotenv
from typing import Dict, Any, List

# ============ ENV ============
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ============ BOT ============
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ============ 간단 DB(JSON 파일) ============
DATA_PATH = "data.json"

def _load_db() -> Dict[str, Any]:
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump({"users": {}}, f, ensure_ascii=False, indent=2)
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_db(db: Dict[str, Any]):
    tmp = DATA_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_PATH)

def _ensure_user(uid: int) -> Dict[str, Any]:
    db = _load_db()
    u = db["users"].get(str(uid))
    if not u:
        u = {"wallet": 0, "total": 0, "count": 0, "recent": []}  # wallet, total, count, recent[ {desc, amount, ts} ]
        db["users"][str(uid)] = u
        _save_db(db)
    return u

def get_user_stats(uid: int) -> Dict[str, Any]:
    return _ensure_user(uid)

def add_tx(uid: int, amount: int, desc: str):
    db = _load_db()
    u = db["users"].setdefault(str(uid), {"wallet":0,"total":0,"count":0,"recent":[]})
    # 보유금액은 예시로 관리하지만, 요청엔 필수는 아님.
    u["wallet"] = max(0, int(u.get("wallet", 0) + amount))
    if amount > 0:
        u["total"] = int(u.get("total", 0) + amount)
    u["count"]  = int(u.get("count", 0) + 1)
    rec = u.get("recent", [])
    rec.insert(0, {"desc": desc, "amount": int(amount), "ts": int(time.time())})
    u["recent"] = rec[:5]
    db["users"][str(uid)] = u
    _save_db(db)

# ============ PartialEmoji ============
def pe(emoji_id: int, name: str = None, animated: bool = False) -> discord.PartialEmoji:
    return discord.PartialEmoji(name=name, id=emoji_id, animated=animated)

EMOJI_NOTICE = pe(1424003478275231916, name="emoji_5", animated=False)   # <:emoji_5:...>
EMOJI_CHARGE = pe(1381244136627245066, name="charge",  animated=False)   # <:charge:...>
EMOJI_INFO   = pe(1381244138355294300, name="info",    animated=False)   # <:info:...>
EMOJI_BUY    = pe(1381244134680957059, name="category",animated=False)   # <:category:...>

# ============ 임베드 ============
PINK = discord.Colour(int("ff5dd6", 16))
GRAY = discord.Colour.dark_grey()

def embed_panel() -> Embed:
    # 서버명/프사 표시 없이
    return Embed(
        title="자동 로벅스 자판기",
        description="아래 버튼을 눌려 이용해주세요!",
        colour=PINK
    )

def embed_notice(guild: discord.Guild | None) -> Embed:
    # 회색, 에페메럴
    emb = Embed(title="공지", description="<#1419230737244229653> 필독 부탁드립니다", colour=GRAY)
    return emb

def embed_myinfo(user: discord.User | discord.Member, stats: Dict[str, Any]) -> Embed:
    # 회색, 오른쪽 썸네일 유저 프로필, 본문에 값들
    emb = Embed(title=f"{user.display_name if hasattr(user,'display_name') else user.name}님 정보", colour=GRAY)
    wallet = int(stats.get("wallet", 0))
    total  = int(stats.get("total", 0))
    count  = int(stats.get("count", 0))
    emb.description = "\n".join([
        f"### 보유 금액 : {wallet:,}원",
        f"### 누적 금액 : {total:,}원",
        f"### 거래 횟수 : {count:,}번",
        "",
        "최근 거래 내역 5개"
    ])
    try:
        emb.set_thumbnail(url=user.display_avatar.url)
    except Exception:
        pass
    return emb

# ============ 드롭다운(최근거래) ============
class TxSelect(discord.ui.Select):
    def __init__(self, entries: List[Dict[str, Any]]):
        options = []
        if entries:
            for i, e in enumerate(entries):
                label = f"{e.get('desc','거래')} / {int(e.get('amount',0)):,}원"
                options.append(discord.SelectOption(label=label[:100], value=str(i)))
        else:
            options = [discord.SelectOption(label="거래 내역 없음", value="none", default=True)]
        super().__init__(placeholder="최근 거래내역 보기", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        # 선택만 받고 별도 안내는 안 띄움(요청 사항: 에페메럴 유지, 조용히 처리)
        try:
            await interaction.response.defer()
        except Exception:
            pass

# ============ 버튼 뷰(2x2 회색) ============
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # 1행
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="공지",   emoji=EMOJI_NOTICE, custom_id="panel_notice", row=0))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="충전",   emoji=EMOJI_CHARGE, custom_id="panel_charge", row=0))
        # 2행
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="내 정보", emoji=EMOJI_INFO,   custom_id="panel_info",   row=1))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="구매",   emoji=EMOJI_BUY,    custom_id="panel_buy",    row=1))

    async def interaction_check(self, interaction: Interaction) -> bool:
        # 버튼 눌러도 공개 채팅에 추가 메시지 안 남김
        try:
            await interaction.response.defer()
        except Exception:
            pass

        cid = (interaction.data or {}).get("custom_id")
        uid = interaction.user.id

        # 길드 제한 없이 어느 길드에서 눌러도 동작
        if cid == "panel_notice":
            emb = embed_notice(interaction.guild)
            # 나만 보이게
            try:
                await interaction.followup.send(embed=emb, ephemeral=True)
            except Exception:
                pass

        elif cid == "panel_info":
            stats = get_user_stats(uid)
            emb = embed_myinfo(interaction.user, stats)
            view = discord.ui.View(timeout=None)
            view.add_item(TxSelect(stats.get("recent", [])))
            try:
                await interaction.followup.send(embed=emb, view=view, ephemeral=True)
            except Exception:
                pass

        elif cid == "panel_charge":
            # 예시: +1000원 충전 → 누적/횟수 반영(실서비스 로직으로 대체 가능)
            add_tx(uid, 1000, "충전")
            stats = get_user_stats(uid)
            emb = embed_myinfo(interaction.user, stats)
            view = discord.ui.View(timeout=None)
            view.add_item(TxSelect(stats.get("recent", [])))
            try:
                await interaction.followup.send(content="충전 완료!", embed=emb, view=view, ephemeral=True)
            except Exception:
                pass

        elif cid == "panel_buy":
            # 예시: -500원 구매 → 횟수만 증가, total은 증가 안 함(수입 개념이 아니므로)
            add_tx(uid, -500, "구매")
            stats = get_user_stats(uid)
            emb = embed_myinfo(interaction.user, stats)
            view = discord.ui.View(timeout=None)
            view.add_item(TxSelect(stats.get("recent", [])))
            try:
                await interaction.followup.send(content="구매 처리 완료!", embed=emb, view=view, ephemeral=True)
            except Exception:
                pass

        return False

# ============ 슬래시: /버튼패널 (전 길드 공용) ============
@tree.command(name="버튼패널", description="자동 로벅스 자판기 패널을 공개로 표시합니다.")
async def 버튼패널(inter: Interaction):
    await inter.response.send_message(embed=embed_panel(), view=PanelView(), ephemeral=False)

# ============ on_ready ============
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    # 전역 등록(여러 길드에서 즉시 보이게 하려면 전역 싱크; 전파 1~60분 가능)
    # 빠른 반영을 원하면 길드별 개별 sync가 필요하지만, 요청은 '여러 길드 가능'이라 전역으로 올린다.
    try:
        await tree.sync()
        print("[SYNC] global commands synced (/버튼패널)")
    except Exception as e:
        print("[SYNC][ERR]", e)

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN 비정상")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
