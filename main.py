import os
import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from dotenv import load_dotenv

# .env 로드
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

# 디스코드 클라이언트
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# PartialEmoji 헬퍼
def pe(emoji_id: int, name: str = None, animated: bool = False) -> discord.PartialEmoji:
    return discord.PartialEmoji(name=name, id=emoji_id, animated=animated)

# 요청한 이모지(PartialEmoji)
EMOJI_NOTICE = pe(1424003478275231916, name="emoji_5", animated=False)   # <:emoji_5:1424003478275231916>
EMOJI_CHARGE = pe(1381244136627245066, name="charge",  animated=False)   # <:charge:1381244136627245066>
EMOJI_INFO   = pe(1381244138355294300, name="info",    animated=False)   # <:info:1381244138355294300>
EMOJI_BUY    = pe(1381244134680957059, name="category",animated=False)   # <:category:1381244134680957059>

# 임베드(서버 이름/서버 프사 비표시)
def make_panel_embed() -> Embed:
    colour = discord.Colour(int("ff5dd6", 16))  # 핑크
    emb = Embed(
        title="자동 로벅스 자판기",
        description="아래 버튼을 눌려 이용해주세요!",
        colour=colour
    )
    # emb.set_author(...) 안 씀 → 서버 이름/프사 표시 안 함
    return emb

# 버튼 뷰(2x2, 회색)
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
        return False

# 슬래시 명령: /버튼패널 (공개 표시)
@tree.command(name="버튼패널", description="자동 로벅스 자판기 패널을 공개로 표시합니다.")
async def cmd_button_panel(inter: Interaction):
    emb = make_panel_embed()
    view = PanelView()
    await inter.response.send_message(embed=emb, view=view, ephemeral=False)

# 길드 싱크
async def sync_tree():
    try:
        if GUILD_ID:
            await tree.sync(guild=discord.Object(id=GUILD_ID))
            print(f"[SYNC] guild {GUILD_ID} sync ok")
        else:
            await tree.sync()
            print("[SYNC] global sync ok (전파 지연 가능)")
    except Exception as e:
        print("[SYNC] error:", e)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await sync_tree()

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN 비어있거나 형식 이상")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
