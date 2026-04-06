# main.py 상단에 추가
import aiohttp

COIN_LIST = {
    "ltc": ("라이트코인", "LTC"),
    "trx": ("트론", "TRX"),
    "btc": ("비트코인", "BTC"),
    "sol": ("솔라나", "SOL"),
}


@bot.tree.command(name="코인설정", description="NOWPayments API 키를 설정합니다")
@app_commands.describe(api_key="NOWPayments API 키")
async def 코인설정(it: discord.Interaction, api_key: str):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('nowpayments_key', ?)", (api_key,))
        conn.commit()

    await it.response.send_message(
        view=await get_container_view("<:upvote:1489930275868770305>  설정 완료", "-# - NOWPayments API 키가 등록되었습니다", 0x57F287),
        ephemeral=True
    )
