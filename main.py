@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"DONE SYNC COMMANDS - Logged in as {bot.user} (ID: {bot.user.id})")

@bot.tree.command(name="자판기", description="자판기 컨테이너를 전송합니다")
async def vending(interaction: discord.Interaction):
    await interaction.response.send_message("**자판기가 전송되었습니다**", ephemeral=True)
    await interaction.channel.send(view=MeuLayout())

@bot.tree.command(name="기본설정", description="입금 계좌 정보/자충 여부")
async def set_account(interaction: discord.Interaction):
    await interaction.response.send_modal(AccountSetupModal())

@bot.tree.command(name="잔액관리", description="유저의 잔액을 추가/차감")
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

    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
    
    if 여부 == "추가":
        cur.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (금액, u_id))
        method_text = "관리자 추가"
    else:
        cur.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (금액, u_id))
        method_text = "관리자 차감"

    cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                (u_id, 금액 if 여부 == "추가" else -금액, time.strftime('%Y-%m-%d %H:%M'), method_text))
    
    conn.commit()
    conn.close()

    embed_color = 0x00ff00 if 여부 == "추가" else 0xff0000
    container = ui.Container(ui.TextDisplay(f"## 잔액 {여부} 완료"), accent_color=embed_color)
    container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(f"대상: {유저.mention}\n금액: {금액:,}원\n잔액이 정상적으로 {여부}되었습니다"))
    
    await interaction.response.send_message(view=ui.LayoutView().add_item(container))

    try:
        dm_con = ui.Container(ui.TextDisplay(f"## 잔액 {여부} 안내"), accent_color=embed_color)
        dm_con.add_item(ui.TextDisplay(f"관리자에 의해 잔액이 **{금액:,}원** {여부}되었습니다."))
        await 유저.send(view=ui.LayoutView().add_item(dm_con))
    except:
        pass

@bot.tree.command(name="블랙리스트", description="유저를 블랙리스트에 추가/해제")
@discord.app_commands.describe(유저="블랙 관리할 유저", 여부="차단 또는 해제 선택")
@discord.app_commands.choices(여부=[
    discord.app_commands.Choice(name="차단", value=1),
    discord.app_commands.Choice(name="해제", value=0)
])
async def black_manage(interaction: discord.Interaction, 유저: discord.Member, 여부: int):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("관리자 권한이 필요합니다", ephemeral=True)

    u_id = str(유저.id)
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()
    
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
    cur.execute("UPDATE users SET is_blacked = ? WHERE user_id = ?", (여부, u_id))
    
    conn.commit()
    conn.close()

    status_text = "차단" if 여부 == 1 else "해제"
    color = 0xff0000 if 여부 == 1 else 0x00ff00
    
    container = ui.Container(ui.TextDisplay(f"## 블랙리스트 {status_text}"), accent_color=color)
    container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(f"대상: {유저.mention}\n해당 유저가 블랙리스트에서 {status_text}되었습니다"))
    
    await interaction.response.send_message(view=ui.LayoutView().add_item(container))

@bot.tree.command(name="유저정보", description="유저의 상세 정보와 거래 내역을 조회합니다")
@app_commands.describe(유저="정보를 조회할 유저", 파일="텍스트 파일로 내보내기 여부")
@app_commands.choices(파일=[
    app_commands.Choice(name="파일로 받기", value="yes"),
    app_commands.Choice(name="파일 받지 않기", value="no")
])
async def user_info_manage(interaction: discord.Interaction, 유저: discord.Member, 파일: str = "no"):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)

    u_id = str(유저.id)
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()

    cur.execute("SELECT money, total_spent, is_blacked FROM users WHERE user_id = ?", (u_id,))
    user_row = cur.fetchone()
    
    cur.execute("SELECT amount, date, method FROM charge_logs WHERE user_id = ? ORDER BY date DESC LIMIT 10", (u_id,))
    logs = cur.fetchall()
    conn.close()

    if not user_row:
        return await interaction.response.send_message("해당 유저의 데이터가 존재하지 않습니다.", ephemeral=True)

    money, total_spent, is_blacked = user_row
    black_status = "O" if is_blacked == 1 else "X"

    if 파일 == "yes":
        report_text = f"=== 유저 정보 보고서 ===\n"
        report_text += f"대상 유저: {유저.display_name} ({유저.id})\n"
        report_text += f"보유 잔액: {money:,}원\n"
        report_text += f"누적 충전: {total_spent:,}원\n"
        report_text += f"블랙 여부: {black_status}\n\n"
        report_text += "--- 최근 거래 내역 (최대 10개) ---\n"
        
        if logs:
            for l in logs:
                report_text += f"[{l[1]}] {l[2]}: {l[0]:,}원\n"
        else:
            report_text += "거래 내역이 없습니다.\n"

        file = discord.File(io.BytesIO(report_text.encode('utf-8')), filename=f"user_info_{u_id}.txt")
        return await interaction.response.send_message(f"```{유저.display_name}님의 상세 정보 파일입니다```", file=file, ephemeral=True)

    container = ui.Container(ui.TextDisplay(f"## {유저.display_name}님의 정보"), accent_color=0xffffff)
    container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(f"보유 잔액: {money:,}원\n누적 충전: {total_spent:,}원\n블랙 여부: {black_status}"))
    container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    select_options = [
        discord.SelectOption(label="최근 거래 내역 확인", value="view_logs")
    ]
    
    select_menu = ui.Select(placeholder="확인할 항목을 선택하세요", options=select_options)

    async def select_callback(it: discord.Interaction):
        if select_menu.values[0] == "view_logs":
            log_con = ui.Container(ui.TextDisplay(f"## {유저.display_name}님의 최근 내역"), accent_color=0xffffff)
            log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            if logs:
                log_text = "\n".join([f"• {l[1]} | {l[2]} | {l[0]:,}원" for l in logs])
                log_con.add_item(ui.TextDisplay(log_text))
            else:
                log_con.add_item(ui.TextDisplay("거래 내역이 존재하지 않습니다"))
            
            await it.response.send_message(view=ui.LayoutView().add_item(log_con), ephemeral=True)

    select_menu.callback = select_callback
    container.add_item(ui.ActionRow(select_menu))
    
    await interaction.response.send_message(view=ui.LayoutView().add_item(container), ephemeral=True)

@bot.tree.command(name="상품설정", description="자판기 상품 정보를 관리합니다")
async def product_setting(it: discord.Interaction):
    if not it.user.guild_permissions.administrator:
        return await it.response.send_message("권한이 없습니다", ephemeral=True)
    await it.response.send_message(view=ProductAdminLayout(), ephemeral=True)

@bot.tree.command(name="업데이트_공지", description="설정된 웹훅으로 컨테이너 공지를 전송합니다")
@app_commands.describe(내용="공지할 내용을 입력하세요")
async def update_notice_container(it: discord.Interaction, 내용: str):
    if not it.user.guild_permissions.administrator:
        return await it.response.send_message("**관리자 권한이 필요합니다**", ephemeral=True)

    target_url = WEBHOOK_CONFIG.get("업데이트")
    if not target_url or "http" not in target_url:
        return await it.response.send_message("**웹훅 URL이 설정되지 않았습니다**", ephemeral=True)

    await it.response.defer(ephemeral=True)

    notice_con = ui.Container(ui.TextDisplay("## 업데이트 안내"), accent_color=0xffffff)
    notice_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    processed_content = 내용.replace("\\n", "\n")
    notice_con.add_item(ui.TextDisplay(f"{processed_content}"))
    
    notice_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    notice_con.add_item(ui.TextDisplay(f"`마지막 업데이트 시간: {time.strftime('%Y-%m-%d %H:%M')}`"))

    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(target_url, session=session)
        try:
            view = ui.LayoutView().add_item(notice_con)
            
            await webhook.send(
                view=view,
                username="Service Update",
                avatar_url=bot.user.avatar.url if bot.user.avatar else None
            )
            await it.followup.send("**공지가 웹훅으로 전송되었습니다**", ephemeral=True)
        except Exception as e:
            await it.followup.send(f"**전송 실패: {e}**", ephemeral=True)

def run_web():
    uvicorn.run(app, host="127.0.0.1", port=8080)

if __name__ == "__main__":
    api_thread = Thread(target=run_fastapi, daemon=True)
    api_thread.start()

    web_p = multiprocessing.Process(target=run_web)
    web_p.start()
