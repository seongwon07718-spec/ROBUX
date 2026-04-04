import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import requests
import sqlite3
import asyncio

# --- 데이터베이스 및 기본 설정 ---
DATABASE = 'robux_shop.db'
BANK_K = "카카오뱅크 3333-xx-xxxxxxx (예금주)" # 실제 계좌로 수정 필요
pending_deposits = {}

# --- [수정] 언패킹 에러 해결을 위한 리턴값 조정 ---
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
        # CSRF 토큰 획득
        token_response = session.post("https://auth.roblox.com/v2/logout", headers=headers, timeout=5)
        x_token = token_response.headers.get("x-csrf-token")

        if not x_token:
            return 0, "보안 점검"

        session.headers.update({"X-CSRF-TOKEN": x_token})

        # 잔액 조회
        economy_url = "https://economy.roblox.com/v1/users/authenticated/currency"
        final_res = session.get(economy_url, headers=headers, timeout=5)

        if final_res.status_code == 200:
            data = final_res.json()
            return data.get('robux', 0), "정상"
        elif final_res.status_code == 401:
            return 0, "쿠키 만료"
        else:
            return 0, f"차단 ({final_res.status_code})"

    except Exception:
        return 0, "연결 오류"

# --- [수정] 자판기 메인 View (타임아웃 제거 및 Section 에러 해결) ---
class RobuxVending(ui.LayoutView):
    def __init__(self, bot):
        super().__init__(timeout=None) # 타임아웃 제거
        self.bot = bot

    async def build_main_menu(self):
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
        conn.close()

        cookie = row[0] if row else None
        robux, status = get_roblox_data(cookie) # 이제 ValueError 안남
        stock_display = f"{robux:,} R$" if status == "정상" else f"점검 중 ({status})"

        con = ui.Container()
        con.accent_color = 0x5865F2
        
        # [해결] Section 필수 인자 accessory 명시
        con.add_item(ui.Section(
            ui.TextDisplay("### <:emoji_18:1487422236838334484>  실시간 재고"),
            accessory=ui.Button(label=f"재고: {stock_display}", style=discord.ButtonStyle.blurple, disabled=True)
        ))

        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # [해결] 썸네일을 Section의 accessory로 포함시켜 Invalid Form Body 방지
        info_section = ui.Section(
            ui.TextDisplay("### <:emoji_18:1487422236838334484>  지급방식\n-# - **게임패스 방식** / 무조건 본인 게임만\n-# - **글로벌 선물 방식** / 예시: 라이벌 - 번들"),
            accessory=ui.Thumbnail(media="https://cdn.discordapp.com/attachments/1485111392087314432/1487425365507833956/IMG_0013.png")
        )
        con.add_item(info_section)
        
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 버튼들
        charge = ui.Button(label="충전", custom_id="charge", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        charge.callback = self.main_callback # 외부에서 정의된 콜백 연결 필요
        
        info = ui.Button(label="정보", custom_id="info", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        info.callback = self.info_callback

        shop = ui.Button(label="구매", custom_id="buying", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        shop.callback = self.shop_callback
        
        con.add_item(ui.ActionRow(charge, info, shop))
        
        self.clear_items()
        self.add_item(con)
        return con

    # 콜백 함수 예시 (기존 코드에 맞춰 사용)
    async def main_callback(self, it): pass
    async def info_callback(self, it): pass
    async def shop_callback(self, it): pass

# --- [수정] 충전 모달 (copy_callback 부재 및 edit_message 에러 해결) ---
class ChargeModal(ui.Modal, title="로벅스 충전 신청"):
    amount = ui.TextInput(label="충전 금액", placeholder="숫자만 입력 (예: 5000)", min_length=1)
    depositor = ui.TextInput(label="입금자명", placeholder="실명을 입력해주세요", min_length=2)

    async def copy_callback(self, it: discord.Interaction):
        # 복사 기능을 위한 텍스트 전송
        await it.response.send_message(content=f"{BANK_K}", ephemeral=True)

    async def on_submit(self, it: discord.Interaction):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### <a:1792loading:1487444148716965949>  충전 준비 중\n-# - **충전 서버 API** 연결 시도중 (1/3)"))
        
        # 첫 응답
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        msg = await it.original_response()

        steps = [
            "-# - **입금자명/충전금액** 설정 중 (2/3)",
            "-# - **안전한 충전**을 위한 설정 중 (3/3)",
            "-# - **모든 설정이 완료되었습니다**"
        ]

        for step in steps:
            await asyncio.sleep(1.2)
            con.clear_items()
            con.add_item(ui.TextDisplay(f"### <a:1792loading:1487444148716965949>  충전 준비 중\n{step}"))
            await msg.edit(view=ui.LayoutView().add_item(con))

        await asyncio.sleep(1)
        con.clear_items()
        con.add_item(ui.TextDisplay("### <a:1792loading:1487444148716965949>  입금 대기 중"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay(f"**입금 계좌**: `{BANK_K}`\n**입금 금액**: `{int(self.amount.value):,}원`\n**입금자명**: `{self.depositor.value}`"))
        
        copy_btn = ui.Button(label="계좌복사", style=discord.ButtonStyle.gray, emoji="<:success:1489875582874554429>")
        copy_btn.callback = self.copy_callback # 이제 에러 안남
        
        con.add_item(ui.ActionRow(copy_btn))
        await msg.edit(view=ui.LayoutView().add_item(con))

        # 이후 입금 확인 로직...

