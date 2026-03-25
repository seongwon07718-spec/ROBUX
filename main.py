import discord
from discord import app_commands, ui
from discord.ext import commands
import sqlite3

# --- 봇 설정 ---
TOKEN = "YOUR_BOT_TOKEN"
intents = discord.Intents.all()

class RobuxVendingBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 데이터베이스 초기화 (유저 잔액 등 저장용)
        conn = sqlite3.connect('robux_shop.db')
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)")
        conn.commit()
        conn.close()
        await self.tree.sync()
        print(f"로그인 완료: {self.user}")

bot = RobuxVendingBot()

# --- 자판기 메뉴 뷰 ---
class RobuxVendingMenu(ui.LayoutView):
    def __init__(self):
        super().__init__()
        # 메인 컨테이너 생성
        self.container = ui.Container()
        self.container.accent_color = 0x00AAFF # 하늘색 강조
        
        # 제목 및 설명 추가
        self.container.add_item(ui.TextDisplay("## 🤖 로벅스 자동 자판기"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(
            "안전하고 빠른 로벅스 충전 서비스를 이용해 보세요!\n"
            "아래 버튼을 클릭하여 원하는 메뉴를 선택하실 수 있습니다."
        ))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 버튼 생성 (ActionRow로 묶기)
        row = ui.ActionRow()
        
        btn_notice = ui.Button(label="공지사항", style=discord.ButtonStyle.gray, emoji="📢")
        btn_notice.callback = self.notice_callback
        
        btn_buy = ui.Button(label="로벅스 구매", style=discord.ButtonStyle.green, emoji="🛒")
        btn_buy.callback = self.buy_callback
        
        btn_charge = ui.Button(label="잔액 충전", style=discord.ButtonStyle.blurple, emoji="💳")
        btn_charge.callback = self.charge_callback
        
        btn_info = ui.Button(label="내 정보", style=discord.ButtonStyle.gray, emoji="👤")
        btn_info.callback = self.info_callback

        # 버튼들을 한 줄(ActionRow)에 추가
        row.add_item(btn_notice)
        row.add_item(btn_buy)
        row.add_item(btn_charge)
        row.add_item(btn_info)

        # 컨테이너에 ActionRow 추가
        self.container.add_item(row)
        
        # 하단 꼬리말
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("-# 이용 중 문의사항은 고객센터를 이용해 주세요."))
        
        # 최종적으로 뷰에 컨테이너 추가
        self.add_item(self.container)

    # --- 각 버튼 콜백 함수 ---
    async def notice_callback(self, it: discord.Interaction):
        await it.response.send_message("📢 공지사항: 현재 시스템 정상 작동 중입니다.", ephemeral=True)

    async def buy_callback(self, it: discord.Interaction):
        await it.response.send_message("🛒 구매 메뉴를 불러오는 중입니다...", ephemeral=True)

    async def charge_callback(self, it: discord.Interaction):
        await it.response.send_message("💳 충전 수단을 선택해 주세요. (계좌이체/문상 등)", ephemeral=True)

    async def info_callback(self, it: discord.Interaction):
        # DB에서 잔액 조회 예시
        conn = sqlite3.connect('robux_shop.db')
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (str(it.user.id),))
        row = cur.fetchone()
        balance = row[0] if row else 0
        conn.close()
        
        await it.response.send_message(f"👤 **{it.user.name}** 님의 정보\n현재 보유 잔액: `{balance}원`", ephemeral=True)

# --- 슬래시 명령어 ---
@bot.tree.command(name="로벅스_자판기", description="로벅스 자판기 메인 메뉴를 출력합니다")
async def robux_vending(it: discord.Interaction):
    # 관리자 전용으로 만들고 싶다면 아래 주석 해제
    # if not it.user.guild_permissions.administrator:
    #     return await it.response.send_message("권한이 없습니다.", ephemeral=True)
    
    await it.response.send_message(view=RobuxVendingMenu())

if __name__ == "__main__":
    bot.run(TOKEN)

