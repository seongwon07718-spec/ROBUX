import asyncio

@bot.tree.command(name="인증유저", description="인증 완료된 유저 수를 확인합니다")
async def total_users(it: discord.Interaction):
    # 1. 처음 보여줄 '조회 중' 컨테이너 설정
    loading_con = ui.Container()
    loading_con.accent_color = 0xffffff
    loading_con.add_item(ui.TextDisplay("## 🔍 데이터베이스 조회 중"))
    loading_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    loading_con.add_item(ui.TextDisplay("서버에서 인증된 유저 정보를 불러오고 있습니다\\n잠시만 기다려 주세요"))
    
    loading_view = ui.LayoutView().add_item(loading_con)
    
    # 먼저 '조회 중' 메시지 전송 (나에게만 보이게)
    await it.response.send_message(view=loading_view, ephemeral=True)

    # 2. 3초 대기 (조회하는 느낌 연출)
    await asyncio.sleep(3)

    # 3. 실제 DB 데이터 가져오기
    conn = sqlite3.connect('restore_user.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM users")
    user_count = cursor.fetchone()[0]
    conn.close()

    # 4. 결과 출력용 컨테이너 설정
    verify_con = ui.Container()
    verify_con.accent_color = 0xffffff 
    
    verify_con.add_item(ui.TextDisplay("## ✅ 인증 유저 통계"))
    verify_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    # 강조를 위해 인원수 부분을 코드 블럭 처리했습니다
    verify_con.add_item(ui.TextDisplay(f"현재 인증 완료된 유저수\\n**` {user_count}명 `**"))
    verify_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    verify_con.add_item(ui.TextDisplay("-# DB는 365일 안전하게 보관됩니다"))
    
    final_view = ui.LayoutView().add_item(verify_con)

    # 5. 기존에 보냈던 메시지를 결과 컨테이너로 수정
    await it.edit_original_response(view=final_view)
