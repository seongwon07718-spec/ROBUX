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

DATABASE = 'robux_shop.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

init_db()

TOKEN = ""
BANK_K = "7777-03-6763823 (카카오뱅크)"
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

class RobuxBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        conn = sqlite3.connect('robux_shop.db')
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)")
        conn.commit()
        conn.close()
        await self.tree.sync()

bot = RobuxBot()

def get_roblox_data(cookie):
    """보안 차단을 피하기 위해 헤더를 설정하여 실시간 로벅스 잔액을 가져옵니다."""
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
            data = response.json()
            return data.get("robux", 0), "정상"
        elif response.status_code == 401:
            return 0, "쿠키 만료"
        else:
            return 0, f"에러 {response.status_code}"
    except Exception as e:
        return 0, f"연결 실패"

class CookieModal(ui.Modal, title="로블록스 쿠키 입력"):
    cookie_input = ui.TextInput(
        label="로블록스 쿠키 (.ROBLOSECURITY)",
        placeholder="이곳에 쿠키를 입력하세요 (절대 공유 금지)",
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
        con.add_item(ui.TextDisplay("## 충전 준비 중"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        status_text = ui.TextDisplay("충전 서버 AP 연결 중 (1/3)")
        con.add_item(status_text)
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay("-# 365일 안전하게 충전 기록은 저장됩니다"))
        
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        msg = await it.original_response()

        steps = [
            "입금자명/충전금액 설정 중 (2/3)",
            "안전한 충전을 위한 설정 중 (3/3)",
            "모든 설정이 완료되었습니다"
        ]

        for step in steps:
            await asyncio.sleep(1.5)
            con.clear_items()
            con.add_item(ui.TextDisplay("## 충전 준비 중"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay(step))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("-# 365일 안전하게 충전 기록은 저장됩니다"))
            await msg.edit(view=ui.LayoutView().add_item(con))

        await asyncio.sleep(1)
        con.clear_items()
        con.accent_color = 0xffffff
        con.add_item(ui.TextDisplay("## 입금 대기 중"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay(f"### 충전 안내\n1. **입금자명**은 반드시 본인 실명으로 입력해주세요\n2. 입금 대기 시간은 **5분**입니다\n3. 충전 처리는 입금 후 **최대 2~3분**까지 걸립니다\n4. **5분 지나고 입금할 시 충전 안됩니다**\n\n**입금 계좌**: `{BANK_K}`\n\n**입금 금액**: `{int(self.amount.value):,}원`\n\n**입금자명**: `{self.depositor.value}`"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay("-# 365일 안전하게 충전 기록은 저장됩니다"))
        await msg.edit(view=ui.LayoutView().add_item(con))

        key = f"{self.depositor.value}_{self.amount.value}"
        success = False
        for _ in range(60):
            if pending_deposits.get(key):
                success = True
                del pending_deposits[key]
                break
            await asyncio.sleep(5)

        con.clear_items()
        
        if success:
            con.accent_color = 0xffffff
            con.add_item(ui.TextDisplay("## 충전 처리 중"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("유저 DB에 충전 기록 저장 중 (1/2)"))
            await msg.edit(view=ui.LayoutView().add_item(con))
            
            await asyncio.sleep(1.5)
            
            con.clear_items()
            con.add_item(ui.TextDisplay("## 충전 처리 중"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("입금 금액 반영 중 (2/2)"))
            await msg.edit(view=ui.LayoutView().add_item(con))

            conn = sqlite3.connect('robux_shop.db')
            cur = conn.cursor()
            cur.execute("INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?", 
                        (str(it.user.id), int(self.amount.value), int(self.amount.value)))
            conn.commit()
            conn.close()

            await asyncio.sleep(1.5)

            con.clear_items()
            con.accent_color = 0x57F287
            con.add_item(ui.TextDisplay(f"## 충전 완료"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay(f"<@{it.user.id}> 님의 잔액이 성공적으로 충전되었습니다\n**충전 금액:** `{int(self.amount.value):,}원`"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("-# 내 정보 버튼을 눌러 잔액을 확인하실 수 있습니다"))
        
        else:
            con.accent_color = 0xED4245
            con.add_item(ui.TextDisplay("## 충전 실패"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("시간 내에 입금이 확인되지 않았습니다\n다시 충전 신청을 해주세요"))
        
        await msg.edit(view=ui.LayoutView().add_item(con))

class RobuxVending(ui.LayoutView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def build_main_menu(self, it: discord.Interaction = None):
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
        con.add_item(ui.TextDisplay(f"```현재 재고: {stock_display}```"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        buy = ui.Button(label="공지", emoji="<:emoji_16:1486337864953495743>")
        buy.callback = self.buy_callback
        
        shop = ui.Button(label="구매", emoji="<:emoji_13:1486337836796874905>")
        shop.callback = self.shop_callback
        
        charge = ui.Button(label="충전", emoji="<:emoji_14:1486337849367330857>", custom_id="charge")
        charge.callback = self.main_callback
        
        info = ui.Button(label="정보", emoji="<:emoji_13:1486337822989484212>")
        info.callback = self.info_callback
        
        row = ui.ActionRow(buy, shop, charge, info)
        con.add_item(row)
        self.add_item(con)

    async def buy_callback(self, it: discord.Interaction):
        await it.response.send_message("공지사항 준비 중", ephemeral=True)

    async def shop_callback(self, it: discord.Interaction):
        await it.response.send_message("제품 목록 준비 중", ephemeral=True)

    async def info_callback(self, it: discord.Interaction):
        """해외 V2 스타일 프로필 적용 버전 (에러 해결)"""
        
        u_id = str(it.user.id)
        money = 0
        try:
            conn = sqlite3.connect('robux_shop.db')
            cur = conn.cursor()
            cur.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
            row = cur.fetchone()
            conn.close()
            if row: money = row[0]
        except: pass

        roles = [role.name for role in it.user.roles if role.name != "@everyone"]
        role_grade = roles[-1] if roles else "Guest"

        con = ui.Container()
        con.accent_color = 0xffffff

        con.add_item(ui.TextDisplay(
            f"## {it.user.display_name} 님의 정보"))
        
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        info_text = (
            f"> **보유 잔액:** `{money:,}원`\n"
            f"> **사용 금액:** `0원`\n"
            f"> **역할 등급:** `{role_grade}`\n"
            f"> **할인 혜택:** `0%`"
        )
        con.add_item(ui.TextDisplay(info_text))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        selecao = ui.Select(placeholder="조회할 내역 선택", options=[
            discord.SelectOption(label="최근 충전 내역", value="charge"),
            discord.SelectOption(label="최근 구매 내역", value="purchase")
        ])
        
        async def res_cb(i: discord.Interaction):
            await i.response.send_message(f"{selecao.values[0]} 내역이 없습니다", ephemeral=True)
        selecao.callback = res_cb
        
        con.add_item(ui.ActionRow(selecao))
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

    async def main_callback(self, it: discord.Interaction):
        cid = it.data.get('custom_id')
        if cid == "charge":
            con = ui.Container()
            con.accent_color = 0xffffff
            con.add_item(ui.TextDisplay("## 충전 수단 선택"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("원하시는 충전 방식을 선택해주세요"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            btn_bank = ui.Button(label="계좌이체", style=discord.ButtonStyle.gray)
            async def bank_cb(i: discord.Interaction):
                await i.response.send_modal(ChargeModal())
            btn_bank.callback = bank_cb
            con.add_item(ui.ActionRow(btn_bank))
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.vending_msg_info = {} # channel_id: message_id

    async def setup_hook(self):
        self.stock_updater.start()

    @tasks.loop(minutes=2.0)
    async def stock_updater(self):
        """2분마다 모든 활성화된 자판기 메시지를 실시간 재고로 업데이트"""
        for channel_id, msg_id in list(self.vending_msg_info.items()):
            try:
                channel = self.get_channel(channel_id)
                if not channel: continue
                msg = await channel.fetch_message(msg_id)
                
                view = RobuxVending(self)
                new_con = await view.build_main_menu()
                await msg.edit(view=ui.LayoutView().add_item(new_con))
            except Exception as e:
                print(f"Update Failed for {msg_id}: {e}")

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
