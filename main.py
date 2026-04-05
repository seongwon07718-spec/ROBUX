@bot.tree.command(name="수동충전", description="유저 잔액을 수동으로 조정합니다")
@app_commands.describe(
    유저="대상 디스코드 유저",
    금액="충전/차감할 금액",
    여부="추가 또는 차감"
)
@app_commands.choices(여부=[
    app_commands.Choice(name="추가", value="추가"),
    app_commands.Choice(name="차감", value="차감"),
])
async def 수동충전(it: discord.Interaction, 유저: discord.Member, 금액: int, 여부: app_commands.Choice[str]):

    # 관리자 확인
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view(
                "<:downvote:1489930277450158080>  권한 없음",
                "-# - 관리자만 사용할 수 있는 명령어입니다",
                0xED4245
            ),
            ephemeral=True
        )
        return

    if 금액 <= 0:
        await it.response.send_message(
            view=await get_container_view(
                "<:downvote:1489930277450158080>  오류",
                "-# - 금액은 1원 이상이어야 합니다",
                0xED4245
            ),
            ephemeral=True
        )
        return

    user_id = str(유저.id)

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()

        # 유저 없으면 생성
        cur.execute(
            "INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)",
            (user_id,)
        )

        # 현재 잔액 조회
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        current = cur.fetchone()[0]

        if 여부.value == "추가":
            new_balance = current + 금액
            cur.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (금액, user_id)
            )
            action_text = f"+{금액:,}원 추가"
            color = 0x57F287

        else:
            if current < 금액:
                await it.response.send_message(
                    view=await get_container_view(
                        "<:downvote:1489930277450158080>  잔액 부족",
                        f"-# - 현재 잔액: {current:,}원\n"
                        f"-# - 차감 금액: {금액:,}원\n"
                        f"-# - 잔액이 부족합니다",
                        0xED4245
                    ),
                    ephemeral=True
                )
                return

            new_balance = current - 금액
            cur.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (금액, user_id)
            )
            action_text = f"-{금액:,}원 차감"
            color = 0xED4245

        conn.commit()

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = color

    con.add_item(ui.TextDisplay(
        f"### ✅ 수동 충전 완료\n"
        f"-# - **대상 유저**: {유저.mention}\n"
        f"-# - **처리 내용**: {action_text}\n"
        f"-# - **이전 잔액**: {current:,}원\n"
        f"-# - **변경 후 잔액**: {new_balance:,}원\n"
        f"-# - **처리자**: {it.user.mention}"
    ))

    view.add_item(con)

    await it.response.send_message(view=view, ephemeral=True)
