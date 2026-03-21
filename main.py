@bot.tree.command(name="인증유저", description="인증 완료된 유저 수를 확인합니다")
async def total_users(it: discord.Interaction):
    conn = sqlite3.connect('restore_user.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM users")
    user_count = cursor.fetchone()[0]
    conn.close()

    verify_con = ui.Container()
    verify_con.accent_color = 0xffffff 
    
    verify_con.add_item(ui.TextDisplay("## 인증 유저 통계"))
    verify_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    verify_con.add_item(ui.TextDisplay(f"**인증 완료된 유저수**\n```{user_count}명```"))
    verify_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    verify_con.add_item(ui.TextDisplay("-# DB는 365일 안전하게 보관됩니다"))
    
    view = ui.LayoutView().add_item(verify_con)
    await it.response.send_message(view=view, ephemeral=True)
