# main.py - 직접 값 입력 가능한 최종본
import discord
import sqlite3
import requests
import uuid
from datetime import timedelta
import datetime
import asyncio
import random
import string

# -----------------------------
# 여기에 직접 값을 넣으세요
# -----------------------------
DISCORD_BOT_TOKEN = "여기에_봇_토큰을_문자열로_넣으세요"
CLIENT_ID = "1434868431064272907"
CLIENT_SECRET = "여기에_client_secret을_넣으세요"
OWNER = 1402654236570812467  # 정수 형태로 관리자 ID
API_ENDPOINT = "https://discord.com/api/v9"
# -----------------------------

# intents 명시적으로 설정
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 랜덤 키 생성 함수
def random_string(length=20):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

async def refresh_token(refresh_token):
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    while True:
        try:
            r = requests.post(f'{API_ENDPOINT}/oauth2/token', data=data, headers=headers, timeout=10)
        except Exception as e:
            print("refresh_token 요청 실패:", e)
            await asyncio.sleep(2)
            continue

        if r.status_code != 429:
            break
        try:
            limitinfo = r.json()
            retry_after = limitinfo.get("retry_after", 1)
        except Exception:
            retry_after = 2
        await asyncio.sleep(retry_after + 2)

    try:
        j = r.json()
    except Exception:
        print("JSON 응답 파싱 실패:", r.text)
        return False

    print(j)
    return False if "error" in j else j

async def add_user(token, gid, id_):
    jsonData = {"access_token": token}
    header = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    while True:
        try:
            r = requests.put(f"{API_ENDPOINT}/guilds/{gid}/members/{id_}", json=jsonData, headers=header, timeout=10)
        except Exception as e:
            print("add_user 요청 실패:", e)
            await asyncio.sleep(2)
            continue

        if r.status_code != 429:
            break
        try:
            limitinfo = r.json()
            retry_after = limitinfo.get("retry_after", 1)
        except Exception:
            retry_after = 2
        await asyncio.sleep(retry_after + 2)

    if r.status_code in (201, 204):
        return True
    else:
        try:
            print("add_user 실패 응답:", r.json())
        except:
            print("add_user 실패 응답 텍스트:", r.text)
        return False

def getguild(id_):
    header = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    try:
        r = requests.get(f'{API_ENDPOINT}/guilds/{id_}', headers=header, timeout=10)
        return r.json()
    except Exception as e:
        print("getguild 요청 실패:", e)
        return {}

def start_db():
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    return con, cur

def get_expiretime(time_str):
    ServerTime = datetime.datetime.now()
    ExpireTime = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M')
    diff = (ExpireTime - ServerTime).total_seconds()
    if diff > 0:
        how_long = (ExpireTime - ServerTime)
        days = how_long.days
        hours = how_long.seconds // 3600
        minutes = how_long.seconds // 60 - hours * 60
        return f"{round(days)}일 {round(hours)}시간 {round(minutes)}분"
    else:
        return False

def make_expiretime(days):
    ServerTime = datetime.datetime.now()
    ExpireTime_STR = (ServerTime + timedelta(days=days)).strftime('%Y-%m-%d %H:%M')
    return ExpireTime_STR

def add_time(now_days, add_days):
    ExpireTime = datetime.datetime.strptime(now_days, '%Y-%m-%d %H:%M')
    ExpireTime_STR = (ExpireTime + timedelta(days=add_days)).strftime('%Y-%m-%d %H:%M')
    return ExpireTime_STR

def is_expired(time_str):
    ServerTime = datetime.datetime.now()
    ExpireTime = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M')
    return (ExpireTime - ServerTime).total_seconds() <= 0

async def is_guild(id_):
    con, cur = start_db()
    cur.execute("SELECT * FROM guilds WHERE id == ?;", (id_,))
    res = cur.fetchone()
    con.close()
    return False if res is None else True

async def is_guild_valid(id_):
    if not str(id_).isdigit():
        return False
    if not await is_guild(id_):
        return False
    con, cur = start_db()
    cur.execute("SELECT * FROM guilds WHERE id == ?;", (id_,))
    guild_info = cur.fetchone()
    con.close()
    if not guild_info:
        return False
    expire_date = guild_info[2]
    if is_expired(expire_date):
        return False
    return True

def embeda(embedtype, embedtitle, description):
    color = 0x5c6cdf
    return discord.Embed(color=color, title=embedtitle, description=description)

# 이벤트 핸들러
@client.event
async def on_ready():
    print(f"Login: {client.user}\nInvite Link: https://discord.com/oauth2/authorize?client_id={client.user.id}&permissions=8&scope=bot")
    # 상태를 계속 바꾸는 루프는 필요시 조정하세요(지속 루프가 블로킹되지 않도록 sleep 사용)
    while True:
        await client.change_presence(activity=discord.Game(f"링크복구봇 | {len(client.guilds)}서버 사용중"))
        await asyncio.sleep(10)

@client.event
async def on_message(message):
    # 봇 자체 메시지 무시
    if message.author.bot:
        return

    # .생성
    if message.content.startswith(".생성"):
        if message.author.id == OWNER:
            if isinstance(message.channel, discord.channel.DMChannel):
                await message.channel.send("DM에서는 사용할 수 없습니다.")
                return
            try:
                amount = int(message.content.split(" ")[1])
            except:
                await message.channel.send("올바른 생성 갯수를 입력해주세요.")
                return
            try:
                license_length = int(message.content.split(" ")[2])
            except:
                await message.channel.send("올바른 생성 기간을 입력해주세요.")
                return

            if not (1 <= amount <= 30):
                await message.channel.send(embed=embeda("error", "생성 실패", "최대 30개까지만 생성이 가능합니다."))
                return

            con, cur = start_db()
            generated_key = []
            for n in range(amount):
                key = "SinRestore-" + random_string(20)
                generated_key.append(key)
                cur.execute("INSERT INTO licenses VALUES(?, ?);", (key, license_length))
                con.commit()
            con.close()
            generated_key_text = "\n".join(generated_key)
            await message.channel.send(embed=embeda("success", "생성 성공", "디엠을 확인해주세요."))
            await message.author.send(generated_key_text)
        else:
            await message.channel.send(embed=embeda("error", "권한 없음", "이 명령어는 소유자만 사용 가능합니다."))

    # .등록
    if message.guild is not None and (message.author.id == message.guild.owner_id or message.author.id == OWNER):
        if message.content.startswith(".등록 "):
            license_number = message.content.split(" ")[1]
            con, cur = start_db()
            cur.execute("SELECT * FROM licenses WHERE key == ?;", (license_number,))
            key_info = cur.fetchone()
            if key_info is None:
                con.close()
                await message.channel.send(embed=embeda("error", "SinLinkBackup", "라이센스가 존재하지 않습니다."))
                return
            cur.execute("DELETE FROM licenses WHERE key == ?;", (license_number,))
            con.commit()
            con.close()
            key_length = key_info[1]

            if await is_guild(message.guild.id):
                con, cur = start_db()
                cur.execute("SELECT * FROM guilds WHERE id == ?;", (message.guild.id,))
                guild_info = cur.fetchone()
                expire_date = guild_info[2]
                if is_expired(expire_date):
                    new_expiredate = make_expiretime(key_length)
                else:
                    new_expiredate = add_time(expire_date, key_length)
                cur.execute("UPDATE guilds SET expiredate = ? WHERE id == ?;", (new_expiredate, message.guild.id))
                con.commit()
                con.close()
                await message.channel.send(embed=embeda("success", "SinLinkBackup", "기간이 연장되었습니다.\n다음 만료일 : " + new_expiredate))
            else:
                try:
                    await register_redirect_url(message.guild.id)
                    con, cur = start_db()
                    new_expiredate = make_expiretime(key_length)
                    recover_key = str(uuid.uuid4())[:8].upper()
                    cur.execute("INSERT INTO guilds VALUES(?, ?, ?, ?);", (message.guild.id, recover_key, new_expiredate, ''))
                    con.commit()
                    con.close()
                    def check(x):
                        return (isinstance(x.channel, discord.channel.DMChannel) and (message.author.id == x.author.id))
                    embed = discord.Embed(title="SinLinkBackup", description="URL을 입력해주세요. ( /URL < 이부분 )", color=0x5c6cdf)
                    await message.author.send(embed=embed)
                    await message.channel.send(embed=embeda("success", "SinLinkBackup", "DM을 확인해 주세요."))
                    x = await client.wait_for("message", timeout=60, check=check)
                    link = x.content
                    con, cur = start_db()
                    cur.execute("SELECT * FROM guilds WHERE link == ?", (link,))
                    find = cur.fetchone()
                    if not find:
                        con = sqlite3.connect("database.db")
                        cur = con.cursor()
                        a = getguild(message.guild.id)
                        icon = a.get('icon') if isinstance(a, dict) else None
                        print("icon:", icon)
                        cur.execute("UPDATE guilds SET link = ? WHERE id == ?;", (link, message.guild.id))
                        con.commit()
                        con.close()
                        await message.channel.send(embed=embeda("success", "SinLinkBackup", "라이센스가 성공적으로 등록되었습니다.\n만료일 : " + new_expiredate + f"\n서버링크 : /{link} \n디엠으로 복구키가 전송되었습니다."))
                        await message.author.send(embed=embeda("success", "SinLinkBackup", f"복구 키 : `{recover_key}`\n복구키를 잃어버리지 않도록 잘 보관해주세요."))
                    else:
                        await message.author.send(embed=discord.Embed(title="SinLinkBackup", description="이미 사용중인 링크 입니다.\n.링크 명령어로 다시 등록해 주세요.", color=0x5c6cdf))
                        await message.channel.send(embed=embeda("success", "SinLinkBackup", "라이센스가 성공적으로 등록되었습니다!\n다음 만료일 : " + new_expiredate + f"\n서버링크 : None \n디엠으로 복구키가 전송되었습니다."))
                        await message.author.send(embed=embeda("success", "SinLinkBackup", f"복구 키 : `{recover_key}`\n복구키를 잃어버리지 않도록 잘 보관해주세요."))
                except Exception as e:
                    print("등록 중 예외:", e)
                    await message.channel.send(embed=embeda("error", "SinLinkBackup", "디엠을 차단하셨거나, 권한이 부족합니다."))

    # .정보
    if message.content == ".정보":
        if not await is_guild_valid(message.guild.id):
            await message.channel.send(embed=embeda("error", "SinLinkBackup", "라이센스가 유효하지 않습니다."))
            return
        con, cur = start_db()
        cur.execute("SELECT * FROM guilds WHERE id == ?;", (message.guild.id,))
        guild_info = cur.fetchone()
        con.close()
        con, cur = start_db()
        cur.execute("SELECT * FROM users WHERE guild_id == ?;", (message.guild.id,))
        users = cur.fetchall()
        con.close()
        con, cur = start_db()
        cur.execute("SELECT * FROM guilds WHERE id == ?", (message.guild.id,))
        row = cur.fetchone()
        con.close()
        link = row[3] if row and len(row) > 3 else "None"
        users = list(set(users))
        await message.channel.send(embed=embeda("success", "SinLinkBackup", f"{get_expiretime(guild_info[2])} ( {guild_info[2]} ) 남음\n 인증 유저 수 : {int(len(users))}\n서버 링크 : /{link}"))

    # .복구
    if message.content.startswith(".복구 "):
        if message.author.id == OWNER:
            recover_key = message.content.split(" ")[1]
            if await is_guild_valid(message.guild.id):
                await message.channel.send(embed=embeda("error", "SinLinkBackup", "라이센스를 등록하기전에 복구를 진행해주세요."))
            else:
                con, cur = start_db()
                cur.execute("SELECT * FROM guilds WHERE token == ?;", (recover_key,))
                token_result = cur.fetchone()
                con.close()
                if token_result is None:
                    await message.channel.send(embed=embeda("error", "SinLinkBackup", "복구 키가 틀렸습니다."))
                    return
                if not await is_guild_valid(token_result[0]):
                    await message.channel.send(embed=embeda("error", "SinLinkBackup", "복구 키가 만료되었습니다."))
                    return
                try:
                    server_info = await client.fetch_guild(token_result[0])
                except:
                    server_info = None
                if not (await message.guild.fetch_member(client.user.id)).guild_permissions.administrator:
                    await message.channel.send(embed=embeda("error", "SinLinkBackup", "봇에게 관리자 권한이 필요합니다."))
                    return

                con, cur = start_db()
                cur.execute("SELECT * FROM users WHERE guild_id == ?;", (token_result[0],))
                users = cur.fetchall()
                con.close()

                users = list(set(users))

                await message.channel.send(embed=embeda("success", "SinLinkBackup", f"복구 중입니다. 잠시만 기다려주세요.(예상복구인원 : {len(users)})"))

                for user in users:
                    try:
                        refresh_token1 = user[1]
                        user_id = user[0]
                        new_token = await refresh_token(refresh_token1)
                        if new_token != False:
                            new_refresh = new_token["refresh_token"]
                            new_access = new_token["access_token"]
                            await add_user(new_access, message.guild.id, user_id)
                            con, cur = start_db()
                            cur.execute("UPDATE users SET token = ? WHERE token == ?;", (new_refresh, refresh_token1))
                            con.commit()
                            con.close()
                    except Exception as e:
                        print("유저 복구 중 예외:", e)
                        pass

                con, cur = start_db()
                cur.execute("UPDATE users SET guild_id = ? WHERE guild_id == ?;", (message.guild.id, token_result[0]))
                con.commit()
                cur.execute("UPDATE guilds SET id = ? WHERE id == ?;", (message.guild.id, token_result[0]))
                con.commit()
                con.close()

                await message.channel.send(embed=embeda("success", "SinLinkBackup", "복구가 정상적으로 완료되었습니다!"))

# register_redirect_url 함수(원래 구현이 비어있었으므로 단순히 True 반환 또는 필요 로직 추가)
async def register_redirect_url(id_):
    # 실제로 URL 등록 로직이 필요하면 여기에 추가하세요
    return True

# 실행
if not DISCORD_BOT_TOKEN or DISCORD_BOT_TOKEN == "여기에_봇_토큰을_문자열로_넣으세요":
    print("ERROR: DISCORD_BOT_TOKEN 값이 비어있습니다. 상단에 토큰을 넣으세요.")
else:
    client.run(DISCORD_BOT_TOKEN)
