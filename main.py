async def send_log(log_type: str, view):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = ?", (log_type,))
            row = cur.fetchone()
        if row:
            channel = bot.get_channel(int(row[0]))
            if channel:
                await channel.send(view=view)
    except Exception as e:
        print(f"[로그 실패] {e}")


@bot.tree.command(name="로그설정", description="로그 채널을 설정합니다")
@app_commands.describe(종류="로그 종류", 채널="로그를 전송할 채널")
@app_commands.choices(종류=[
    app_commands.Choice(name="구매 로그", value="purchase_log"),
    app_commands.Choice(name="충전 로그", value="charge_log"),
    app_commands.Choice(name="수동충전 로그", value="manual_charge_log"),
    app_commands.Choice(name="주문취소 로그", value="cancel_log"),
    app_commands.Choice(name="할인 설정 로그", value="discount_log"),
])
async def 로그설정(it: discord.Interaction, 종류: app_commands.Choice[str], 채널: discord.TextChannel):

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
        cur.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (종류.value, str(채널.id))
        )
        conn.commit()

    await it.response.send_message(
        view=await get_container_view(
            "<:upvote:1489930275868770305>  설정 완료",
            f"-# - **{종류.name}** 채널: {채널.mention}",
            0x57F287
        ),
        ephemeral=True
    )
