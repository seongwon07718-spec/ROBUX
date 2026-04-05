async def info_callback(self, it: discord.Interaction):

    u_id = str(it.user.id)
    money = 0
    used_money = 0
    discount = 0

    try:
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()

            # 잔액
            cur.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
            row = cur.fetchone()
            if row:
                money = row[0]

            # 누적 구매 금액 (completed 상태만)
            cur.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM orders WHERE user_id = ? AND status = 'completed'",
                (u_id,)
            )
            used_row = cur.fetchone()
            if used_row:
                used_money = used_row[0]

            # 할인율
            cur.execute("SELECT value FROM config WHERE key = ?", (f"discount_{u_id}",))
            disc_row = cur.fetchone()
            if disc_row:
                discount = int(disc_row[0])

    except:
        pass

    roles = [role.name for role in it.user.roles if role.name != "@everyone"]
    role_grade = roles[-1] if roles else "Guest"

    con = ui.Container()
    con.accent_color = 0x5865F2

    con.add_item(ui.TextDisplay(
        f"### <:emoji_19:1487441741484392498>  {it.user.display_name} 님의 정보"
    ))

    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

    con.add_item(ui.TextDisplay(
        f"-# - **보유 잔액:** `{money:,}원`\n"
        f"-# - **사용 금액:** `{used_money:,}원`\n"
        f"-# - **역할 등급:** `{role_grade}`\n"
        f"-# - **할인 혜택:** `{discount}%`"
    ))

    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

    select = ui.Select(
        placeholder="조회할 내역 선택해주세요",
        options=[
            discord.SelectOption(label="최근 충전 내역", value="charge"),
            discord.SelectOption(label="최근 구매 내역", value="purchase")
        ]
    )

    async def res_cb(i: discord.Interaction):

        selected = select.values[0]

        try:
            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()

                if selected == "charge":
                    cur.execute(
                        "SELECT amount, created_at FROM orders WHERE user_id = ? AND status = 'charge' ORDER BY created_at DESC LIMIT 5",
                        (u_id,)
                    )
                    rows = cur.fetchall()

                    if not rows:
                        await i.response.send_message(
                            view=await get_container_view(
                                "📋 최근 충전 내역",
                                "-# - 충전 내역이 없습니다",
                                0x5865F2
                            ),
                            ephemeral=True
                        )
                        return

                    text = "### 📋 최근 충전 내역\n"
                    for row in rows:
                        text += f"-# - `{row[1][:10]}` | **+{row[0]:,}원**\n"

                else:
                    cur.execute(
                        "SELECT order_id, amount, robux, created_at FROM orders WHERE user_id = ? AND status = 'completed' ORDER BY created_at DESC LIMIT 5",
                        (u_id,)
                    )
                    rows = cur.fetchall()

                    if not rows:
                        await i.response.send_message(
                            view=await get_container_view(
                                "🛒 최근 구매 내역",
                                "-# - 구매 내역이 없습니다",
                                0x5865F2
                            ),
                            ephemeral=True
                        )
                        return

                    text = "### 🛒 최근 구매 내역\n"
                    for row in rows:
                        text += f"-# - `{row[3][:10]}` | **{row[1]:,}원** | `{row[0]}`\n"

        except:
            await i.response.send_message(
                view=await get_container_view("❌ 오류", "-# - 내역을 불러올 수 없습니다", 0xED4245),
                ephemeral=True
            )
            return

        result_view = ui.LayoutView(timeout=60)
        result_con = ui.Container()
        result_con.accent_color = 0x5865F2
        result_con.add_item(ui.TextDisplay(text))
        result_view.add_item(result_con)

        await i.response.send_message(view=result_view, ephemeral=True)

    select.callback = res_cb

    con.add_item(ui.ActionRow(select))

    await it.response.send_message(
        view=ui.LayoutView(timeout=60).add_item(con),
        ephemeral=True
    )


@bot.tree.command(name="할인", description="유저 할인율을 설정합니다")
@app_commands.describe(
    유저="대상 디스코드 유저",
    할인율="할인율 (0~100)"
)
async def 할인(it: discord.Interaction, 유저: discord.Member, 할인율: int):

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

    if 할인율 < 0 or 할인율 > 100:
        await it.response.send_message(
            view=await get_container_view(
                "<:downvote:1489930277450158080>  오류",
                "-# - 할인율은 0~100 사이여야 합니다",
                0xED4245
            ),
            ephemeral=True
        )
        return

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (f"discount_{유저.id}", str(할인율))
        )
        conn.commit()

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = 0x57F287

    con.add_item(ui.TextDisplay(
        f"### ✅ 할인율 설정 완료\n"
        f"-# - **대상 유저**: {유저.mention}\n"
        f"-# - **할인율**: {할인율}%\n"
        f"-# - **처리자**: {it.user.mention}"
    ))

    view.add_item(con)

    await it.response.send_message(view=view, ephemeral=True)
