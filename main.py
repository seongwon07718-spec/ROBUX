@bot.tree.command(name="잔액", description="유저의 잔액을 추가하거나 차감합니다 (관리자 전용)")
@discord.app_commands.describe(유저="잔액을 관리할 유저", 금액="설정할 금액", 여부="추가 또는 차감 선택")
@discord.app_commands.choices(여부=[
    discord.app_commands.Choice(name="추가", value="추가"),
    discord.app_commands.Choice(name="차감", value="차감")
])
async def balance_manage(interaction: discord.Interaction, 유저: discord.Member, 금액: int, 여부: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)

    u_id = str(유저.id)
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()

    # 유저 데이터 확인 및 생성
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
    
    if 여부 == "추가":
        cur.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (금액, u_id))
        method_text = "관리자 추가"
    else:
        cur.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (금액, u_id))
        method_text = "관리자 차감"

    # ✅ 충전 로그에 기록 저장
    cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                (u_id, 금액 if 여부 == "추가" else -금액, time.strftime('%Y-%m-%d %H:%M'), method_text))
    
    conn.commit()
    conn.close()

    # 결과 컨테이너 전송
    embed_color = 0x00ff00 if 여부 == "추가" else 0xff0000
    container = ui.Container(ui.TextDisplay(f"## 💰 잔액 {여부} 완료"), accent_color=embed_color)
    container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(f"대상: {유저.mention}\n금액: **{금액:,}원**\n결과: 잔액이 정상적으로 {여부}되었습니다."))
    
    await interaction.response.send_message(view=ui.LayoutView().add_item(container))

    # 유저에게 알림 (선택 사항)
    try:
        await 유저.send(f"**관리자에 의해 잔액이 {금액:,}원 {여부}되었습니다.**")
    except:
        pass
