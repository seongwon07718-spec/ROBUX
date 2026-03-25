import discord
from discord import app_commands, ui
from discord.ext import tasks, commands
import sqlite3, asyncio, re, uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel
from threading import Thread
from datetime import datetime
import requests
import time

# --- 데이터베이스 및 기본 설정 ---
DATABASE = 'robux_shop.db'
TOKEN = "YOUR_BOT_TOKEN_HERE" # 실제 토큰으로 교체하세요
BANK_K = "7777-03-6763823 (카카오뱅크)"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

init_db()

# --- FastAPI 설정 (입금 확인용) ---
app = FastAPI()
pending_deposits = {}

class ChargeData(BaseModel):
    message: str

@app.post("/charge")
async def receive_charge(data: ChargeData):
    msg = data.message.strip()
    amount_match = re.search(r'입금\s*([\d,]+)원', msg)
    name_match = re.search(r'원\n([가-힣]+)\n잔액', msg)
    
    if amount_match and name_match:
        amount = amount_match.group(1).replace(",", "")
        name = name_match.group(1)
        key = f"{name}_{amount}"
        pending_deposits[key] = True
    else:
        fallback = re.search(r'([가-힣]+)\s*(\d+)', msg)
        if fallback:
            key = f"{fallback.group(1)}_{fallback.group(2)}"
            pending_deposits[key] = True
    return {"ok": True}

# --- 로블록스 데이터 조회 함수 ---
def get_roblox_data(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    
    url = "https://economy.roblox.com/v1/users/authenticated/currency"
    headers = {
        "Cookie": f".ROBLOSECURITY={cookie}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json().get("robux", 0), "정상"
        elif response.status_code == 401:
            return 0, "쿠키 만료"
        else:
            return 0, f"에러 {response.status_code}"
    except:
        return 0, "연결 실패"

# --- 모달 클래스 ---
class CookieModal(ui.Modal, title="로블록스 쿠키 입력"):
    cookie_input = ui.TextInput(
        label="로블록스 쿠키 (.ROBLOSECURITY)",
        placeholder="이곳에 쿠키를 입력하세요",
        style=discord.TextStyle.long,
        required=True
    )

    async def on_submit(self, it: discord.Interaction):
        cookie = self.cookie_input.value
        robux, status = get_roblox_data(cookie)
        if status == "정상":
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('roblox_cookie', ?)", (cookie,))
            conn.commit()
            conn.close()
            await it.response.send_message(f"✅ 로그인 성공! 현재 재고: `{robux:,}` R$", ephemeral=True)
        else:
            await it.response.send_message(f"❌ 로그인 실패: {status}", ephemeral=True)

class ChargeModal(ui.Modal, title="계좌이체 충전 신청"):
    depositor = ui.TextInput(label="입금자명", placeholder="입금자명을 입력해주세요", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전 금액", placeholder="숫자만 입력해주세요", min_length=3)

    async def on_submit(self, it: discord.Interaction):
        con = ui.Container()
        con.accent_color = 0xffffff
        con.add_item(ui.TextDisplay("## 충전 준비 중\n충전 서버 AP 연결 중 (1/3)"))
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        msg = await it.original_response()

        for step in ["입금자명/충전금액 설정 중 (2/3)", "안전한 충전을 위한 설정 중 (3/3)", "모든 설정이 완료되었습니다"]:
            await asyncio.sleep(1.2)
            con.clear_items()
            con.add_item(ui.TextDisplay(f"## 충전 준비 중\n{step}"))
            await msg.edit(view=ui.LayoutView().add_item(con))

        await asyncio.sleep(1)
        con.clear_items()
        con.add_item(ui.TextDisplay(f"## 입금 대기 중\n\n**입금 계좌**: `{BANK_K}`\n**입금 금액**: `{int(self.amount.value):,}원`\n**입금자명**: `{self.depositor.value}`\n\n-# 5분 이내에 입금해주세요. 입금 후 자동 처리됩니다."))
        await msg.edit(view=ui.LayoutView().add_item(con))

        key = f"{self.depositor.value}_{self.amount.value}"
        success = False
        for _ in range(60): # 약 5분
            if pending_deposits.get(key):
                success = True
                del pending_deposits[key]
                break
            await asyncio.sleep(5)

        con.clear_items()
        if success:
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()
            cur.execute("INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?", 
                        (str(it.user.id), int(self.amount.value), int(self.amount.value)))
            conn.commit()
            conn.close()
            con.accent_color = 0x57F287
            con.add_item(ui.TextDisplay(f"## 충전 완료\n<@{it.user.id}> 님의 잔액이 성공적으로 충전되었습니다.\n**충전 금액:** `{int(self.amount.value):,}원`"))
        else:
            con.accent_color = 0xED4245
            con.add_item(ui.TextDisplay("## 충전 실패\n시간 내에 입금이 확인되지 않았습니다. 다시 시도해주세요."))
        
        await msg.edit(view=ui.LayoutView().add_item(con))

# --- 자판기 뷰 클래스 ---
class RobuxVending(ui.LayoutView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def build_main_menu(self):
        """실시간 재고가 포함된 메인 컨테이너 빌드"""
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
        conn.close()

        cookie = row[0] if row else None
        robux, status = get_roblox_data(cookie)
        stock_display = f"{robux:,} R$" if status == "정상" else f"점검 중 ({status})"

        con = ui.Container()
        con.accent_color = 0xffffff
        con.add_item(ui.TextDisplay("## 구매하기"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay(f"
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 버튼들 생성 및 콜백 지정
        btn_notice = ui.Button(label="공지", emoji="📢")
        btn_notice.callback = lambda it: it.response.send_message("공지사항 준비 중", ephemeral=True)
        
        btn_shop = ui.Button(label="구매", emoji="🛒")
        btn_shop.callback = lambda it: it.response.send_message("제품 목록 준비 중", ephemeral=True)
        
        btn_charge = ui.Button(label="충전", emoji="💳", custom_id="charge_main")
        btn_charge.callback = self.main_callback
        
        btn_info = ui.Button(label="정보", emoji="👤")
        btn_info.callback = self.info_callback
        
        con.add_item(ui.ActionRow(btn_notice, btn_shop, btn_charge, btn_info))
        return con

    async def info_callback(self, it: discord.Interaction):
        u_id = str(it.user.id)
        money = 0
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone()
        conn.close()
        if row: money = row[0]

        roles = [role.name for role in it.user.roles if role.name != "@everyone"]
        role_grade = roles[-1] if roles else "Guest"

        con = ui.Container()
        con.accent_color = 0xffffff
        con.add_item(ui.TextDisplay(f"## {it.user.display_name} 님의 정보"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        info_text = (
            f"> **보유 잔액:** `{money:,}원`\n"
            f"> **사용 금액:** `0원`\n"
            f"> **역할 등급:** `{role_grade}`\n"
            f"> **할인 혜택:** `0%`"
        )
        con.add_item(ui.TextDisplay(info_text))
        
        sel = ui.Select(placeholder="내역 조회 선택", options=[
            discord.SelectOption(label="최근 충전 내역", value="c"),
            discord.SelectOption(label="최근 구매 내역", value="p")
        ])
        async def sel_cb(i: discord.Interaction):
            await i.response.send_message(f"내역이 존재하지 않습니다.", ephemeral=True)
        sel.callback = sel_cb
        con.add_item(ui.ActionRow(sel))

        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

    async def main_callback(self, it: discord.Interaction):
        # 충전 수단 선택창
        con = ui.Container()
        con.accent_color = 0xffffff
        con.add_item(ui.TextDisplay("## 충전 수단 선택\n\n원하시는 충전 방식을 선택해주세요."))
        
        btn_bank = ui.Button(label="계좌이체", style=discord.ButtonStyle.gray)
        btn_bank.callback = lambda i: i.response.send_modal(ChargeModal())
        con.add_item(ui.ActionRow(btn_bank))
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

# --- 봇 클래스 ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.vending_msg_info = {} # channel_id: message_id

    async def setup_hook(self):
        self.stock_updater.start()
        await self.tree.sync()

    @tasks.loop(minutes=2.0)
    async def stock_updater(self):
        """2분마다 자판기 메시지 실시간 갱신"""
        for channel_id, msg_id in list(self.vending_msg_info.items()):
            try:
                channel = self.get_channel(channel_id)
                if not channel: continue
                msg = await channel.fetch_message(msg_id)
                
                v_view = RobuxVending(self)
                new_con = await v_view.build_main_menu()
                await msg.edit(view=ui.LayoutView().add_item(new_con))
            except:
                pass

bot = MyBot()

@bot.tree.command(name="쿠키", description="로블록스 쿠키를 설정합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def set_cookie(it: discord.Interaction):
    await it.response.send_modal(CookieModal())

@bot.tree.command(name="자판기", description="실시간 재고 자판기를 소환합니다.")
async def spawn_vending(it: discord.Interaction):
    view = RobuxVending(bot)
    con = await view.build_main_menu()
    
    await it.response.send_message(view=ui.LayoutView().add_item(con))
    msg = await it.original_response()
    bot.vending_msg_info[it.channel_id] = msg.id

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=88)

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    bot.run(TOKEN)



