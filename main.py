import os
import discord
import aiohttp
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

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
        try: await interaction.response.defer()
        except: pass
        return False

@tree.command(name="버튼패널", description="자동 로벅스 자판기 패널을 공개로 표시합니다.")
async def cmd_button_panel(inter: Interaction):
    await inter.response.send_message(embed=make_panel_embed(), view=PanelView(), ephemeral=False)

API = "https://discord.com/api/v10"

async def get_app_id(session: aiohttp.ClientSession) -> str:
    async with session.get(f"{API}/oauth2/applications/@me", headers={"Authorization": f"Bot {TOKEN}"}) as r:
        js = await r.json()
        if r.status != 200:
            raise RuntimeError(f"get app failed: {r.status} {js}")
        return js["id"]

async def put_commands(session: aiohttp.ClientSession, app_id: str, scope: str, guild_id: int | None, body):
    # scope: "global" or "guild"
    if scope == "global":
        url = f"{API}/applications/{app_id}/commands"
    else:
        if not guild_id: raise RuntimeError("guild_id required for guild scope")
        url = f"{API}/applications/{app_id}/guilds/{guild_id}/commands"
    async with session.put(url, headers={"Authorization": f"Bot {TOKEN}"}, json=body) as r:
        js = await r.json()
        if r.status not in (200, 201):
            raise RuntimeError(f"put {scope} cmds failed: {r.status} {js}")
        return js

async def hard_reset_commands(panel_only: bool = True):
    async with aiohttp.ClientSession() as session:
        app_id = await get_app_id(session)
        # 1) 전역 명령 전체 삭제(= 빈 배열로 덮어쓰기)
        await put_commands(session, app_id, "global", None, body=[])
        print("[CLEAN][GLOBAL] cleared")

        # 2) 길드 명령 전체 삭제(= 빈 배열로 덮어쓰기)
        if GUILD_ID:
            await put_commands(session, app_id, "guild", GUILD_ID, body=[])
            print(f"[CLEAN][GUILD {GUILD_ID}] cleared")

        # 3) 패널만 다시 등록(길드에만)
        if panel_only and GUILD_ID:
            body = [{
                "name": "버튼패널",
                "type": 1,
                "description": "자동 로벅스 자판기 패널을 공개로 표시합니다."
            }]
            await put_commands(session, app_id, "guild", GUILD_ID, body=body)
            print(f"[SET][GUILD {GUILD_ID}] set panel-only")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        await hard_reset_commands(panel_only=True)
    except Exception as e:
        print("[RESET][ERR]", e)

    # 트리 싱크(혹시 모를 캐시 반영 보조)
    try:
        if GUILD_ID:
            await tree.sync(guild=discord.Object(id=GUILD_ID))
            print(f"[SYNC] guild {GUILD_ID} panel-only")
        else:
            await tree.sync()
            print("[SYNC] global (empty) — no commands")
    except Exception as e:
        print("[SYNC][ERR]", e)

def main():
    if not TOKEN or len(TOKEN) < 10:
        raise RuntimeError("DISCORD_TOKEN 비정상")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
