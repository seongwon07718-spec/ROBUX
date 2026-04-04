import discord
from discord import ui, app_commands
from discord.ext import commands
import requests
import sqlite3
import asyncio

# --- 데이터베이스 및 설정 ---
DATABASE = 'robux_shop.db'
TOKEN = "YOUR_BOT_TOKEN"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

init_db()

# --- [수정] 에러 없는 로블록스 데이터 연동 로직 ---
def get_roblox_data(cookie):
    """
    반드시 (잔액, 상태) 두 개의 값을 리턴해야 ValueError가 발생하지 않습니다.
    """
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
        # 1. CSRF 토큰 탈취 (이게 없으면 403 보안 차단 뜸)
        token_res = session.post("https://auth.roblox.com/v2/logout", headers=headers, timeout=5)
        x_token = token_res.headers.get("x-csrf-token")

        if not x_token:
            return 0, "CSRF 획득 실패"

        session.headers.update({"X-CSRF-TOKEN": x_token})

        # 2. 잔액 조회
        economy_url = "https://economy.roblox.com/v1/users/authenticated/currency"
        final_res = session.get(economy_url, headers=headers, timeout=5)

        if final_res.status_code == 200:
            robux = final_res.json().get('robux', 0)
            return robux, "정상"
        elif final_res.status_code == 401:
            return 0, "쿠키 만료 (IP 차단)"
        else:
            return 0, f"보안 차단 ({final_res.status_code})"

    except Exception as e:
        return 0, f"연결 오류"

# --- UI 헬퍼 함수 ---
def create_container_msg(title, content, color=0x5865F2):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"## {title}"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(content))
    return con

# --- [수정] 자판기 메인 UI ---
class RobuxVending(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

    async def build_main_menu(self):
        """사진 속 Section 및 Invalid Form Body 에러를 완벽히 수정한 빌더"""
        con = ui.Container()
        con.accent_color = 0x5865F2

        try:
            # DB에서 쿠키 로드
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
            row = cur.fetchone()
            conn.close()

            cookie = row[0] if row else None
            robux, status = get_roblox_data(cookie)
            
            stock_display = f"{robux:,} R$" if status == "정상" else f"점검 중 ({status})"

            # [해결] Section 선언 시 반드시 TextDisplay와 accessory를 동시에 넣어야 함
            # accessory는 무조건 keyword-only 인자로 전달
            con.add_item(ui.Section(
                ui.TextDisplay(f"### ✨ 실시간 재고\n-# 현재 판매 가능한 로벅스 수량입니다.\n\n**현재 재고: `{stock_display}`**"),
                accessory=ui.Button(label="재고 확인", style=discord.ButtonStyle.secondary, disabled=True, emoji="📦")
            ))

            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            # [해결] 지급방식 섹션 수정
            info_section = ui.Section(
                ui.TextDisplay(
                    "### 💠 지급방식\n"
                    "- 게임패스 방식 / 무조건 본인 게임만\n"
                    "- 글로벌 선물 방식 / 예시) 라이벌 - 번들\n\n"
                    "### 💠 버튼 안내\n"
                    "- **Charge** - 충전하기 / 24시간 자동 충전\n"
                    "- **Info** - 내 정보 확인하기\n"
                    "- **Buying** - 로벅스 구매하기"
                ),
                accessory=ui.Thumbnail(media="https://cdn.discordapp.com/attachments/1485111392087314432/1487425365507833956/IMG_0013.png")
            )
            con.add_item(info_section)
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            # 하단 버튼 로우
            btn_charge = ui.Button(label="Charge", style=discord.ButtonStyle.blurple, emoji="💳")
            btn_charge.callback = self.on_charge
            
            btn_info = ui.Button(label="Info", style=discord.ButtonStyle.blurple, emoji="👤")
            btn_info.callback = self.on_info

            btn_buy = ui.Button(label="Buying", style=discord.ButtonStyle.blurple, emoji="🛒")
            btn_buy.callback = self.on_buy

            con.add_item(ui.ActionRow(btn_charge, btn_info, btn_buy))

        except Exception as e:
            con.add_item(ui.TextDisplay(f"⚠️ UI 생성 중 오류: {e}"))
            print(f"[DEBUG] {e}")

        self.clear_items()
        self.add_item(con)
        return con

    async def on_charge(self, it: discord.Interaction):
        await it.response.send_modal(CookieModal())

    async def on_info(self, it: discord.Interaction):
        await it.response.send_message("정보 조회 기능 준비 중...", ephemeral=True)

    async def on_buy(self, it: discord.Interaction):
        await it.response.send_message("구매 목록 준비 중...", ephemeral=True)

# --- [수정] 쿠키 모달 ---
class CookieModal(ui.Modal, title="보안 인증: 로블록스 쿠키 등록"):
    cookie_input = ui.TextInput(
        label="로블록스 쿠키 (.ROBLOSECURITY)",
        placeholder="_|WARNING:-DO-NOT-SHARE-THIS... 전체 입력",
        style=discord.TextStyle.long,
        required=True
    )

    async def on_submit(self, it: discord.Interaction):
        cookie = self.cookie_input.value
        # [해결] 이제 리턴값이 2개이므로 언패킹 에러가 나지 않습니다.
        robux, status = get_roblox_data(cookie)
        
        if status == "정상":
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('roblox_cookie', ?)", (cookie,))
            conn.commit()
            conn.close()
            
            con = create_container_msg("✅ 인증 성공", f"성공적으로 연동되었습니다.\n현재 잔액: **{robux:,} R$**", 0x57F287)
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        else:
            con = create_container_msg("❌ 인증 실패", f"인식 실패: `{status}`\n쿠키 또는 IP 차단 여부를 확인하세요.", 0xED4245)
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

# --- 실행부 ---
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.tree.command(name="자판기", description="자판기를 소환합니다.")
async def spawn(it: discord.Interaction):
    view = RobuxVending()
    con = await view.build_main_menu()
    # [해결] Invalid Form Body 에러 방지를 위해 View와 Container를 올바르게 전송
    await it.response.send_message(view=ui.LayoutView().add_item(con))

bot.run(TOKEN)

