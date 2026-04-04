import requests
import sqlite3
import discord
from discord import ui, app_commands
from discord.ext import commands
import asyncio

# --- 설정 ---
DATABASE = 'robux_shop.db'
TOKEN = "YOUR_BOT_TOKEN"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    # 프록시 저장용 컬럼 추가
    cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

init_db()

# --- [강화] 로블록스 데이터 연동 (프록시 지원) ---
def get_roblox_data(cookie, proxy=None):
    if not cookie:
        return 0, "쿠키 없음"
        
    auth_cookie = cookie.strip().strip('"').strip("'")
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", auth_cookie, domain=".roblox.com")
    
    # 프록시 설정 (보안 차단 해결책)
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com"
    }

    try:
        # 1. CSRF 토큰 갱신 (Logout Trick)
        token_res = session.post("https://auth.roblox.com/v2/logout", headers=headers, proxies=proxies, timeout=7)
        x_token = token_res.headers.get("x-csrf-token")

        if x_token:
            headers["X-CSRF-TOKEN"] = x_token

        # 2. 잔액 조회
        economy_url = "https://economy.roblox.com/v1/users/authenticated/currency"
        final_res = session.get(economy_url, headers=headers, proxies=proxies, timeout=7)

        if final_res.status_code == 200:
            robux = final_res.json().get('robux', 0)
            return robux, "정상"
        elif final_res.status_code == 401:
            return 0, "쿠키 무효 (IP 불일치)"
        elif final_res.status_code == 403:
            return 0, "보안 차단 (IP 차단됨)"
        else:
            return 0, f"에러 {final_res.status_code}"

    except Exception as e:
        return 0, "연결 실패 (Timeout)"

# --- UI 유틸리티 ---
def create_container_msg(title, content, color=0x5865F2):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"## {title}"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(content))
    return con

# --- 자판기 메인 View ---
class RobuxVending(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

    async def build_main_menu(self):
        con = ui.Container()
        con.accent_color = 0x5865F2

        try:
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
            c_row = cur.fetchone()
            cur.execute("SELECT value FROM config WHERE key = 'proxy_url'")
            p_row = cur.fetchone()
            conn.close()

            cookie = c_row[0] if c_row else None
            proxy = p_row[0] if p_row else None
            
            robux, status = get_roblox_data(cookie, proxy)
            stock_text = f"{robux:,} R$" if status == "정상" else f"점검 중 ({status})"

            # [해결] Section & Accessory 구조
            con.add_item(ui.Section(
                ui.TextDisplay(f"### ✨ 실시간 재고\n**현재 재고: `{stock_text}`**\n-# 2분마다 자동으로 갱신됩니다."),
                accessory=ui.Button(label="새로고침", style=discord.ButtonStyle.secondary, disabled=True, emoji="📦")
            ))

            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            info_section = ui.Section(
                ui.TextDisplay(
                    "### 💠 이용 안내\n"
                    "- **Charge** : 로블록스 쿠키 및 프록시 설정\n"
                    "- **Buying** : 로벅스 구매 (준비 중)\n\n"
                    "⚠️ **보안 차단**이 뜨면 프록시를 설정하세요."
                ),
                accessory=ui.Thumbnail(media="https://cdn.discordapp.com/attachments/1485111392087314432/1487425365507833956/IMG_0013.png")
            )
            con.add_item(info_section)

            # 하단 버튼
            btn_charge = ui.Button(label="Charge", style=discord.ButtonStyle.blurple, emoji="💳")
            btn_charge.callback = self.on_charge
            btn_shop = ui.Button(label="Buying", style=discord.ButtonStyle.blurple, emoji="🛒")
            btn_shop.callback = self.on_shop
            
            con.add_item(ui.ActionRow(btn_charge, btn_shop))

        except Exception as e:
            con.add_item(ui.TextDisplay(f"⚠️ UI 로드 에러: {e}"))

        self.clear_items()
        self.add_item(con)
        return con

    async def on_charge(self, it: discord.Interaction):
        await it.response.send_modal(AdminModal())

    async def on_shop(self, it: discord.Interaction):
        await it.response.send_message("상품 준비 중입니다.", ephemeral=True)

# --- 어드민 설정 모달 (쿠키 + 프록시) ---
class AdminModal(ui.Modal, title="자판기 관리 설정"):
    cookie_in = ui.TextInput(label="로블록스 쿠키", style=discord.TextStyle.long, required=True)
    proxy_in = ui.TextInput(label="프록시 주소 (선택)", placeholder="http://id:pw@ip:port", required=False)

    async def on_submit(self, it: discord.Interaction):
        cookie = self.cookie_in.value
        proxy = self.proxy_in.value if self.proxy_in.value else None
        
        robux, status = get_roblox_data(cookie, proxy)
        
        if status == "정상":
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('roblox_cookie', ?)", (cookie,))
            if proxy:
                cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('proxy_url', ?)", (proxy,))
            conn.commit()
            conn.close()
            
            con = create_container_msg("✅ 설정 완료", f"현재 재고: **{robux:,} R$**\n데이터가 정상적으로 연동되었습니다.", 0x57F287)
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        else:
            con = create_container_msg("❌ 연동 실패", f"사유: `{status}`\n쿠키가 만료되었거나 IP가 차단되었습니다.", 0xED4245)
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

# --- 실행부 ---
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.tree.command(name="자판기", description="자판기를 소환합니다.")
async def spawn(it: discord.Interaction):
    view = RobuxVending()
    con = await view.build_main_menu()
    await it.response.send_message(view=ui.LayoutView().add_item(con))

bot.run(TOKEN)

