import discord
from discord import ui, app_commands
from discord.ext import commands
import sqlite3

# --- DB 초기화 확장 ---
def init_db_v2():
    conn = sqlite3.connect('robux_shop.db')
    cur = conn.cursor()
    # 가격 설정을 위한 테이블 (기본값 1.0당 1300)
    cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('robux_rate', '1300')")
    conn.commit()
    conn.close()

init_db_v2()

# --- 로벅스 계산기 모달 ---
class RobuxCalculatorModal(ui.Modal, title="로벅스 가격 계산기"):
    amount = ui.TextInput(label="구매하실 금액 (단위: 원)", placeholder="예: 10000", min_length=1)

    async def on_submit(self, it: discord.Interaction):
        try:
            money = int(self.amount.value)
            conn = sqlite3.connect('robux_shop.db')
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
            rate = int(cur.fetchone()[0])
            conn.close()

            # 1.0(만원)당 rate이므로 (금액 / 10000) * rate
            expected_robux = int((money / 10000) * rate)
            
            con = ui.Container()
            con.accent_color = 0x5865F2
            con.add_item(ui.TextDisplay("### 🧮 계산 결과"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay(
                f"- **입력 금액**: `{money:,}원`\n"
                f"- **현재 비율**: `1.0당 {rate} R$`\n\n"
                f"### 💰 예상 수령 로벅스: `{expected_robux:,} R$`"
            ))
            
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        except ValueError:
            await it.response.send_message("숫자만 입력해주세요.", ephemeral=True)

# --- 자판기 클래스 수정 ---
class RobuxVending(ui.LayoutView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def build_main_menu(self):
        conn = sqlite3.connect('robux_shop.db')
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
        conn.close()

        cookie = row[0] if row else None
        robux, status = get_roblox_data(cookie)
        stock_display = f"{robux:,} R$" if status == "정상" else f"{status}"

        con = ui.Container()
        con.accent_color = 0x5865F2
        
        # 실시간 재고
        con.add_item(ui.Section(
            ui.TextDisplay("### <:emoji_18:1487422236838334484>  실시간 재고"),
            accessory=ui.Button(label=f"현재 재고: {stock_display}", style=discord.ButtonStyle.blurple, disabled=True)
        ))

        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 지급방식
        con.add_item(ui.Section(
            ui.TextDisplay("### <:emoji_18:1487422236838334484>  지급방식\n-# - **게임패스 방식** / 무조건 본인 게임만\n-# - **글로벌 선물 방식** / 예시: 라이벌 - 번들"),
            accessory=ui.Thumbnail(media="https://cdn.discordapp.com/attachments/1485111392087314432/1487425365507833956/IMG_0013.png")
        ))
        
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 버튼 로우 1
        charge = ui.Button(label="충전", custom_id="charge", style=discord.ButtonStyle.blurple, emoji="💳")
        charge.callback = self.main_callback
        
        info = ui.Button(label="정보", custom_id="info", style=discord.ButtonStyle.blurple, emoji="👤")
        info.callback = self.info_callback

        shop = ui.Button(label="구매", custom_id="buying", style=discord.ButtonStyle.blurple, emoji="🛒")
        shop.callback = self.shop_callback
        
        # 버튼 로우 2 (계산기 추가)
        calc = ui.Button(label="계산기", custom_id="calc", style=discord.ButtonStyle.gray, emoji="🧮")
        calc.callback = self.calc_callback
        
        con.add_item(ui.ActionRow(charge, info, shop))
        con.add_item(ui.ActionRow(calc))
        
        self.clear_items()
        self.add_item(con)
        return con

    async def calc_callback(self, it: discord.Interaction):
        await it.response.send_modal(RobuxCalculatorModal())

    # --- 기존 콜백 생략 (수정 금지) ---
    async def main_callback(self, it): pass
    async def info_callback(self, it): pass
    async def shop_callback(self, it): 
        # 이전 응답 로직 유지...
        pass

# --- 새로운 슬래시 명령어 추가 ---
@bot.tree.command(name="가격설정", description="1.0(만원)당 지급할 로벅스 수량을 설정합니다.")
@app_commands.describe(수량="1.0당 지급할 로벅스 양 (예: 1300)")
async def set_rate(it: discord.Interaction, 수량: int):
    if not it.user.guild_permissions.administrator:
        await it.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)
        return

    conn = sqlite3.connect('robux_shop.db')
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('robux_rate', ?)", (str(수량),))
    conn.commit()
    conn.close()

    await it.response.send_message(f"✅ 가격 설정 완료: **1.0(만원)당 {수량:,} R$**", ephemeral=True)

