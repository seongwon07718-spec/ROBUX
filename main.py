@bot.tree.command(name="미완료주문", description="pending 상태 주문 목록을 확인합니다")
async def 미완료주문(it: discord.Interaction):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT order_id, user_id, amount, created_at FROM orders WHERE status = 'pending' ORDER BY created_at DESC"
        )
        rows = cur.fetchall()

    if not rows:
        await it.response.send_message(
            view=await get_container_view("<:upvote:1489930275868770305>  미완료 없음", "-# - pending 상태 주문이 없습니다", 0x57F287),
            ephemeral=True
        )
        return

    text = (
        f"### <:acy2:1489883409001091142>  미완료 주문 목록\n"
        f"-# - 총 {len(rows)}건\n"
    )

    for row in rows:
        order_id, user_id, amount, created_at = row
        try:
            member = await it.guild.fetch_member(int(user_id))
            name = member.display_name
        except Exception:
            name = f"{user_id}"
        text += f"-# - `{created_at[:10]}` | **{amount:,}원** | {name} | `{order_id}`\n"

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = 0xFEE75C
    con.add_item(ui.TextDisplay(text))
    view.add_item(con)
    await it.response.send_message(view=view, ephemeral=True)


@bot.tree.command(name="블랙리스트", description="특정 유저의 구매를 차단하거나 해제합니다")
@app_commands.describe(유저="차단/해제할 디스코드 유저")
async def 블랙리스트(it: discord.Interaction, 유저: discord.Member):

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
        row = cur.fetchone()

    if not row or str(it.user.id) != row[0]:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  권한 없음", "-# - 관리자만 사용할 수 있는 명령어입니다", 0xED4245),
            ephemeral=True
        )
        return

    key = f"blacklist_{유저.id}"

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = ?", (key,))
        current = cur.fetchone()

    is_blocked = current and current[0] == "1"

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, "0" if is_blocked else "1")
        )
        conn.commit()

    if is_blocked:
        view = ui.LayoutView(timeout=None)
        con = ui.Container()
        con.accent_color = 0x57F287
        con.add_item(ui.TextDisplay(
            f"### <:upvote:1489930275868770305>  차단 해제\n"
            f"-# - **대상 유저**: {유저.mention}\n"
            f"-# - 구매가 가능한 상태로 변경되었습니다\n"
            f"-# - **처리자**: {it.user.mention}"
        ))
        view.add_item(con)
    else:
        view = ui.LayoutView(timeout=None)
        con = ui.Container()
        con.accent_color = 0xED4245
        con.add_item(ui.TextDisplay(
            f"### <:downvote:1489930277450158080>  차단 완료\n"
            f"-# - **대상 유저**: {유저.mention}\n"
            f"-# - 구매가 불가한 상태로 변경되었습니다\n"
            f"-# - **처리자**: {it.user.mention}"
        ))
        view.add_item(con)

    await it.response.send_message(view=view, ephemeral=True)

        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = ?", (f"blacklist_{self.user_id}",))
            bl = cur.fetchone()

        if bl and bl[0] == "1":
            await it.response.edit_message(
                view=await get_container_view(
                    "<:downvote:1489930277450158080>  구매 불가",
                    "-# - 구매가 제한된 유저입니다",
                    0xED4245
                )
            )
            return
