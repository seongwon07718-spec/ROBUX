@bot.tree.command(name="잔액조회", description="특정 유저의 잔액을 확인합니다")
@app_commands.describe(유저="조회할 디스코드 유저")
async def 잔액조회(it: discord.Interaction, 유저: discord.Member):

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

        cur.execute("SELECT balance FROM users WHERE user_id = ?", (str(유저.id),))
        row = cur.fetchone()
        balance = row[0] if row else 0

        cur.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM orders WHERE user_id = ? AND status = 'completed'",
            (str(유저.id),)
        )
        used = cur.fetchone()[0]

        cur.execute("SELECT value FROM config WHERE key = ?", (f"discount_{유저.id}",))
        d = cur.fetchone()
        discount = int(d[0]) if d else 0

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = 0x5865F2
    con.add_item(ui.TextDisplay(
        f"### <:acy2:1489883409001091142>  {유저.display_name} 잔액 조회\n"
        f"-# - **보유 잔액**: `{balance:,}원`\n"
        f"-# - **누적 사용**: `{used:,}원`\n"
        f"-# - **할인율**: `{discount}%`\n"
        f"-# - **조회자**: {it.user.mention}"
    ))
    view.add_item(con)
    await it.response.send_message(view=view, ephemeral=True)


@bot.tree.command(name="주문조회", description="특정 유저의 전체 주문 내역을 확인합니다")
@app_commands.describe(유저="조회할 디스코드 유저", 페이지="페이지 번호 (기본: 1)")
async def 주문조회(it: discord.Interaction, 유저: discord.Member, 페이지: int = 1):

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

    limit = 10
    offset = (페이지 - 1) * limit

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()

        cur.execute(
            "SELECT order_id, amount, status, created_at FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (str(유저.id), limit, offset)
        )
        rows = cur.fetchall()

        cur.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?", (str(유저.id),))
        total = cur.fetchone()[0]

    if not rows:
        await it.response.send_message(
            view=await get_container_view("<:acy2:1489883409001091142>  주문 없음", "-# - 주문 내역이 없습니다", 0x5865F2),
            ephemeral=True
        )
        return

    total_pages = (total + limit - 1) // limit
    status_map = {"completed": "<:upvote:1489930275868770305> 완료", "failed": "<:downvote:1489930277450158080> 실패", "pending": "대기", "charge": "충전"}

    text = (
        f"### <:acy2:1489883409001091142>  {유저.display_name} 주문 내역\n"
        f"-# - 총 {total}건 | {페이지}/{total_pages} 페이지\n"
    )
    for row in rows:
        status_text = status_map.get(row[2], row[2])
        text += f"-# - `{row[3][:10]}` | {status_text} | **{row[1]:,}원** | `{row[0]}`\n"

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = 0x5865F2
    con.add_item(ui.TextDisplay(text))
    view.add_item(con)
    await it.response.send_message(view=view, ephemeral=True)


@bot.tree.command(name="전체통계", description="전체 서비스 통계를 확인합니다")
async def 전체통계(it: discord.Interaction):

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

        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'charge'")
        total_charge = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'completed'")
        total_sales = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
        total_orders = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'failed'")
        total_failed = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'completed' AND DATE(created_at) = DATE('now')")
        today_sales = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'charge' AND DATE(created_at) = DATE('now')")
        today_charge = cur.fetchone()[0]

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = 0x5865F2
    con.add_item(ui.TextDisplay(
        f"### <:acy2:1489883409001091142>  전체 통계\n"
        f"-# ─────────────────────\n"
        f"-# - **총 유저 수**: {total_users:,}명\n"
        f"-# ─────────────────────\n"
        f"-# - **총 충전 금액**: {total_charge:,}원\n"
        f"-# - **총 매출**: {total_sales:,}원\n"
        f"-# - **총 주문 수**: {total_orders:,}건\n"
        f"-# - **총 실패 수**: {total_failed:,}건\n"
        f"-# ─────────────────────\n"
        f"-# - **오늘 충전**: {today_charge:,}원\n"
        f"-# - **오늘 매출**: {today_sales:,}원\n"
        f"-# ─────────────────────"
    ))
    view.add_item(con)
    await it.response.send_message(view=view, ephemeral=True)


@bot.tree.command(name="쿠키상태", description="현재 로블록스 쿠키 상태를 확인합니다")
async def 쿠키상태(it: discord.Interaction):

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

    await it.response.defer(ephemeral=True)

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        cookie_row = cur.fetchone()

    cookie = cookie_row[0] if cookie_row else None
    is_success, result = get_roblox_data(cookie)

    if is_success:
        view = await get_container_view(
            "<:upvote:1489930275868770305>  쿠키 정상",
            f"-# - 상태: 정상\n-# - 보유 로벅스: {result:,} R$",
            0x57F287
        )
    else:
        view = await get_container_view(
            "<:downvote:1489930277450158080>  쿠키 오류",
            f"-# - 상태: 만료 또는 오류\n-# - 사유: {result}",
            0xED4245
        )

    await it.followup.send(view=view, ephemeral=True)


@bot.tree.command(name="주문취소", description="특정 주문을 취소하고 잔액을 복구합니다")
@app_commands.describe(거래id="취소할 거래 ID")
async def 주문취소(it: discord.Interaction, 거래id: str):

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
        cur.execute("SELECT user_id, amount, status FROM orders WHERE order_id = ?", (거래id,))
        order = cur.fetchone()

    if not order:
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  오류", "-# - 해당 거래 ID를 찾을 수 없습니다", 0xED4245),
            ephemeral=True
        )
        return

    user_id, amount, status = order

    if status in ("failed", "charge"):
        await it.response.send_message(
            view=await get_container_view("<:downvote:1489930277450158080>  취소 불가", f"-# - 이미 {status} 상태인 주문입니다", 0xED4245),
            ephemeral=True
        )
        return

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE orders SET status = 'failed' WHERE order_id = ?", (거래id,))
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()

    try:
        member = await it.guild.fetch_member(int(user_id))
        mention = member.mention
    except Exception:
        mention = f"`{user_id}`"

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = 0x57F287
    con.add_item(ui.TextDisplay(
        f"### <:upvote:1489930275868770305>  주문 취소 완료\n"
        f"-# - **거래ID**: `{거래id}`\n"
        f"-# - **대상 유저**: {mention}\n"
        f"-# - **복구 금액**: {amount:,}원\n"
        f"-# - **처리자**: {it.user.mention}"
    ))
    view.add_item(con)
    await it.response.send_message(view=view, ephemeral=True)


@bot.tree.command(name="점검모드", description="구매를 일시 중단하거나 재개합니다")
async def 점검모드(it: discord.Interaction):

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
        cur.execute("SELECT value FROM config WHERE key = 'maintenance'")
        current = cur.fetchone()

    is_maintenance = current and current[0] == "1"

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES ('maintenance', ?)",
            ("0" if is_maintenance else "1")
        )
        conn.commit()

    if is_maintenance:
        view = await get_container_view(
            "<:upvote:1489930275868770305>  점검 해제",
            "-# - 구매가 재개되었습니다",
            0x57F287
        )
    else:
        view = await get_container_view(
            "<:downvote:1489930277450158080>  점검 모드",
            "-# - 구매가 일시 중단되었습니다",
            0xED4245
        )

    await it.response.send_message(view=view, ephemeral=True)


@bot.tree.command(name="유저목록", description="전체 유저 잔액 순위를 확인합니다")
@app_commands.describe(페이지="페이지 번호 (기본: 1)")
async def 유저목록(it: discord.Interaction, 페이지: int = 1):

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

    limit = 10
    offset = (페이지 - 1) * limit

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]

        cur.execute(
            "SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = cur.fetchall()

    if not rows:
        await it.response.send_message(
            view=await get_container_view("<:acy2:1489883409001091142>  유저 없음", "-# - 등록된 유저가 없습니다", 0x5865F2),
            ephemeral=True
        )
        return

    total_pages = (total + limit - 1) // limit
    text = (
        f"### <:acy2:1489883409001091142>  유저 잔액 순위\n"
        f"-# - 총 {total}명 | {페이지}/{total_pages} 페이지\n"
    )

    for i, (user_id, balance) in enumerate(rows):
        rank = offset + i + 1
        try:
            member = await it.guild.fetch_member(int(user_id))
            name = member.display_name
        except Exception:
            name = f"{user_id}"
        text += f"-# - **{rank}위** | {name} | `{balance:,}원`\n"

    view = ui.LayoutView(timeout=None)
    con = ui.Container()
    con.accent_color = 0x5865F2
    con.add_item(ui.TextDisplay(text))
    view.add_item(con)
    await it.response.send_message(view=view, ephemeral=True)
