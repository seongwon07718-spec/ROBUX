@bot.tree.command(name="초대랭킹", description="실시간 초대 랭킹 상위 10명을 확인합니다")
async def invite_ranking(it: discord.Interaction):
    def get_rank_text(guild_id):
        conn = sqlite3.connect('restore_user.db')
        cur = conn.cursor()
        cur.execute("SELECT inviter_id, used_count FROM invites WHERE server_id = ? ORDER BY used_count DESC LIMIT 10", (str(guild_id),))
        rows = cur.fetchall()
        conn.close()
        
        if not rows: return "아직 초대 데이터가 없습니다"
        
        text = ""
        for i, (uid, count) in enumerate(rows, 1):
            text += f"**{i}위** | <@{uid}> - `{count}명` 초대\n"
        return text

    con = ui.Container()
    con.accent_color = 0xffffff
    con.add_item(ui.TextDisplay("## 실시간 초대 랭킹"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(get_rank_text(it.guild_id)))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    con.add_item(ui.TextDisplay(f"-# 업데이트: {datetime.now().strftime('%H:%M:%S')}"))

    await it.response.send_message(view=ui.LayoutView().add_item(con))
