# bot_restore.py
import sqlite3, requests, time, asyncio, uuid
import discord
from discord import app_commands
from discord.ext import commands
from urllib.parse import quote_plus

# ----------------- 설정 (테스트용: 실제 값으로 변경하세요) -----------------
BOT_TOKEN = "여기에_BOT_TOKEN_입력"
CLIENT_ID = "1434868431064272907"
CLIENT_SECRET = "여기에_CLIENT_SECRET_입력"
OWNER = 1402654236570812467  # 소유자 ID (정수)
API_ENDPOINT = "https://discord.com/api/v9"
DATABASE_PATH = "database.db"
BASE_URL = "https://btcclink.duckdns.org"  # web_app.py의 BASE_URL/REDIRECT_URI와 동일하게
MAX_CONCURRENT = 3
# ----------------------------------------------------------------

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)
tree = bot.tree

def start_db():
    con = sqlite3.connect(DATABASE_PATH)
    cur = con.cursor()
    return con, cur

def ensure_schema():
    con, cur = start_db()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guilds (
        id INTEGER PRIMARY KEY,
        token TEXT UNIQUE,
        expiredate TEXT,
        link TEXT,
        icon TEXT
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        token TEXT,
        guild_id INTEGER
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS licenses (
        key TEXT PRIMARY KEY,
        days INTEGER
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guild_settings (
        guild_id INTEGER PRIMARY KEY,
        log_channel_id INTEGER,
        auth_role_id INTEGER
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS state_nonce (
        state TEXT PRIMARY KEY,
        guild_id INTEGER,
        created_at INTEGER
    );""")
    con.commit()
    con.close()

def embeda(t, title, desc, fields=None):
    color_map = {"success":0x5c6cdf,"error":0xff5c5c,"info":0x5c6cdf}
    color = color_map.get(t, 0x5c6cdf)
    embed = discord.Embed(title=title, description=desc, color=color)
    if fields:
        for name,val,inline in fields:
            embed.add_field(name=name, value=val, inline=inline)
    embed.set_footer(text="LinkRestoreBot")
    return embed

def make_oauth_url(guild_id):
    nonce = uuid.uuid4().hex
    state = f"{guild_id}:{nonce}"
    con, cur = start_db()
    cur.execute("INSERT OR REPLACE INTO state_nonce (state, guild_id, created_at) VALUES (?, ?, ?);", (state, guild_id, int(time.time())))
    con.commit()
    con.close()
    scope = quote_plus("identify guilds.join")
    oauth_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={BASE_URL}/join&response_type=code&scope={scope}&state={state}"
    return oauth_url

def refresh_token_sync(refresh_token):
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    headers = {"Content-Type":"application/x-www-form-urlencoded"}
    try:
        r = requests.post(f"{API_ENDPOINT}/oauth2/token", data=data, headers=headers, timeout=10)
    except Exception as e:
        print("refresh_token exception:", e)
        return None
    if r.status_code == 429:
        try:
            info = r.json()
            retry = info.get("retry_after", 1)
        except:
            retry = 2
        time.sleep(retry + 1)
        return refresh_token_sync(refresh_token)
    try:
        return r.json()
    except:
        return None

def add_user_sync(access_token, guild_id, user_id):
    jsonData = {"access_token": access_token}
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    try:
        r = requests.put(f"{API_ENDPOINT}/guilds/{guild_id}/members/{user_id}", json=jsonData, headers=headers, timeout=10)
    except Exception as e:
        print("add_user exception:", e)
        return False
    if r.status_code == 429:
        try:
            retry = r.json().get("retry_after", 1)
        except:
            retry = 2
        time.sleep(retry + 1)
        return add_user_sync(access_token, guild_id, user_id)
    if r.status_code in (201, 204):
        return True
    else:
        print("add_user failed:", r.status_code, r.text)
        return False

class OAuthView(discord.ui.View):
    def __init__(self, oauth_url):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="인증하기", style=discord.ButtonStyle.link, url=oauth_url))

@tree.command(name="인증패널", description="인증 임베드와 OAuth 링크 버튼을 발행합니다. (관리자 전용)")
@app_commands.describe(channel="발행할 채널 (텍스트 채널)")
async def auth_panel(interaction: discord.Interaction, channel: discord.TextChannel):
    if interaction.user.id != OWNER and (not interaction.guild or not interaction.user.guild_permissions.administrator):
        return await interaction.response.send_message("권한이 없습니다. 관리자만 사용 가능합니다.", ephemeral=True)

    con, cur = start_db()
    cur.execute("SELECT auth_role_id FROM guild_settings WHERE guild_id == ?;", (interaction.guild.id,))
    row = cur.fetchone()
    con.close()
    if not row or not row[0]:
        return await interaction.response.send_message("먼저 /역할 명령어로 인증 역할을 설정해 주세요.", ephemeral=True)
    oauth_url = make_oauth_url(interaction.guild.id)
    embed = embeda("info", "인증하기", "아래 버튼을 눌러 Discord 인증을 진행하세요. 인증 완료 시 토큰이 저장되며, 가능한 경우 자동 초대가 시도됩니다.")
    view = OAuthView(oauth_url)
    try:
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"{channel.mention} 채널에 인증 패널을 발행했습니다.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("봇에게 해당 채널에 메시지 전송 권한이 없습니다.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"메시지 발송 실패: {e}", ephemeral=True)

@tree.command(name="역할", description="인증 역할을 설정합니다. (관리자 전용)")
@app_commands.describe(role="설정할 역할")
async def set_role(interaction: discord.Interaction, role: discord.Role):
    if interaction.user.id != OWNER and (not interaction.guild or not interaction.user.guild_permissions.administrator):
        return await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
    con, cur = start_db()
    cur.execute("INSERT INTO guild_settings (guild_id, auth_role_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET auth_role_id=excluded.auth_role_id;", (interaction.guild.id, role.id))
    con.commit()
    con.close()
    await interaction.response.send_message(f"인증 역할이 {role.mention} 으로 설정되었습니다.", ephemeral=True)

async def recover_guild_members(source_guild_id, target_guild_id, followup):
    con, cur = start_db()
    cur.execute("SELECT id, token FROM users WHERE guild_id == ?;", (source_guild_id,))
    rows = cur.fetchall()
    con.close()
    total = len(rows)
    if total == 0:
        await followup.send("복구 대상이 없습니다.", ephemeral=True)
        return

    sem = asyncio.Semaphore(MAX_CONCURRENT)
    loop = asyncio.get_event_loop()
    success = 0
    fail = 0
    done = 0

    await followup.send(f"복구 시작: 총 {total}명. 동시 작업 수 {MAX_CONCURRENT}.", ephemeral=True)

    async def worker(row):
        nonlocal success, fail, done
        user_id, refresh_tok = row[0], row[1]
        async with sem:
            token_data = await loop.run_in_executor(None, refresh_token_sync, refresh_tok)
            if not token_data or "access_token" not in token_data:
                fail += 1
                done += 1
                if done % 10 == 0:
                    await followup.send(f"진행: {done}/{total} (성공:{success} 실패:{fail})", ephemeral=True)
                return
            access_tok = token_data["access_token"]
            new_refresh = token_data.get("refresh_token", refresh_tok)
            added = await loop.run_in_executor(None, add_user_sync, access_tok, target_guild_id, user_id)
            if added:
                success += 1
                try:
                    con, cur = start_db()
                    cur.execute("UPDATE users SET token = ? WHERE id == ?;", (new_refresh, user_id))
                    con.commit()
                    con.close()
                except Exception as e:
                    print("DB update error:", e)
            else:
                fail += 1
            done += 1
            if done % 10 == 0:
                await followup.send(f"진행: {done}/{total} (성공:{success} 실패:{fail})", ephemeral=True)

    tasks = [asyncio.create_task(worker(r)) for r in rows]
    await asyncio.gather(*tasks)
    await followup.send(embed=embeda("success", "복구 완료", f"총 {total}명 중 성공: {success}, 실패: {fail}"), ephemeral=True)

@tree.command(name="복구", description="소유자 전용: 복구키로 저장된 사용자를 현재 서버로 복구합니다.")
@app_commands.describe(recover_key="복구키 (guilds.token 컬럼 값)")
async def recover_command(interaction: discord.Interaction, recover_key: str):
    if interaction.user.id != OWNER:
        return await interaction.response.send_message("이 명령어는 소유자만 사용할 수 있습니다.", ephemeral=True)
    await interaction.response.send_message("복구를 시작합니다. 진행은 비공개로 전송됩니다.", ephemeral=True)
    con, cur = start_db()
    cur.execute("SELECT id FROM guilds WHERE token == ?;", (recover_key,))
    row = cur.fetchone()
    con.close()
    if not row:
        return await interaction.followup.send(embed=embeda("error", "복구 실패", "해당 복구키에 해당하는 서버 정보가 없습니다."), ephemeral=True)
    source_guild_id = row[0]
    target_guild_id = interaction.guild.id
    try:
        member = await interaction.guild.fetch_member(bot.user.id)
        if not member.guild_permissions.administrator:
            return await interaction.followup.send(embed=embeda("error", "권한 오류", "봇에게 관리자 권한이 필요합니다."), ephemeral=True)
    except Exception as e:
        print("bot fetch member error:", e)
        return await interaction.followup.send(embed=embeda("error", "오류", "봇 멤버 조회 실패"), ephemeral=True)
    asyncio.create_task(recover_guild_members(source_guild_id, target_guild_id, interaction.followup))

@bot.event
async def on_ready():
    ensure_schema()
    await tree.sync()
    print(f"Bot ready: {bot.user} (ID: {bot.user.id})")

if __name__ == "__main__":
    if BOT_TOKEN.startswith("여기에") or not BOT_TOKEN:
        print("ERROR: BOT_TOKEN을 설정하세요.")
    else:
        bot.run(BOT_TOKEN)
