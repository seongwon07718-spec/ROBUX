# 블랙리스트 확인 공통 함수
async def check_black(interaction: discord.Interaction):
    u_id = str(interaction.user.id)
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()
    cur.execute("SELECT is_blacked FROM users WHERE user_id = ?", (u_id,))
    row = cur.fetchone()
    conn.close()
    
    if row and row[0] == 1:
        # 블랙 유저일 경우: 응답을 아예 하지 않거나 에러 메시지를 띄움
        # '상호작용 오류'를 유도하려면 아래 한 줄만 쓰면 됩니다.
        return True 
    return False

# 예시: MeuLayout 내 콜백 수정
class MeuLayout(ui.LayoutView):
    # ... (기존 __init__ 생략)

    async def shop_callback(self, it: discord.Interaction):
        if await check_black(it): return # 블랙이면 여기서 중단 (상호작용 오류 발생)
        await it.response.send_message("준비중입니다", ephemeral=True)

    async def chage_callback(self, it: discord.Interaction):
        if await check_black(it): return
        await it.response.send_message(view=ChargeLayout(), ephemeral=True)

    async def info_callback(self, it: discord.Interaction):
        if await check_black(it): return
        # ... (이후 기존 정보 조회 로직)
