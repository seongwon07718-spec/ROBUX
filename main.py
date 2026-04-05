@bot.tree.command(name="관리자설정", description="관리자 ID를 설정합니다")
async def 관리자설정(it: discord.Interaction):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES ('admin_id', ?)",
            (str(it.user.id),)
        )
        conn.commit()
    await it.response.send_message("✅ 관리자로 설정되었습니다", ephemeral=True)
