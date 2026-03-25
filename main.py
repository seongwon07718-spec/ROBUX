import discord
from discord import ui, app_commands
from discord.ext import tasks, commands
import sqlite3
import requests
import asyncio
import time

# --- DB 설정 ---
DATABASE = 'robux_shop.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    # 유저 정보 및 설정 테이블
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

init_db()

# --- 로블록스 실시간 API 유틸리티 (보안 강화) ---
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

# --- 쿠키 입력 모달 ---
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

# --- 자판기 메뉴 클래스 ---
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

        # 컨테이너 생성 (해외 V2 스타일)
        con = ui.Container()
        con.accent_color = 0xffffff
        
        # 타이틀 및 재고 표시
        con.add_item(ui.TextDisplay(f"## 🛒 로벅스 자판기"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        status_msg = (
            f"> <:dot_white:1482000567562928271> **현재 재고:** `{stock_display}`\n"
            f"> <:dot_white:1482000567562928271> **마지막 갱신:** <t:{int(time.time())}:R>"
        )
        con.add_item(ui.TextDisplay(status_msg))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 버튼 생성
        btn_buy = ui.Button(label="구매하기", emoji="🛒", style=discord.ButtonStyle.gray, custom_id="vending_buy")
        btn_charge = ui.Button(label="충전하기", emoji="💳", style=discord.ButtonStyle.gray, custom_id="vending_charge")
        btn_info = ui.Button(label="정보조회", emoji="👤", style=discord.ButtonStyle.gray, custom_id="vending_info")

        # 콜백 연결 (별도 함수로 관리)
        btn_buy.callback = self.on_buy
        btn_charge.callback = self.on_charge
        btn_info.callback = self.on_info

        con.add_item(ui.ActionRow(btn_buy, btn_charge, btn_info))
        return con

    async def on_buy(self, it: discord.Interaction):
        await it.response.send_message("준비 중인 기능입니다.", ephemeral=True)

    async def on_charge(self, it: discord.Interaction):
        await it.response.send_message("충전 메뉴를 로드합니다.", ephemeral=True)

    async def on_info(self, it: discord.Interaction):
        # 유저 정보 조회 로직 (가장 높은 역할 및 잔액)
        u_id = str(it.user.id)
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone()
        conn.close()
        
        money = row[0] if row else 0
        roles = [role.name for role in it.user.roles if role.name != "@everyone"]
        role_grade = roles[-1] if roles else "Guest"

        info_con = ui.Container()
        info_con.accent_color = 0xffffff
        info_con.add_item(ui.TextDisplay(f"## {it.user.display_name} 님의 정보"))
        
        info_text = (
            f"> <:dot_white:1482000567562928271> **보유 잔액:** `{money:,}`원\n"
            f"> <:dot_white:1482000567562928271> **역할 등급:** `{role_grade}`\n"
            f"> <:dot_white:1482000567562928271> **할인 혜택:** `0%`"
        )
        info_con.add_item(ui.TextDisplay(info_text))
        
        # 정보창 내역 선택 메뉴
        sel = ui.Select(placeholder="내역 조회", options=[
            discord.SelectOption(label="충전 내역", value="c"),
            discord.SelectOption(label="구매 내역", value="p")
        ])
        info_con.add_item(ui.ActionRow(sel))

        await it.response.send_message(view=ui.LayoutView().add_item(info_con), ephemeral=True)

# --- 봇 메인 클래스 ---
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

@bot.tree.command(name="쿠키", description="로블록스 관리자 쿠키를 설정합니다.")
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

bot.run("YOUR_TOKEN")

