import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask, request, jsonify
import sqlite3
import threading
import os
import datetime
import asyncio

# cultureland.py 파일 연동 (오류 방지 처리)
try:
    from cultureland import Cultureland, Pin
except ImportError:
    Cultureland = None
    Pin = None
    print("⚠️ cultureland.py 파일을 찾을 수 없습니다. 문상 충전 기능이 제한됩니다.")

# --- 설정 ---
TOKEN = 'MTQ2OTIwNjM3MTMyMzg3MTI0Mg.GEzYYR.xBtA28CZEhEQOg9oEjNc80dVL57ucB2_AsSanU'
ADMIN_ID = 1322619161075253301    
CULTURE_COOKIE = "" # 컬쳐랜드 쿠키값

app = Flask(__name__)
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 데이터베이스 초기화 ---
def get_db():
    return sqlite3.connect('vending1.db', timeout=10)

def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY, money INTEGER DEFAULT 0, 
        total_spent INTEGER DEFAULT 0, is_blacked INTEGER DEFAULT 0)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS products (
        name TEXT PRIMARY KEY, price INTEGER, category TEXT, content TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS log_settings (
        type TEXT PRIMARY KEY, channel_id TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS ios_pending (
        id INTEGER PRIMARY KEY AUTOINCREMENT, userid TEXT, displayname TEXT, amount INTEGER, success INTEGER DEFAULT 0)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS rewards (
        threshold INTEGER PRIMARY KEY, role_id TEXT, discount INTEGER)''')
    conn.commit(); conn.close()

# --- 공통 유틸리티 ---
async def send_log(log_type, message):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT channel_id FROM log_settings WHERE type = ?", (log_type,))
    row = cur.fetchone(); conn.close()
    if row:
        channel = bot.get_channel(int(row[0]))
        if channel:
            embed = discord.Embed(title=f"🔔 {log_type} 알림", description=message, color=0x5865F2, timestamp=datetime.datetime.now())
            embed.set_footer(text="Log System")
            await channel.send(embed=embed)

async def apply_reward_roles(user_id, guild):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT total_spent FROM users WHERE user_id = ?", (str(user_id),))
    res = cur.fetchone()
    if not res: return
    total = res[0]
    cur.execute("SELECT role_id FROM rewards WHERE threshold <= ? ORDER BY threshold DESC", (total,))
    roles_to_add = cur.fetchall(); conn.close()
    member = guild.get_member(int(user_id))
    if member:
        for r in roles_to_add:
            role = guild.get_role(int(r[0]))
            if role and role not in member.roles:
                try: await member.add_roles(role)
                except: pass

async def do_culture_charge(pin_string):
    if Cultureland is None: return {"status": "error", "message": "모듈 누락"}
    try:
        cl = Cultureland(); await cl.login(CULTURE_COOKIE)
        target_pin = Pin(pin_string) 
        result = await cl.charge([target_pin]) 
        res = result[0] if isinstance(result, list) else result
        return {"status": "success", "amount": res.amount, "message": res.message}
    except Exception as e: return {"status": "error", "message": str(e)}

# --- Flask 서버 (계좌 자동 충전) ---
@app.route("/ios/check", methods=["POST"])
def ios_check():
    obj = request.get_json(); msg = obj.get("messageText", "")
    try:
        if '카카오뱅크' in msg:
            lines = msg.split('\n')
            amount = int(lines[4].split('입금 ')[1].split('원')[0].replace(',', ''))
            name = lines[5]
        elif '케이뱅크' in msg:
            lines = msg.split('\n')
            amount = int(lines[3].split('입금 ')[1].split('원')[0].replace(',', ''))
            name = lines[5]
        else: return jsonify({'result': False})

        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT userid FROM ios_pending WHERE amount = ? AND displayname = ? AND success = 0", (amount, name))
        res = cur.fetchone()
        if res:
            u_id = res[0]
            cur.execute("UPDATE ios_pending SET success = 1 WHERE amount = ? AND displayname = ?", (amount, name))
            cur.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, u_id))
            conn.commit(); conn.close()
            bot.loop.create_task(send_log("충전", f"💰 **계좌 자동 충전 완료**\n👤 유저: <@{u_id}>\n💵 금액: {amount:,}원"))
            return jsonify({'result': True})
        conn.close(); return jsonify({'result': False})
    except: return jsonify({'result': False})

# --- UI 컴포넌트 (모달 및 뷰) ---
class CultureModal(discord.ui.Modal, title="문상 실시간 자동 충전"):
    pin = discord.ui.TextInput(label="핀번호 입력", placeholder="숫자만 입력하세요", min_length=16)
    async def on_submit(self, it: discord.Interaction):
        await it.response.send_message(embed=discord.Embed(description="⏳ 핀번호 확인 중...", color=0xFFFF00), ephemeral=True)
        res = await do_culture_charge(str(self.pin).replace("-", "").strip())
        if res["status"] == "success" and res["amount"] > 0:
            amount = res["amount"]; u_id = str(it.user.id)
            conn = get_db(); cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
            cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount, amount, u_id))
            conn.commit(); conn.close()
            await it.edit_original_response(embed=discord.Embed(title="✅ 충전 성공", description=f"금액: `{amount:,}원`", color=0x00FF00))
            await send_log("충전", f"🎫 **문상 충전 성공**\n👤 유저: {it.user.mention}\n💵 금액: {amount:,}원")
            await apply_reward_roles(u_id, it.guild)
        else:
            await it.edit_original_response(embed=discord.Embed(title="❌ 충전 실패", description=f"사유: `{res.get('message')}`", color=0xFF0000))

class BankChargeModal(discord.ui.Modal, title="계좌이체 예약"):
    name = discord.ui.TextInput(label="입금자명"); amount = discord.ui.TextInput(label="입금 금액")
    async def on_submit(self, it: discord.Interaction):
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO ios_pending (userid, displayname, amount, success) VALUES (?, ?, ?, 0)", (str(it.user.id), str(self.name), int(str(self.amount))))
        conn.commit(); conn.close()
        await it.response.send_message(embed=discord.Embed(description=f"✅ {self.name}님 {self.amount}원 입금 시 자동 충전됩니다.", color=0x5865F2), ephemeral=True)

class MainVendingView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="제품구매", style=discord.ButtonStyle.primary, custom_id="v_buy", emoji="🛒")
    async def buy(self, it: discord.Interaction, btn):
        conn = get_db(); cur = conn.cursor(); cur.execute("SELECT DISTINCT category FROM products")
        cats = [r[0] for r in cur.fetchall()]; conn.close()
        if not cats: return await it.response.send_message(embed=discord.Embed(description="❌ 등록된 제품이 없습니다.", color=0xFF0000), ephemeral=True)
        view = discord.ui.View(); sel = discord.ui.Select(placeholder="카테고리 선택")
        for c in cats: sel.add_option(label=c, emoji="📂")
        sel.callback = lambda i: show_prods(i, sel.values[0]); view.add_item(sel)
        await it.response.send_message(embed=discord.Embed(description="📂 카테고리를 선택하세요."), view=view, ephemeral=True)

    @discord.ui.button(label="충전하기", style=discord.ButtonStyle.success, custom_id="v_charge", emoji="💸")
    async def charge(self, it: discord.Interaction, btn):
        embed = discord.Embed(title="💳 충전소", color=0xFEE100); embed.add_field(name="🏦 계좌 정보", value="`입금처 정보`", inline=False)
        view = discord.ui.View()
        b_btn = discord.ui.Button(label="계좌 예약", style=discord.ButtonStyle.primary); b_btn.callback = lambda i: i.response.send_modal(BankChargeModal())
        c_btn = discord.ui.Button(label="문상 자충", style=discord.ButtonStyle.secondary); c_btn.callback = lambda i: i.response.send_modal(CultureModal())
        view.add_item(b_btn); view.add_item(c_btn)
        await it.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="내 정보", style=discord.ButtonStyle.secondary, custom_id="v_info", emoji="👤")
    async def info(self, it: discord.Interaction, btn):
        conn = get_db(); cur = conn.cursor(); cur.execute("SELECT money, total_spent FROM users WHERE user_id = ?", (str(it.user.id),))
        r = cur.fetchone(); conn.close()
        m, t = (r[0], r[1]) if r else (0, 0)
        embed = discord.Embed(title="👤 내 정보", color=0x2F3136); embed.add_field(name="잔액", value=f"`{m:,}원`", inline=True); embed.add_field(name="누적", value=f"`{t:,}원`", inline=True)
        await it.response.send_message(embed=embed, ephemeral=True)

# --- 구매 및 상품 목록 ---
async def show_prods(it, cat):
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT name, price, content FROM products WHERE category = ?", (cat,))
    prods = cur.fetchall(); conn.close()
    view = discord.ui.View(); sel = discord.ui.Select(placeholder="제품 선택")
    for p in prods:
        stk = list(filter(None, p[2].split('\n')))
        if stk: sel.add_option(label=p[0], description=f"{p[1]:,}원 | 재고 {len(stk)}개")
    if not sel.options: return await it.response.edit_message(content="❌ 재고 없음", view=None)
    sel.callback = lambda i: process_purchase(i, sel.values[0]); view.add_item(sel)
    await it.response.edit_message(embed=discord.Embed(description=f"📦 **{cat}** 목록입니다."), view=view)

async def process_purchase(it, p_name):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT money, total_spent FROM users WHERE user_id = ?", (str(it.user.id),))
    u = cur.fetchone(); cur.execute("SELECT price, content FROM products WHERE name = ?", (p_name,))
    p = cur.fetchone()
    stk_list = list(filter(None, p[1].split('\n')))
    
    # 할인 적용
    cur.execute("SELECT discount FROM rewards WHERE threshold <= ? ORDER BY threshold DESC LIMIT 1", (u[1] if u else 0,))
    rew = cur.fetchone(); discount = rew[0] if rew else 0
    f_price = int(p[0] * (1 - discount/100))

    if not u or u[0] < f_price: return await it.response.send_message(embed=discord.Embed(description=f"❌ 잔액 부족 (할인가: {f_price:,}원)", color=0xFF0000), ephemeral=True)

    data = stk_list[0]; rem = "\n".join(stk_list[1:])
    cur.execute("UPDATE users SET money = money - ?, total_spent = total_spent + ? WHERE user_id = ?", (f_price, f_price, str(it.user.id)))
    cur.execute("UPDATE products SET content = ? WHERE name = ?", (rem, p_name))
    conn.commit(); conn.close()
    
    success_embed = discord.Embed(title="🎁 구매 완료", color=0x00FF00); success_embed.add_field(name="데이터", value=f"```\n{data}\n```", inline=False)
    try: await it.user.send(embed=success_embed)
    except: pass
    await it.response.send_message(embed=discord.Embed(description="✅ 구매 완료! DM을 확인해주세요."), ephemeral=True)
    await send_log("구매", f"🛒 **제품 구매**\n👤 유저: {it.user.mention}\n📦 제품: {p_name}\n💳 결제액: {f_price:,}원")

# --- 슬래시 커맨드 (글로벌) ---
@bot.tree.command(name="자판기", description="자판기 패널 출력")
async def v_main(it: discord.Interaction):
    if it.user.id != ADMIN_ID: return
    await it.response.send_message(embed=discord.Embed(title="🛒 SHOP", description="버튼을 눌러 이용하세요."), view=MainVendingView())

@bot.tree.command(name="입고", description="제품 등록")
async def add_p(it: discord.Interaction, 이름: str, 가격: int, 카테고리: str, 재고내용: str):
    if it.user.id != ADMIN_ID: return
    conn = get_db(); cur = conn.cursor(); cur.execute("INSERT OR REPLACE INTO products VALUES (?, ?, ?, ?)", (이름, 가격, 카테고리, 재고내용))
    conn.commit(); conn.close()
    await it.response.send_message(f"✅ {이름} 입고 완료", ephemeral=True)

@bot.tree.command(name="혜택설정", description="누적 할인 설정")
async def set_reward(it: discord.Interaction, 기준금액: int, 역할: discord.Role, 할인율: int):
    if it.user.id != ADMIN_ID: return
    conn = get_db(); cur = conn.cursor(); cur.execute("INSERT OR REPLACE INTO rewards VALUES (?, ?, ?)", (기준금액, str(역할.id), 할인율))
    conn.commit(); conn.close()
    await it.response.send_message(f"✅ 설정 완료: {기준금액:,}원 이상 시 {할인율}% 할인", ephemeral=True)

@bot.event
async def on_ready():
    init_db(); await bot.tree.sync()
    print(f"🚀 {bot.user.name} 가동 시작 (글로벌 동기화 완료)")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=80), daemon=True).start()
    bot.run(TOKEN)
