import os
import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from dotenv import load_dotenv

# ===== env =====
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

# ===== client =====
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ===== emoji helper =====
def pe(eid: int, name: str = None, animated: bool = False) -> discord.PartialEmoji:
    return discord.PartialEmoji(name=name, id=eid, animated=animated)

EMOJI_NOTICE = pe(1424003478275231916, name="emoji_5", animated=False)
EMOJI_CHARGE = pe(1381244136627245066, name="charge",  animated=False)
EMOJI_INFO   = pe(1381244138355294300, name="info",    animated=False)
EMOJI_BUY    = pe(1381244134680957059, name="category",animated=False)

# ===== embed =====
def make_panel_embed() -> Embed:
    return Embed(
        title="자동 로벅스 자판기",
        description="아래 버튼을 눌려 이용해주세요!",
        colour=discord.Colour(int("ff5dd6", 16))
    )

# ===== view =====
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="공지",   emoji=EMOJI_NOTICE, custom_id="panel_notice", row=0))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="충전",   emoji=EMOJI_CHARGE, custom_id="panel_charge", row=0))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="내 정보", emoji=EMOJI_INFO,   custom_id="panel_info",   row=1))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="구매",   emoji=EMOJI_BUY,    custom_id="panel_buy",    row=1))

    async def interaction_check(self, interaction: Interaction) -> bool:
        try:
            await interaction.response.defer()
        except Exception:
            pass
        return False

# ===== slash: 패널만 등록 =====
@tree.command(name="버튼패널", description="자동 로벅스 자판기 패널을 공개로 표시합니다.")
async def cmd_button_panel(inter: Interaction):
    await inter.response.send_message(embed=make_panel_embed(), view=PanelView(), ephemeral=False)

# ===== command cleanup =====
TARGET_HIDE = {"재고카드", "재고패널"}  # 절대 보이면 안 되는 이름들
KEEP_ONLY  = {"버튼패널"}              # 유지할 것

async def purge_commands_everywhere():
    try:
        # 1) 길드 커맨드 가져와서 제거
        if GUILD_ID:
            g = discord.Object(id=GUILD_ID)
            guild_cmds = await tree.fetch_commands(guild=g)
            removed = []
            for c in guild_cmds:
                if (c.name in TARGET_HIDE) or (c.name not in KEEP_ONLY and c.name != "버튼패널"):
                    await tree.remove_command(c.name, guild=g)
                    removed.append(c.name)
            if removed:
                await tree.sync(guild=g)
                print(f"[CLEAN] guild removed: {removed}")

        # 2) 전역 커맨드도 가져와서 제거(전파 지연 가능)
        global_cmds = await tree.fetch_commands()
        removed_g = []
        for c in global_cmds:
            if c.name in TARGET_HIDE:
                await tree.remove_command(c.name)
                removed_g.append(c.name)
        if removed_g:
            await tree.sync()
            print(f"[CLEAN] global removed: {removed_g}")

        # 3) 최종: 패널만 등록 상태로 맞추기
        if GUILD_ID:
            await tree.sync(guild=discord.Object(id=GUILD_ID))
            print(f"[SYNC] guild {GUILD_ID} → panel-only")
        else:
            await tree.sync()
            print("[SYNC] global → panel-only (may delay)")
    except Exception as e:
        print("[CLEAN][ERR]", e)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await purge_commands_everywhere()

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN 비정상")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
