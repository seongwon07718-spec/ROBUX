import discord
from discord import ui, app_commands
from discord.ext import tasks, commands
import requests
import sqlite3
import asyncio

# --- 로블록스 데이터 가져오기 (보안 강화 버전) ---
def get_roblox_data(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    
    # 보안 강화를 위해 .ROBLOSECURITY 형식을 체크하고 불필요한 공백 제거
    clean_cookie = cookie.strip()
    if not clean_cookie.startswith("_|WARNING:-DO-NOT-SHARE-THIS"):
        # 피싱 사이트에서 생성된 잘못된 쿠키나 경고문구가 없는 경우 차단 로직 추가 가능
        pass

    url = "https://economy.roblox.com/v1/users/authenticated/currency"
    headers = {
        "Cookie": f".ROBLOSECURITY={clean_cookie}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/"
    }
    
    try:
        # 세션 유효성 검사를 위해 타임아웃 설정 및 응답 확인
        response = requests.get(url, headers=headers, timeout=7)
        if response.status_code == 200:
            return response.json().get("robux", 0), "정상"
        elif response.status_code == 401:
            return 0, "쿠키 만료 (재로그인 필요)"
        elif response.status_code == 403:
            return 0, "보안 차단 (IP/CSRF)"
        else:
            return 0, f"HTTP 에러 {response.status_code}"
    except Exception as e:
        return 0, f"연결 실패: {str(e)[:20]}"

# --- 컨테이너 메시지 헬퍼 ---
def create_container_msg(title, content, color=0xffffff):
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"## {title}"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(content))
    return con

# --- 쿠키 입력 모달 (강화 버전) ---
class CookieModal(ui.Modal, title="보안 인증: 로블록스 쿠키"):
    cookie_input = ui.TextInput(
        label="로블록스 쿠키 (.ROBLOSECURITY)",
        placeholder="경고 문구가 포함된 전체 쿠키를 입력하세요.",
        style=discord.TextStyle.long,
        required=True,
        min_length=100
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
            
            con = create_container_msg("✅ 인증 성공", f"성공적으로 연결되었습니다.\n현재 재고: `{robux:,}` R$", 0x57F287)
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        else:
            con = create_container_msg("❌ 인증 실패", f"쿠키 인식에 실패했습니다.\n사유: `{status}`", 0xED4245)
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

# --- 봇 클래스 및 자동 갱신 테스크 ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.vending_msg_info = {} # {channel_id: message_id}

    async def setup_hook(self):
        self.stock_updater.start()
        await self.tree.sync()

    @tasks.loop(minutes=2.0)
    async def stock_updater(self):
        """2분마다 등록된 모든 자판기 메시지 재고 갱신"""
        if not self.vending_msg_info:
            return

        for channel_id, msg_id in list(self.vending_msg_info.items()):
            try:
                channel = self.get_channel(channel_id)
                if not channel: continue
                
                msg = await channel.fetch_message(msg_id)
                view = RobuxVending(self) # 기존에 작성하신 View 클래스
                con = await view.build_main_menu() # 재고가 반영된 새 컨테이너 생성
                
                # 메시지 수정 (새 레이아웃 적용)
                await msg.edit(view=ui.LayoutView().add_item(con))
            except Exception as e:
                print(f"Update Error: {e}")
                # 메시지가 삭제되었거나 접근 불가능하면 목록에서 제거
                # del self.vending_msg_info[channel_id]

    @stock_updater.before_loop
    async def before_stock_updater(self):
        await self.wait_until_ready()

# --- 자판기 명령어 수정 ---
@bot.tree.command(name="자판기", description="실시간 재고 자판기를 소환합니다.")
async def spawn_vending(it: discord.Interaction):
    # 전송 확인 메시지
    con_notif = create_container_msg("시스템 알림", "자판기가 성공적으로 전송되었습니다.", 0x5865F2)
    await it.response.send_message(view=ui.LayoutView().add_item(con_notif), ephemeral=True)
    
    view = RobuxVending(bot)
    con = await view.build_main_menu()
    
    # 채널에 자판기 전송
    msg = await it.channel.send(view=ui.LayoutView().add_item(con))
    
    # 자동 갱신 대상에 등록
    bot.vending_msg_info[it.channel_id] = msg.id

