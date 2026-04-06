@bot.tree.command(name="충전설정", description="자동충전 server_id와 pw를 설정합니다")
@app_commands.describe(server_id="서버 ID", pw="비밀번호")
async def 충전설정(it: discord.Interaction, server_id: str, pw: str):

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
        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('charge_server_id', ?)", (server_id,))
        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('charge_pw', ?)", (pw,))
        conn.commit()

    await it.response.send_message(
        view=await get_container_view(
            "<:upvote:1489930275868770305>  설정 완료",
            f"-# - server_id: `{server_id}`\n-# - pw: `{pw}`",
            0x57F287
        ),
        ephemeral=True
    )
