import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import sqlite3
import requests
import asyncio

# --- 기본 설정 ---
DATABASE = 'robux_shop.db'

# --- [불변] 로벅스 데이터 연동 로직 ---
def get_roblox_data(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    auth_cookie = cookie.strip().strip('"').strip("'")
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", auth_cookie, domain=".roblox.com")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/"
    }
    try:
        token_res = session.post("https://auth.roblox.com/v2/logout", headers=headers, timeout=5)
        x_token = token_res.headers.get("x-csrf-token")
        if x_token:
            session.headers.update({"X-CSRF-TOKEN": x_token})
        economy_url = "https://economy.roblox.com/v1/users/authenticated/currency"
        final_res = session.get(economy_url, headers=headers, timeout=5)
        if final_res.status_code == 200:
            return final_res.json().get('robux', 0), "정상"
        return 0, f"오류({final_res.status_code})"
    except:
        return 0, "연결 실패"

# --- 자판기 메인 View ---
class RobuxVending(ui.LayoutView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def build_main_menu(self):
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        # 쿠키 가져오기
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        # 설정된 가격 비율 가져오기 (기본값 1300)
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        cookie = c_row[0] if c_row else None
        rate = r_row[0] if r_row else "1300"
        
        robux, status = get_roblox_data(cookie)
        stock_display = f"{robux:,} R$" if status == "정상" else f"{status}"

        con = ui.Container()
        con.accent_color = 0x5865F2
        
        # 1. 실시간 재고 및 가격 표시 (요청 사항 반영)
        con.add_item(ui.Section(
            ui.TextDisplay(
                f"### <:emoji_18:1487422236838334484>  실시간 정보\n"
                f"- **실시간 재고**: `{stock_display}`\n"
                f"- **실시간 가격**: `1.0 = {rate} R$`"
            ),
            accessory=ui.Button(label="새로고침", style=discord.ButtonStyle.secondary, disabled=True, emoji="🔄")
        ))

        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 2. 지급 방식 섹션
        con.add_item(ui.Section(
            ui.TextDisplay(
                "### <:emoji_18:1487422236838334484>  지급방식\n"
                "-# - **게임패스 방식** / 무조건 본인 게임만\n"
                "-# - **글로벌 선물 방식** / 예시: 라이벌 - 번들"
            ),
            accessory=ui.Thumbnail(media="https://cdn.discordapp.com/attachments/1485111392087314432/1487425365507833956/IMG_0013.png")
        ))
        
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 버튼 로우 구성
        charge = ui.Button(label="충전", custom_id="charge", style=discord.ButtonStyle.blurple, emoji="💳")
        charge.callback = self.main_callback
        
        info = ui.Button(label="정보", custom_id="info", style=discord.ButtonStyle.blurple, emoji="👤")
        info.callback = self.info_callback

        shop = ui.Button(label="구매", custom_id="buying", style=discord.ButtonStyle.blurple, emoji="🛒")
        shop.callback = self.shop_callback
        
        calc = ui.Button(label="계산기", custom_id="calc", style=discord.ButtonStyle.gray, emoji="🧮")
        calc.callback = self.calc_callback
        
        con.add_item(ui.ActionRow(charge, info, shop))
        con.add_item(ui.ActionRow(calc))
        
        self.clear_items()
        self.add_item(con)
        return con

    # --- 콜백 함수들 ---
    async def calc_callback(self, it: discord.Interaction):
        await it.response.send_modal(RobuxCalculatorModal())

    async def shop_callback(self, it: discord.Interaction):
        # 구매 방식 선택 컨테이너 (이전 요청사항 유지)
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### <:emoji_18:1487422236838334484>  구매 방식 선택"))
        btn_gp = ui.Button(label="게임패스", style=discord.ButtonStyle.gray, emoji="🎮")
        btn_ig = ui.Button(label="인게임", style=discord.ButtonStyle.gray, emoji="💎")
        btn_gr = ui.Button(label="그룹", style=discord.ButtonStyle.gray, emoji="👥")
        con.add_item(ui.ActionRow(btn_gp, btn_ig, btn_gr))
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

    async def main_callback(self, it): pass # 기존 로직 연결
    async def info_callback(self, it): pass # 기존 로직 연결

# --- 가격 설정 명령어 ---
@bot.tree.command(name="가격설정", description="1.0(만원)당 지급할 로벅스 수량을 설정합니다.")
@app_commands.describe(수량="1.0당 지급할 로벅스 양 (예: 1300)")
async def set_rate(it: discord.Interaction, 수량: int):
    if not it.user.guild_permissions.administrator:
        await it.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)
        return

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('robux_rate', ?)", (str(수량),))
    conn.commit()
    conn.close()

    await it.response.send_message(f"✅ 가격 설정 완료: **1.0 = {수량:,} R$**\n자판기 메뉴에 즉시 반영됩니다.", ephemeral=True)

