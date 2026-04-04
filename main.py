import requests
import sqlite3
import discord
from discord import ui

# [참고] DATABASE 변수와 create_container_msg 함수는 기존 코드에 정의된 것을 사용합니다.

def get_roblox_data(cookie):
    """
    쿠키의 유효성을 검사하고 결과를 반환합니다.
    반환값: (성공여부, 로벅스 수량 또는 에러메시지)
    """
    if not cookie:
        return False, "입력된 쿠키가 없습니다."
    
    # 쿠키 포맷 정리
    auth_cookie = cookie.strip().strip('"').strip("'")
    if not auth_cookie.startswith(".ROBLOSECURITY="):
        full_cookie = f".ROBLOSECURITY={auth_cookie}"
    else:
        full_cookie = auth_cookie
    
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": full_cookie,
    }

    try:
        # 유저 인증 API 호출
        res = session.get("https://users.roblox.com/v1/users/authenticated", headers=headers, timeout=7)
        if res.status_code == 200:
            user_id = res.json().get('id')
            # 로벅스 수량 가져오기
            eco_res = session.get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers=headers, timeout=5)
            robux = eco_res.json().get('robux', 0) if eco_res.status_code == 200 else 0
            return True, robux
        return False, "만료되었거나 잘못된 쿠키입니다."
    except:
        return False, "로블록스 서버와 연결할 수 없습니다."

class CookieModal(ui.Modal, title="로블록스 쿠키 등록"):
    cookie_input = ui.TextInput(
        label="로블록스 쿠키",
        placeholder="_|WARNING:-DO-NOT-SHARE-THIS... 전체 입력",
        style=discord.TextStyle.long,
        required=True
    )

    async def on_submit(self, it: discord.Interaction):
        cookie = self.cookie_input.value
        # get_roblox_data는 (성공여부, 로벅스_또는_에러메시지)를 반환함
        is_success, result = get_roblox_data(cookie)
        
        if is_success:
            # ✅ 인증 및 등록 성공
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('roblox_cookie', ?)", (cookie,))
            conn.commit()
            conn.close()
            
            # 초록색 컨테이너 (result는 로벅스 수량)
            con = create_container_msg("✅ 쿠키 등록 성공", f"로블록스 계정이 성공적으로 연결되었습니다!\n현재 재고: **{result:,} R$**", 0x57F287)
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        else:
            # ❌ 인증 실패 (result는 에러 메시지)
            # 빨간색 컨테이너 (0xED4245)
            con = create_container_msg("❌ 쿠키 등록 실패", f"인증에 실패하였습니다.\n사유: `{result}`", 0xED4245)
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

@bot.tree.command(name="자판기", description="로벅스 자판기를 전송합니다.")
async def spawn_vending(it: discord.Interaction):
    con_notif = create_container_msg("-# - 자판기가 성공적으로 전송되었습니다", 0x5865F2)
    await it.response.send_message(view=ui.LayoutView().add_item(con_notif), ephemeral=True)
    
    view = RobuxVending(bot)
    con = await view.build_main_menu()
    msg = await it.channel.send(view=ui.LayoutView().add_item(con))
    bot.vending_msg_info[it.channel_id] = msg.id
