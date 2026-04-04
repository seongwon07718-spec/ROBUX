import requests
import discord
from discord import ui
import sqlite3

# --- [수정 1] 보안 강화된 로블록스 데이터 요청 함수 ---
def get_roblox_data(cookie):
    if not cookie:
        return 0, "쿠키 없음"
    
    clean_cookie = cookie.strip()
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", clean_cookie, domain=".roblox.com")
    
    # 실제 브라우저와 유사한 헤더 설정 (IP/CSRF 차단 우회용)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.roblox.com/home",
        "Origin": "https://www.roblox.com"
    }

    try:
        # 1. CSRF 토큰을 얻기 위한 초기 요청
        auth_url = "https://auth.roblox.com/v2/logout" # 로그아웃 API는 403 에러와 함께 X-CSRF-TOKEN을 반환함
        auth_res = session.post(auth_url, headers=headers, timeout=5)
        csrf_token = auth_res.headers.get("x-csrf-token")
        
        if csrf_token:
            headers["X-CSRF-TOKEN"] = csrf_token

        # 2. 실제 잔액 조회 요청
        url = "https://economy.roblox.com/v1/users/authenticated/currency"
        response = session.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            return response.json().get("robux", 0), "정상"
        elif response.status_code == 401:
            return 0, "쿠키 만료"
        elif response.status_code == 403:
            return 0, "보안 차단 (CSRF 미일치)"
        else:
            return 0, f"에러 {response.status_code}"
    except Exception as e:
        return 0, f"연결 실패 ({str(e)[:10]})"

# --- [수정 2] build_main_menu 함수 (Section 문법 완벽 수정) ---
    async def build_main_menu(self):
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()
        conn.close()

        cookie = row[0] if row else None
        robux, status = get_roblox_data(cookie)
        stock_display = f"{robux:,} R$" if status == "정상" else f"점검 중 ({status})"

        con = ui.Container()
        con.accent_color = 0x5865F2
        
        # [해결] Section 생성 시 accessory 인자를 '키워드'로 직접 전달해야 합니다.
        # 사진에서 났던 missing 1 required argument 에러를 해결합니다.
        main_section = ui.Section(
            ui.TextDisplay(
                "### <:emoji_18:1487422236838334484>  지급방식\n-# - 겜패 선물 방식\n-# - 인게임 선물 방식\n\n"
                "### <:emoji_18:1487422236838334484>  버튼 안내\n-# - **Charge** - 충전 / **Info** - 내 정보 / **Buying** - 구매"
            ),
            accessory=ui.Thumbnail(media="https://cdn.discordapp.com/attachments/1485111392087314432/1487425365507833956/IMG_0013.png")
        )
        con.add_item(main_section)
        
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        # 실시간 재고 버튼 (비활성화 상태로 표시)
        stock_btn = ui.Button(label=f"현재 재고: {stock_display}", style=discord.ButtonStyle.secondary, disabled=True, emoji="📦")
        con.add_item(ui.ActionRow(stock_btn))
        
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 하단 조작 버튼
        charge = ui.Button(label="Charge", custom_id="charge", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        charge.callback = self.main_callback
        
        info = ui.Button(label="Info", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        info.callback = self.info_callback

        shop = ui.Button(label="Buying", style=discord.ButtonStyle.blurple, emoji="<:dot_white:1485105325500797069>")
        shop.callback = self.shop_callback
        
        con.add_item(ui.ActionRow(charge, info, shop))
        
        self.clear_items()
        self.add_item(con)
        return con

