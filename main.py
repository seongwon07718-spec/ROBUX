def build_rank_container(guild_id):
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    cur.execute("SELECT inviter_id, used_count FROM invites WHERE server_id = ? ORDER BY used_count DESC LIMIT 10", (str(guild_id),))
    rows = cur.fetchall()
    conn.close()

    con = ui.Container()
    con.accent_color = 0xffffff
    con.add_item(ui.TextDisplay("## 실시간 초대 랭킹"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

    if not rows:
        con.add_item(ui.TextDisplay("아직 집계된 데이터가 없습니다"))
    else:
        for i, (uid, count) in enumerate(rows, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
            con.add_item(ui.TextDisplay(f"{emoji} **{i}위** | <@{uid}>\n> 초대 성공: `{count}명`"))
            if i < len(rows):
                con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

    return con
