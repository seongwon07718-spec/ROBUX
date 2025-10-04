import os
import discord
import aiohttp
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from dotenv import load_dotenv

# ============ ENV ============
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

# ============ CLIENT ============
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ============ EMOJI/VIEW ============
def pe(eid: int, name: str = None, animated: bool = False) -> discord.PartialEmoji:
    return discord.PartialEmoji(name=name, id=eid, animated=animated)

EMOJI_NOTICE = pe(1424003478275231916, name="emoji_5", animated=False)
EMOJI_CHARGE = pe(1381244136627245066, name="charge",  animated=False)
EMOJI_INFO   = pe(1381244138355294300, name="info",    animated=False)
EMOJI_BUY    = pe(1381244134680957059, name="category",animated=False)

def make_panel_embed() -> Embed:
    return Embed(
        title="자동 로벅스 자판기",
        description="아래 버튼을 눌려 이용해주세요!",
        colour=discord.Colour(int("ff5dd6", 16))
    )

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

# ============ 슬래시: 패널만 등록 ============
@tree.command(name="버튼패널", description="자동 로벅스 자판기 패널을 공개로 표시합니다.")
async def cmd_button_panel(inter: Interaction):
    await inter.response.send_message(embed=make_panel_embed(), view=PanelView(), ephemeral=False)

# ============ 하드 삭제(REST) 유틸 ============
API = "https://discord.com/api/v10"

async def get_app_id(session: aiohttp.ClientSession) -> str:
    # 봇 자신의 application 정보
    async with session.get(f"{API}/oauth2/applications/@me", headers={"Authorization": f"Bot {TOKEN}"}) as r:
        js = await r.json()
        if r.status != 200:
            raise RuntimeError(f"get app failed: {r.status} {js}")
        return js["id"]

async def list_guild_commands(session: aiohttp.ClientSession, app_id: str, guild_id: int):
    async with session.get(f"{API}/applications/{app_id}/guilds/{guild_id}/commands", headers={"Authorization": f"Bot {TOKEN}"}) as r:
        js = await r.json()
        if r.status != 200:
            raise RuntimeError(f"list guild cmds failed: {r.status} {js}")
        return js

async def delete_guild_command(session: aiohttp.ClientSession, app_id: str, guild_id: int, cmd_id: str):
    async with session.delete(f"{API}/applications/{app_id}/guilds/{guild_id}/commands/{cmd_id}", headers={"Authorization": f"Bot {TOKEN}"}) as r:
        if r.status not in (200, 204):
            js = await r.text()
            raise RuntimeError(f"delete guild cmd failed: {r.status} {js}")

async def list_global_commands(session: aiohttp.ClientSession, app_id: str):
    async with session.get(f"{API}/applications/{app_id}/commands", headers={"Authorization": f"Bot {TOKEN}"}) as r:
        js = await r.json()
        if r.status != 200:
            raise RuntimeError(f"list global cmds failed: {r.status} {js}")
        return js

async def delete_global_command(session: aiohttp.ClientSession, app_id: str, cmd_id: str):
    async with session.delete(f"{API}/applications/{app_id}/commands/{cmd_id}", headers={"Authorization": f"Bot {TOKEN}"}) as r:
        if r.status not in (200, 204):
            js = await r.text()
            raise RuntimeError(f"delete global cmd failed: {r.status} {js}")

TARGET_REMOVE = {"재고카드", "재고패널"}  # 반드시 지울 이름
KEEP_ONLY = {"버튼패널"}                 # 이 외는 삭제

async def hard_cleanup_commands():
    async with aiohttp.ClientSession() as session:
        app_id = await get_app_id(session)
        removed_names = []

        # 1) 길드 명령 싹 정리
        if GUILD_ID:
            cmds = await list_guild_commands(session, app_id, GUILD_ID)
            for c in cmds:
                name = c.get("name")
                cid = c.get("id")
                if (name in TARGET_REMOVE) or (name not in KEEP_ONLY):
                    await delete_guild_command(session, app_id, GUILD_ID, cid)
                    removed_names.append(f"guild:{name}")

        # 2) 전역 명령에서도 같은 이름 제거(혹시 전역에 남아 있으면)
        gcmds = await list_global_commands(session, app_id)
        for c in gcmds:
            name = c.get("name")
            cid = c.get("id")
            if name in TARGET_REMOVE:
                await delete_global_command(session, app_id, cid)
                removed_names.append(f"global:{name}")

        if removed_names:
            print("[CLEAN][HARD] removed:", removed_names)
        else:
            print("[CLEAN][HARD] nothing to remove")

# ============ on_ready ============
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    # 0) 하드 삭제 먼저 실행(REST로 즉시 삭제)
    try:
        await hard_cleanup_commands()
    except Exception as e:
        print("[CLEAN][ERR]", e)

    # 1) 이제 /버튼패널만 등록되어 있도록 동기화
    try:
        if GUILD_ID:
            await tree.sync(guild=discord.Object(id=GUILD_ID))
            print(f"[SYNC] guild {GUILD_ID} → panel-only")
        else:
            await tree.sync()
            print("[SYNC] global → panel-only (may delay)")
    except Exception as e:
        print("[SYNC][ERR]", e)

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN 비정상")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
