@bot.tree.command(name="블랙", description="유저를 블랙리스트에 추가하거나 해제합니다.")
@discord.app_commands.describe(유저="블랙 관리할 유저", 여부="차단 또는 해제 선택")
@discord.app_commands.choices(여부=[
    discord.app_commands.Choice(name="차단", value=1),
    discord.app_commands.Choice(name="해제", value=0)
])
async def black_manage(interaction: discord.Interaction, 유저: discord.Member, 여부: int):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)

    u_id = str(유저.id)
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()
    
    # 유저 데이터 확인 및 블랙 상태 업데이트
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
    cur.execute("UPDATE users SET is_blacked = ? WHERE user_id = ?", (여부, u_id))
    
    conn.commit()
    conn.close()

    status_text = "차단" if 여부 == 1 else "해제"
    color = 0xff0000 if 여부 == 1 else 0x00ff00
    
    container = ui.Container(ui.TextDisplay(f"## 🚫 블랙리스트 {status_text}"), accent_color=color)
    container.add_item(ui.TextDisplay(f"대상: {유저.mention}\n상태: 해당 유저가 블랙리스트에서 **{status_text}**되었습니다."))
    
    await interaction.response.send_message(view=ui.LayoutView().add_item(container))
