# link_restore_bot.py
# discord.py v2 기준. .env 대신 코드 상단에 직접 값 입력 방식.
import os
import sqlite3
import asyncio
import time
from typing import Optional, List, Tuple
import requests
import discord
from discord import app_commands
from discord.ext import commands

# ----------------------------
# 설정 (여기에 직접 값을 입력하세요)
# ----------------------------
BOT_TOKEN = "여기에_봇_토큰을_문자열로_넣으세요"
CLIENT_ID = "1434868431064272907"
CLIENT_SECRET = "여기에_CLIENT_SECRET을_넣으세요"
OWNER = 1402654236570812467  # 소유자(정수)
DATABASE_PATH = "database.db"
API_ENDPOINT = "https://discord.com/api/v9"
MAX_CONCURRENT_REQUESTS = 3  # 복구시 동시 요청 수 제한
# ----------------------------

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)
tree = bot.tree

# ----------------------------
# DB 유틸
# ----------------------------
def start_db():
    con = sqlite3.connect(DATABASE_PATH)
    cur = con.cursor()
    return con, cur

def ensure_schema():
    con, cur = start_db()
    # guilds 테이블: id, token(복구키), expiredate, link, icon 등 필요에 따라 확장
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guilds (
        id INTEGER PRIMARY KEY,
        token TEXT UNIQUE,
        expiredate TEXT,
        link TEXT,
        icon TEXT
    );
    """)
    # users: id, token(refresh_token), guild_id
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        token TEXT,
        guild_id INTEGER
    );
    """)
    # licenses 단순 예시
    cur.execute("""
    CREATE TABLE IF NOT EXISTS licenses (
        key TEXT PRIMARY KEY,
        days INTEGER
    );
    """)
    con.commit()
    con.close()

# ----------------------------
# 권한 관련
# ----------------------------
def is_owner(user: discord.User) -> bool:
    return user.id == OWNER

def is_allowed_dev(user: discord.User) -> bool:
    # 추가 허용자 체크를 넣고 싶으면 목록을 확인하도록 수정
    return is_owner(user)

async def check_guild_admin(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    member = interaction.user
    if isinstance(member, discord.Member):
        return member.guild_permissions.administrator or member.guild_permissions.manage_guild
    return False

def embeda(embed_type: str, title: str, description: str, fields: Optional[List[Tuple[str,str,bool]]] = None) -> discord.Embed:
    color_map = {"success":0x5c6cdf, "error":0xff5c5c, "warn":0xffa500, "info":0x5c6cdf}
    embed = discord.Embed(title=title, description=description, color=color_map.get(embed_type,0x5c6cdf))
    if fields:
        for n,(name,val,inline) in enumerate(fields):
            embed.add_field(name=name, value=val, inline=inline)
    embed.set_footer(text="SinLinkBackup")
    return embed

# ----------------------------
# OAuth2 refresh -> access token
# ----------------------------
def refresh_token_sync(refresh_token: str) -> Optional[dict]:
    """
    동기 요청으로 refresh_token을 access_token으로 교환.
    반환: dict (access_token, refresh_token, expires_in, ...) 또는 None
    """
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
        print("refresh_token 요청 예외:", e)
        return None

    if r.status_code == 429:
        # rate limit: caller가 재시도 로직을 처리해야 함
        try:
            info = r.json()
            retry = info.get("retry_after", 1)
        except:
            retry = 2
        print("rate limited on refresh_token, retry after", retry)
        time.sleep(retry + 1)
        # 간단히 재귀 한 번 더 시도 (심화는 반복 재시도 로직 권장)
        return refresh_token_sync(refresh_token)

    try:
        j = r.json()
    except Exception as e:
        print("refresh_token 응답 JSON 파싱 실패:", e, r.text)
        return None

    if "error" in j:
        print("refresh_token error:", j)
        return None
    return j  # access_token, refresh_token 등 포함

# ----------------------------
# add_user: access_token으로 guild에 멤버 추가
# ----------------------------
def add_user_sync(access_token: str, guild_id: int, user_id: str) -> bool:
    jsonData = {"access_token": access_token}
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    try:
        r = requests.put(f"{API_ENDPOINT}/guilds/{guild_id}/members/{user_id}", json=jsonData, headers=headers, timeout=10)
    except Exception as e:
        print("add_user 요청 예외:", e)
        return False

    if r.status_code == 429:
        try:
            info = r.json()
            retry = info.get("retry_after", 1)
        except:
            retry = 2
        print("add_user rate limited, retry after", retry)
        time.sleep(retry + 1)
        return add_user_sync(access_token, guild_id, user_id)

    if r.status_code in (201, 204):
        return True
    else:
        print("add_user 실패:", r.status_code, r.text)
        return False

# ----------------------------
# 비동기 복구 작업 헬퍼
# ----------------------------
async def recover_guild_members(source_guild_id: int, target_guild_id: int, followup, semaphore: asyncio.Semaphore):
    """
    source_guild_id: 원본이 저장된 guild id (DB의 guilds.token으로 매핑되는 값)
    target_guild_id: 현재 복구를 적용할 서버 id (interaction.guild.id)
    followup: interaction.followup에 메시지 보낼 수 있는 객체
    semaphore: 동시성 제어용 Semaphore
    """
    con, cur = start_db()
    cur.execute("SELECT id, token FROM users WHERE guild_id == ?;", (source_guild_id,))
    users = cur.fetchall()
    con.close()

    total = len(users)
    if total == 0:
        await followup.send("복구 대상 사용자가 없습니다.", ephemeral=True)
        return

    await followup.send(f"총 {total}명 대상 복구를 시작합니다. (동시 {MAX_CONCURRENT_REQUESTS}개)", ephemeral=True)

    progress = 0
    success = 0
    fail = 0

    async def worker(u):
        nonlocal progress, success, fail
        user_id = u[0]
        refresh_tok = u[1]
        async with semaphore:
            # 1) refresh -> access
            loop = asyncio.get_event_loop()
            token_data = await loop.run_in_executor(None, refresh_token_sync, refresh_tok)
            if not token_data or "access_token" not in token_data:
                print("refresh 실패:", user_id)
                fail += 1
                progress += 1
                return
            access_tok = token_data["access_token"]
            new_refresh = token_data.get("refresh_token", refresh_tok)

            # 2) add user
            added = await loop.run_in_executor(None, add_user_sync, access_tok, target_guild_id, user_id)
            if added:
                success += 1
                # DB에 refresh token 갱신
                try:
                    con, cur = start_db()
                    cur.execute("UPDATE users SET token = ? WHERE id == ?;", (new_refresh, user_id))
                    con.commit()
                    con.close()
                except Exception as e:
                    print("DB 업데이트 실패:", e)
            else:
                fail += 1
            progress += 1
            # 진행 상태 간단 로그(원하면 followup으로 주기적 업데이트 가능)
            if progress % 10 == 0:
                await followup.send(f"진행: {progress}/{total} (성공: {success}, 실패: {fail})", ephemeral=True)

    # 작업 배포
    tasks = [asyncio.create_task(worker(u)) for u in users]
    await asyncio.gather(*tasks)

    await followup.send(embeda("success", "복구 완료", f"총 {total}명 중 성공: {success}, 실패: {fail}"), ephemeral=True)

# ----------------------------
# /복구 슬래시 구현(소유자 전용)
# ----------------------------
@tree.command(name="복구", description="소유자 전용: 복구키로 저장된 사용자를 현재 서버로 복구합니다.")
@app_commands.describe(recover_key="복구에 사용할 키(원본 서버의 token 컬럼)")
async def recover_command(interaction: discord.Interaction, recover_key: str):
    if not is_owner(interaction.user):
        return await interaction.response.send_message("이 명령어는 소유자만 사용할 수 있습니다.", ephemeral=True)

    await interaction.response.send_message("복구 작업을 시작합니다. 진행 상황은 비공개로 전송됩니다.", ephemeral=True)
    # recover_key -> source_guild_id 찾기
    con, cur = start_db()
    cur.execute("SELECT id FROM guilds WHERE token == ?;", (recover_key,))
    row = cur.fetchone()
    con.close()
    if not row:
        return await interaction.followup.send(embeda("error", "복구 실패", "해당 복구키에 해당하는 서버 정보가 없습니다."), ephemeral=True)

    source_guild_id = row[0]
    target_guild_id = interaction.guild.id

    # 봇이 target 서버에서 관리자 권한을 갖고 있는지 확인
    try:
        member = await interaction.guild.fetch_member(bot.user.id)
        if not member.guild_permissions.administrator:
            return await interaction.followup.send(embeda("error", "권한 오류", "봇에게 관리자 권한이 필요합니다."), ephemeral=True)
    except Exception as e:
        print("봇 멤버 조회 실패:", e)
        return await interaction.followup.send(embeda("error", "오류", "봇 멤버 조회 실패"), ephemeral=True)

    # 동시성 제어용 semaphore
    sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    # 비동기 복구 실행
    asyncio.create_task(recover_guild_members(source_guild_id, target_guild_id, interaction.followup, sem))

# ----------------------------
# on_ready 등
# ----------------------------
@bot.event
async def on_ready():
    ensure_schema()
    await tree.sync()
    print(f"Bot ready: {bot.user} (ID: {bot.user.id})")

if __name__ == "__main__":
    if not BOT_TOKEN or BOT_TOKEN.startswith("여기에"):
        print("ERROR: BOT_TOKEN을 코드 상단에 넣어주세요.")
    else:
        bot.run(BOT_TOKEN)
