import requests
from flask import redirect, Flask, request,render_template
import uuid
import sqlite3
import json
from json import JSONDecodeError
from setting import *
import asyncio, discord, requests, sqlite3, datetime
from discord.errors import Forbidden
import w

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())


import requests

API_ENDPOINT = 'https://discord.com/api/v9'
client_id = "1434868431064272907" #디스코드 개발자 센터 Oauth2 탭에 들어가면 있는 Client ID
client_secret = "OR8fMHByU2abW8qLS61OR0IofA0PD5ou" #디스코드 개발자 센터 Oauth2 탭에 들어가면 있는 Client Secret

def start_db():
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    return con, cur
def geticon(id):
      con,cur = start_db()
      cur.execute("SELECT * FROM guilds WHERE id == ?",(id,))
      icon = cur.fetchone()[2]
      con.close()
      r = requests.get(f'https://cdn.discordapp.com/icons/{id}/{icon}.png')

def get_user_profile(token):
    header = {"Authorization" : "Bearer " + token} #Bot은 Authorization : Bot TOKEN, 유저 Access Token은 Bearer Token으로 명시함 이 경우는 oauth2 access token인 경우에만 해당 
    res = requests.get("https://discordapp.com/api/v8/users/@me", headers=header) #여긴 그냥 헤더에 토큰쳐넣으면 user정보 반환하는거임 
    print(res.json())
    if (res.status_code != 200):
        return False
    else:
        return res.json()
def get_kr_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

def getip():
    return request.headers.get("CF-Connecting-IP", request.remote_addr)
    
def get_agent():
    return request.user_agent.string
def getguild(id):
    header = {
        "Authorization" : "Bot "
    }
    r = requests.get(f'https://discord.com/api/v9/guilds/{id}',headers=header)
    rr = r.json()
    #print(rr['approximate_member_count'])
    return r.json()
def add_user(token, id,gid):
    try:
      jsonData = {"access_token" : token}
      header = {"Authorization" : "Bot " + ''}
      res = requests.put(f'%s/guilds/{gid}/members/{id}' % API_ENDPOINT, json=jsonData, headers=header)
      return res.json()
    except JSONDecodeError as e:
      return False
def gd(id,link):
    try:
        jsonData = {
          "info":getguild(id)
        }
        headers = {
          'Content-Type': 'application/json'
        }
        r = requests.post(f"/{link}",json = jsonData)#,headers=headers)
        return r.json()
    except:
        return False
def exchange_code(code):
    data = {
      'client_id': client_id,
      'client_secret': client_secret,
      'grant_type': 'authorization_code',
      'code': code,
      'redirect_uri': "/join"
    }
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    r = requests.post(f"{api_endpoint}/oauth2/token", data=data, headers=headers)
    return r.json()
def getme(id):
    header = {
      "Authorization" : "Bot " + '',
    }
    r = requests.get(f'https://discord.com/api/v9/guilds/{id}?with_counts=true',headers=header)
    print(r.json())
    return r.json()
@app.route('/<link>',methods=['GET'])
def joi(link):
    try:
      con, cur = start_db()
      cur.execute("SELECT * FROM guilds WHERE link == ?", (link,))
      gid = cur.fetchone()[0]
      con.close()
      ginfo = getguild(gid)
      r = getme(gid)
      return render_template("s.html",link=link,id = gid,info=ginfo,icon=ginfo['icon'],member=r['approximate_member_count'])
    except Exception as e:
      print(e)
      return render_template("fail.html")
@app.route('/join', methods=['GET']) 
def callback():
      query = request.args.get('code') 
      state = request.args.get('state')
      print(state)
      result = exchange_code(query) 
      print(result) 
      data = get_user_profile(result['access_token']) 
      ginfo = getguild(state)
      print(ginfo)
      print(data)
      add_user(result['access_token'], data['id'],int(state))
      con, cur = start_db()
      cur.execute("INSERT INTO users VALUES(?, ?, ?);", (str(data["id"]), result["refresh_token"], int(state)))
      con.commit()
      con.close()
      try:
        return render_template("success.html")
      except:
        print("fails")
        return render_template('fail.html')

app.run(debug=False, host='0.0.0.0' ,port=80)

