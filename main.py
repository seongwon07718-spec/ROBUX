from http.client import FOUND
import discord
import sqlite3
import requests
from setting import *
import uuid
from datetime import timedelta
import datetime
from json import JSONDecodeError
import asyncio
import randomstring

client = discord.Client()
API_ENDPOINT = 'https://discord.com/api/v9'
client_id = "1434868431064272907" #디스코드 개발자 센터 Oauth2 탭에 들어가면 있는 Client ID
client_secret = "OR8fMHByU2abW8qLS61OR0IofA0PD5ou" #디스코드 개발자 센터 Oauth2 탭에 들어가면 있는 Client Secret
async def refresh_token(refresh_token):
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    while True:
        r = requests.post('%s/oauth2/token' % api_endpoint, data=data, headers=headers)
        if (r.status_code != 429):
            break

        limitinfo = r.json()
        await asyncio.sleep(limitinfo["retry_after"] + 2)

    print(r.json())
    return False if "error" in r.json() else r.json()
def get_expiretime(time):
    ServerTime = datetime.datetime.now()
    ExpireTime = datetime.datetime.strptime(time, '%Y-%m-%d %H:%M')
    if ((ExpireTime - ServerTime).total_seconds() > 0):
        how_long = (ExpireTime - ServerTime)
        days = how_long.days
        hours = how_long.seconds // 3600
        minutes = how_long.seconds // 60 - hours * 60
        return str(round(days)) + "일 " + str(round(hours)) + "시간 " + str(round(minutes)) + "분" 
    else:
        return False
async def add_user(token, gid,id):
    while True:
        jsonData = {"access_token" : token}
        header = {"Authorization" : "Bot " + ""} #Bot Token
        r = requests.put(f"{api_endpoint}/guilds/{gid}/members/{id}", json=jsonData, headers=header)
        if (r.status_code != 429):
            break

        limitinfo = r.json()
        await asyncio.sleep(limitinfo["retry_after"] + 2)

    if (r.status_code == 201 or r.status_code == 204):
        return True
    else:
        print(r.json())
        return False

def make_expiretime(days):
    ServerTime = datetime.datetime.now()
    ExpireTime_STR = (ServerTime + timedelta(days=days)).strftime('%Y-%m-%d %H:%M')
    return ExpireTime_STR

def add_time(now_days, add_days):
    ExpireTime = datetime.datetime.strptime(now_days, '%Y-%m-%d %H:%M')
    ExpireTime_STR = (ExpireTime + timedelta(days=add_days)).strftime('%Y-%m-%d %H:%M')
    return ExpireTime_STR

async def register_redirect_url(id):
    return True
def is_expired(time):
    ServerTime = datetime.datetime.now()
    ExpireTime = datetime.datetime.strptime(time, '%Y-%m-%d %H:%M')
    if ((ExpireTime - ServerTime).total_seconds() > 0):
        return False
    else:
        return True

async def is_guild(id):
    con,cur = start_db()
    cur.execute("SELECT * FROM guilds WHERE id == ?;", (id,))
    res = cur.fetchone()
    con.close()
    if (res == None):
        return False
    else:
        return True
def embeda(embedtype, embedtitle, description):
    if (embedtype == "error"):
        return discord.Embed(color=0x5c6cdf, title=embedtitle, description=description)
    if (embedtype == "success"):
        return discord.Embed(color=0x5c6cdf, title=embedtitle, description=description)
    if (embedtype == "warning"):
        return discord.Embed(color=0x5c6cdf, title=embedtitle, description=description)
def getguild(id):
    header = {
        "Authorization" : "Bot "
    }
    r = requests.get(f'https://discord.com/api/v9/guilds/{id}',headers=header)
    return r.json()
def start_db():
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    return con, cur
async def is_guild_valid(id):
    if not (str(id).isdigit()):
        return False
    if not (await is_guild(id)):
        return False
    con,cur = start_db()
    cur.execute("SELECT * FROM guilds WHERE id == ?;", (id,))
    guild_info = cur.fetchone()
    expire_date = guild_info[2]
    con.close()
    if (is_expired(expire_date)):
        return False
    return True

@client.event
async def on_ready():
    print(f"Login: {client.user}\nInvite Link: https://discord.com/oauth2/authorize?client_id={client.user.id}&permissions=8&scope=bot")
    while True:
        await client.change_presence(activity=discord.Game(f"링크복구봇 | {len(client.guilds)}서버 사용중"),status=discord.Status.online)
        await asyncio.sleep(5)
        await client.change_presence(activity=discord.Game(f"링크복구봇 | {len(client.guilds)}서버 사용중"),status=discord.Status.online)
        await asyncio.sleep(5)

@client.event
async def on_message(message):
    if (message.content.startswith(".생성")):
        if message.author.id == owner:
            if not isinstance(message.channel, discord.channel.DMChannel):
                try:
                    amount = int(message.content.split(" ")[1])
                except:
                    await message.channel.send("올바른 생성 갯수를 입력해주세요.")
                    return
                if 1 <= amount <= 30:
                    try:
                        license_length = int(message.content.split(" ")[2])
                    except:
                        await message.channel.send("올바른 생성 기간을 입력해주세요.")
                        return
            con,cur = start_db()
            generated_key = []
            for n in range(int(amount)):
                key = "SinRestore-" + randomstring.pick(20)
                generated_key.append(key)
                cur.execute("INSERT INTO licenses VALUES(?, ?);", (key, license_length))
                con.commit()
            con.close()
            generated_key = "\n".join(generated_key)
            await message.channel.send(embed=discord.Embed(color=0x5c6cdf, title="생성 성공", description=f"디엠을 확인해주세요."))
            await message.author.send(generated_key)
        else:
            await message.channel.send(embed=discord.Embed(color=0x5c6cdf, title="생성 실패", description=f"최대 30개까지만 생성이 가능합니다."))


    if message.guild != None and message.author.id == message.guild.owner_id or message.author.id == owner:
        if (message.content.startswith(".등록 ")):
            license_number = message.content.split(" ")[1]
            con,cur = start_db()
            cur.execute("SELECT * FROM licenses WHERE key == ?;", (license_number,))
            key_info = cur.fetchone()
            if (key_info == None):
                con.close()
                await message.channel.send(embed=embeda("error", "SinLinkBackup", "라이센스가 존재하지 않습니다."))
                return
            cur.execute("DELETE FROM licenses WHERE key == ?;", (license_number,))
            con.commit()
            con.close()
            key_length = key_info[1]

            if (await is_guild(message.guild.id)):
                con,cur = start_db()
                cur.execute("SELECT * FROM guilds WHERE id == ?;", (message.guild.id,))
                guild_info = cur.fetchone()
                expire_date = guild_info[2]
                if (is_expired(expire_date)):
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
                    con,cur = start_db()
                    new_expiredate = make_expiretime(key_length)
                    recover_key = str(uuid.uuid4())[:8].upper()
                    cur.execute("INSERT INTO guilds VALUES(?, ?, ?, ?);", (message.guild.id,recover_key, new_expiredate,''))
                    con.commit()
                    con.close()
                    def check(x):
                        return (isinstance(x.channel,discord.channel.DMChannel) and (message.author.id == x.author.id))
                    embed = discord.Embed(title="SinLinkBackup",description="URL을 입력해주세요. ( /URL < 이부분 )",color=0x5c6cdf)
                    await message.author.send(embed=embed)
                    await message.channel.send(embed=embeda("success", "SinLinkBackup", "DM을 확인해 주세요."))
                    x = await client.wait_for("message", timeout=60,check=check)
                    link = x.content
                    con,cur = start_db()
                    cur.execute("SELECT * FROM guilds WHERE link == ?",(link,))
                    find = cur.fetchone()
                    if not find:
                        con = sqlite3.connect("database.db")
                        cur = con.cursor()
                        a = getguild(message.guild.id)
                        icon = a['icon']
                        print(icon)
                        cur.execute("UPDATE guilds SET link = ?WHERE id == ?;", (link,message.guild.id))
                        con.commit()
                        con.close()
                        await message.channel.send(embed=embeda("success", "SinLinkBackup", "라이센스가 성공적으로 등록되었습니다.\n만료일 : " + new_expiredate + f"\n서버링크 : /{link} \n디엠으로 복구키가 전송되었습니다."))
                        await message.author.send(embed=embeda("success", "SinLinkBackup", f"복구 키 : `{recover_key}`" + "\n" + "복구키를 잃어버리지 않도록 잘 보관해주세요.\n잃어버릴 시 복구가 불가능합니다."))
                    else:
                        embed = discord.Embed(title="SinLinkBackup",description="이미 사용중인 링크 입니다.\n.링크 명령어로 다시 등록해 주세요.",color=0x5c6cdf)
                        await message.author.send(embed=embed)
                        await message.channel.send(embed=embeda("success", "SinLinkBackup", "라이센스가 성공적으로 등록되었습니다!\n다음 만료일 : " + new_expiredate + f"\n서버링크 : None \n디엠으로 복구키가 전송되었습니다."))
                        await message.author.send(embed=embeda("success", "SinLinkBackup", f"복구 키 : `{recover_key}`" + "\n" + "복구키를 잃어버리지 않도록 잘 보관해주세요.\n잃어버릴 시 복구가 불가능합니다."))
                except Exception as e:
                    print(e)
                    await message.channel.send(embed=embeda("success", "SinLinkBackup", "디엠을 차단하셨거나, 권한이 부족합니다."))

    if message.content == ".명령어":
        embed = discord.Embed(title="SinLinkBackup",description=".생성 (갯수) (몇일) : (몇일)라이센스를(갯수)만큼 생성합니다.\n.링크 : URL을 수정합니다.\n.등록 (코드) : 라이센스를 등록합니다.\n.정보 : 라이센스 기간, 인증 유저 수, 서버초대URL을 표시합니다.\n.복구 (복구키) : 유저 복구를 진행합니다.",color=0x5c6cdf)
        embed.set_footer(text = "SinLinkBackup", icon_url = "https://cdn.discordapp.com/attachments/930440105557119058/930630521212506152/fc615348a028c5ae.png")
        await message.channel.send(embed=embed)

    if message.content == ".초대":
        embed = discord.Embed(title="SinLinkBackup봇 초대",description="[봇을 초대하려면 여기 클릭!](https://discord.com/api/oauth2/authorize?client_id=941007903035359362&permissions=8&scope=bot)",color=0x5c6cdf)
        embed.set_footer(text = "SinLinkBackup", icon_url = "https://cdn.discordapp.com/attachments/930440105557119058/930630521212506152/fc615348a028c5ae.png")
        await message.channel.send(embed=embed)

    if message.content == ".링크":
        if message.author.guild_permissions.administrator:
            if (await is_guild(message.guild.id)):
                try:
                    def check(zaza):
                        return (isinstance(zaza.channel,discord.channel.DMChannel) and (message.author.id == zaza.author.id))
                    embed = discord.Embed(title="SinLinkBackup",description="URL을 입력해주세요. ( /URL < 이부분 )",color=0x5c6cdf)
                    await message.author.send(embed=embed)
                    await message.channel.send(embed=embeda("success", "SinLinkBackup", "DM을 확인해 주세요."))
                    zaza = await client.wait_for("message", timeout=60,check=check)
                    link = zaza.content
                    await message.delete()
                    con,cur = start_db()
                    cur.execute("SELECT * FROM guilds WHERE link == ?",(link,))
                    f = cur.fetchone()
                    if not f:
                        con = sqlite3.connect("database.db")
                        cur = con.cursor()
                        cur.execute("UPDATE guilds SET link = ?WHERE id == ?;", (link,message.guild.id))
                        con.commit()
                        con.close()
                        embed1 = discord.Embed(title="SinLinkBackup",description=f"/{link}",color=0x5c6cdf)
                        await message.author.send(embed=embed1)
                    else:
                        embed = discord.Embed(title="SinLinkBackup",description="이미 사용중인 링크 입니다.\n다시 등록해 주세요.",color=0x5c6cdf)
                        await message.author.send(embed=embed)
                        return
                except:
                    await message.channel.send(embed=embeda("success", "SinLinkBackup", "디엠을 차단하셨거나, 권한이 부족합니다."))
            else:
               await message.channel.send(embed=embeda("success", "SinLinkBackup", "라이센스가 등록 되어있지 않습니다."))
        else:
            embed = discord.Embed(title="SinLinkBackup",description="당신은 서버에 관리자 권한이 없습니다.",color=0x5c6cdf)
            await message.channel.send(embed=embed) 

    if (message.content == (".정보")):
        if not (await is_guild_valid(message.guild.id)):
            await message.channel.send(embed=embeda("error", "SinLinkBackup", "라이센스가 유효하지 않습니다."))
            return
        con,cur = start_db()
        cur.execute("SELECT * FROM guilds WHERE id == ?;", (message.guild.id,))
        guild_info = cur.fetchone()
        con.close()
        con,cur = start_db()
        cur.execute("SELECT * FROM users WHERE guild_id == ?;", (message.guild.id,))
        users = cur.fetchall()
        con.close()
        con,cur = start_db()
        cur.execute("SELECT * FROM guilds WHERE id == ?",(message.guild.id,))
        link = cur.fetchone()[3]
        con.close()
        users = list(set(users))
        await message.channel.send(embed=embeda("success" , "SinLinkBackup", f"{get_expiretime(guild_info[2])} ( {guild_info[2]} ) 남음\n 인증 유저 수 : {int(len(users))}\n서버 링크 : /{link}"))

        
    if (message.content.startswith(".복구 ")):
        if message.author.id == owner:
            recover_key = message.content.split(" ")[1]
            if (await is_guild_valid(message.guild.id)):
                await message.channel.send(embed=embeda("error", "SinLinkBackup", "라이센스를 등록하기전에 복구를 진행해주세요."))
            else:
                con,cur = start_db()
                cur.execute("SELECT * FROM guilds WHERE token == ?;", (recover_key,))
                token_result = cur.fetchone()
                con.close()
                if (token_result == None):
                    await message.channel.send(embed=embeda("error", "SinLinkBackup", "복구 키가 틀렸습니다."))
                    return
                if not (await is_guild_valid(token_result[0])):
                    await message.channel.send(embed=embeda("error", "SinLinkBackup", "복구 키가 만료되었습니다."))
                    return
                try:
                    server_info = await client.fetch_guild(token_result[0])
                except:
                    server_info = None
                    pass
                #if (server_info != None):
                   # await message.channel.send(embed=embeda("error", "SinLinkBackup", "터지지 않은 서버의 복구 키입니다."))
                    #return
                if not (await message.guild.fetch_member(client.user.id)).guild_permissions.administrator:
                    await message.channel.send(embed=embeda("error", "SinLinkBackup", "봇에게 관리자 권한이 필요합니다."))
                    return

                con,cur = start_db()
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
                        if (new_token != False):
                            new_refresh = new_token["refresh_token"]
                            new_token = new_token["access_token"]
                            await add_user(new_token, message.guild.id, user_id)
                            print(new_token)
                            con,cur = start_db()
                            cur.execute("UPDATE users SET token = ? WHERE token == ?;", (new_refresh, refresh_token1))
                            con.commit()
                            con.close()
                    except:
                        pass

                con,cur = start_db()
                cur.execute("UPDATE users SET guild_id = ? WHERE guild_id == ?;", (message.guild.id, token_result[0]))
                con.commit()
                cur.execute("UPDATE guilds SET id = ? WHERE id == ?;", (message.guild.id ,token_result[0]))
                con.commit()
                con.close()

                await message.channel.send(embed=embeda("success", "SinLinkBackup", "복구가 정상적으로 완료되었습니다!"))

client.run("")
