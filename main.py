@bot.tree.command(name="유저복구", description="인증했던 유저들을 서버에 복구하기")
@app_commands.checks.has_permissions(administrator=True)
async def restore(it: discord.Interaction):
    # 1. 초기 진행 중 컨테이너
    process_con = ui.Container()
    process_con.accent_color = 0xffffff
    process_con.add_item(ui.TextDisplay("## 🔄 유저 복구 프로세스 가동"))
    process_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    process_con.add_item(ui.TextDisplay("데이터베이스에서 유저 정보를 조회하여\\n서버로의 복구 작업을 시작합니다"))
    
    process_view = ui.LayoutView().add_item(process_con)
    await it.response.send_message(view=process_view, ephemeral=True)
    
    # DB 조회
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id, access_token FROM users WHERE server_id = ?", (str(it.guild_id),))
    all_users = cur.fetchall()
    conn.close()

    if not all_users:
        # 데이터 없을 때의 컨테이너
        error_con = ui.Container()
        error_con.accent_color = 0xffffff
        error_con.add_item(ui.TextDisplay("## ❌ 복구 불가"))
        error_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        error_con.add_item(ui.TextDisplay("복구할 유저 데이터가 존재하지 않습니다\\n인증된 유저가 있는지 먼저 확인해 주세요"))
        return await it.edit_original_response(view=ui.LayoutView().add_item(error_con))

    success, fail = 0, 0
    async with aiohttp.ClientSession() as session:
        for u_id, token in all_users:
            url = f"https://discord.com/api/v10/guilds/{it.guild_id}/members/{u_id}"
            headers = {
                "Authorization": f"Bot {TOKEN}",
                "Content-Type": "application/json"
            }
            # 데이터 복구 요청
            async with session.put(url, headers=headers, json={"access_token": token}) as resp:
                if resp.status in [201, 204]:
                    success += 1
                else:
                    fail += 1
                # 디스코드 API 레이트 리밋 방지를 위한 짧은 대기
                await asyncio.sleep(0.5)

    # 2. 복구 완료 최종 결과 컨테이너
    result_con = ui.Container()
    result_con.accent_color = 0xffffff
    result_con.add_item(ui.TextDisplay("## ✅ 복구 작업 완료"))
    result_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    # 성공/실패 인원 가독성 좋게 표시
    result_con.add_item(ui.TextDisplay(
        f"**작업 결과 보고**\\n"
        f"```diff\\n"
        f"+ 성공: {success}명\\n"
        f"- 실패: {fail}명\\n"
        f"```"
    ))
    
    result_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    result_con.add_item(ui.TextDisplay("-# RESTORE PROTOCOL SYSTEM VERIFIED"))
    
    final_view = ui.LayoutView().add_item(result_con)
    
    # 기존 메시지를 결과 컨테이너로 수정
    await it.edit_original_response(view=final_view)
