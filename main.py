@bot.tree.command(name="로그채널설정", description="구매 로그 채널을 설정합니다")
@app_commands.describe(채널="로그를 전송할 채널")
async def 로그채널설정(it: discord.Interaction, 채널: discord.TextChannel):

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
            "INSERT OR REPLACE INTO config (key, value) VALUES ('log_channel_id', ?)",
            (str(채널.id),)
        )
        conn.commit()

    await it.response.send_message(
        view=await get_container_view(
            "<:upvote:1489930275868770305>  로그 채널 설정 완료",
            f"-# - 로그 채널: {채널.mention}",
            0x57F287
        ),
        ephemeral=True
    )
