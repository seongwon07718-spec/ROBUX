@bot.tree.command(name="인증유저", description="현재까지 인증 완료된 유저 수를 확인합니다")
async def total_users(it: discord.Interaction):
    # DB에서 중복을 제외한 총 유저 수 계산
    conn = sqlite3.connect('restore_user.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM users")
    user_count = cursor.fetchone()[0]
    conn.close()

    # 컨테이너(Embed) 형식으로 디자인
    embed_con = ui.Container()
    embed_con.accent_color = 0xffffff # 흰색 강조선
    
    # 상단 제목 및 아이콘
    embed_con.add_item(ui.TextDisplay("## 📊 인증 유저 통계"))
    
    # 유저 수 표시 (가독성을 위해 강조 처리)
    embed_con.add_item(ui.TextDisplay(f"현재까지 보안 인증을 완료한 유저 수는\\n총 **`{user_count}명`** 입니다"))
    
    # 꼬리말 추가
    embed_con.add_item(ui.TextDisplay("-# RESTORE PROTOCOL DATABASE SYSTEM"))
    
    # 전송 (ephemeral=True로 나에게만 보이게 설정)
    view = ui.LayoutView().add_item(embed_con)
    await it.response.send_message(view=view, ephemeral=True)
