import discord
from discord import ui, app_commands
from discord.ext import tasks, commands
import requests
import sqlite3
import asyncio
from datetime import datetime

# --- 설정 및 데이터베이스 ---
DATABASE = 'robux_shop.db'
TOKEN = "YOUR_BOT_TOKEN_HERE"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

init_db()

# --- [강화된 보안 로그인 로직] ---
# 외국 오픈소스에서 사용하는 CSRF 토큰 갱신 및 세션 우회 방식
def get_roblox_data(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    
    clean_cookie = cookie.strip()
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", clean_cookie, domain=".roblox.com")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com"
    }

    try:
        # 1. CSRF 토큰 강제 추출 (Logout Trick)
        # 이 과정이 없으면 무조건 403 보안 차단이 뜹니다.
        auth_res = session.post("https://auth.roblox.com/v2/logout", headers=headers, timeout=5)
        csrf_token = auth_res.headers.get("x-csrf-token")
        
        if csrf_token:
            headers["X-CSRF-TOKEN"] = csrf_token
        
        # 2. 잔액 및 유저 정보 확인
        url = "https://economy.roblox.com/v1/users/authenticated/currency"
        response = session.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            return response.json().get("robux", 0), "정상"
        elif response.status_code == 401:
            return 0, "쿠키 만료"
        elif response.status_code == 403:
            return 0, "보안 차단 (CSRF/IP)"
        else:
            return 0, f"Error {response.status_code}"
    except Exception as e:
        return 0, f"연결 실패"

# --- UI 헬퍼 함수 ---
def create_container_msg(title, content, color=0x5865F2):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"## {title}"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(content))
    return con

# --- [자판기 메인 UI 클래스] ---
class RobuxVending(ui.LayoutView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def build_main_menu(self):
        """사진 속 Section 에러와 NoneType 에러를 완벽히 해결한 빌더"""
        con = ui.Container()
        con.accent_color = 0x5865F2
        
        try:
            # 1. 쿠키 데이터 가져오기
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
            row = cur.fetchone()
            conn.close()

            cookie = row[0] if row else None
            robux, status = get_roblox_data(cookie)
            stock_text = f"{robux:,} R$" if status == "정상" else f"점검 중 ({status})"

            # 2. 실시간 재고 섹션
            stock_section = ui.Section(
                ui.TextDisplay(f"### ✨ 실시간 재고\n-# 현재 판매 가능한 로벅스 수량입니다.\n\n**현재 재고: `{stock_text}`**"),
                accessory=ui.Button(label="재고 확인", style=discord.ButtonStyle.secondary, disabled=True, emoji="📦")
            )
            con.add_item(stock_section)
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            # 3. 지급방식 섹션 (사진 219번 줄 에러 해결 포인트)
            # Section 선언 시 반드시 accessory를 인자로 넣어야 합니다.
            info_section = ui.Section(
                ui.TextDisplay(
                    "### 💠 지급방식\n"
                    "- 게임패스 방식 / 무조건 본인 게임만\n"
                    "- 글로벌 선물 방식 / 예시) 라이벌 - 번들\n\n"
                    "### 💠 버튼 안내\n"
                    "- **충전** - 충전하기 / 24시간 자동 충전\n"
                    "- **정보** - 내 정보 확인하기 / 구매 내역\n"
                    "- **구매** - 로벅스 구매하기"
                ),
                accessory=ui.Thumbnail(media="https://cdn.discordapp.com/attachments/1485111392087314432/1487425365507833956/IMG_0013.png")
            )
            con.add_item(info_section)
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            # 4. 하단 버튼 액션로우
            btn_charge = ui.Button(label="충전", style=discord.ButtonStyle.blurple, emoji="💳")
            btn_charge.callback = self.charge_callback
            
            btn_info = ui.Button(label="정보", style=discord.ButtonStyle.blurple, emoji="👤")
            btn_info.callback = self.info_callback

            btn_buy = ui.Button(label="구매", style=discord.ButtonStyle.blurple, emoji="🛒")
            btn_buy.callback = self.buy_callback
            
            con.add_item(ui.ActionRow(btn_charge, btn_info, btn_buy))

        except Exception as e:
            con.add_item(ui.TextDisplay(f"⚠️ UI 생성 오류: {e}"))
            print(f"DEBUG ERROR: {e}")

        # 기존 아이템 비우고 컨테이너 추가
        self.clear_items()
        self.add_item(con)
        return con # 절대 None이 아님

    async def charge_callback(self, it: discord.Interaction):
        await it.response.send_modal(CookieModal())

    async def info_callback(self, it: discord.Interaction):
        con = create_container_msg("👤 내 정보", f"현재 {it.user.mention} 님의 정보를 조회할 수 없습니다.")
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

    async def buy_callback(self, it: discord.Interaction):
        con = create_container_msg("🛒 구매하기", "현재 준비된 상품이 없습니다.")
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

# --- [쿠키 입력 모달] ---
class CookieModal(ui.Modal, title="보안 인증: 로블록스 쿠키 등록"):
    cookie_input = ui.TextInput(
        label="로블록스 쿠키 (.ROBLOSECURITY)",
        placeholder="_|WARNING:-DO-NOT-SHARE-THIS... 전체 입력",
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
            
            con = create_container_msg("✅ 인증 성공", f"로블록스 계정이 연결되었습니다!\n현재 재고: **{robux:,} R$**", 0x57F287)
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        else:
            con = create_container_msg("❌ 인증 실패", f"쿠키 인식 실패: `{status}`\n사유를 확인해주세요.", 0xED4245)
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

# --- 봇 메인 클래스 ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

@bot.tree.command(name="자판기", description="실시간 재고 자판기를 소환합니다.")
async def spawn_vending(it: discord.Interaction):
    # 사진 속 spawn_vending 로직 수정
    view = RobuxVending(bot)
    con = await view.build_main_menu() # con은 이제 절대 None이 아닙니다.
    
    # 1. 먼저 상호작용에 응답 (add_item(con) 필수)
    await it.response.send_message(view=ui.LayoutView().add_item(con))

bot.run(TOKEN)

