    async def on_submit(self, it: discord.Interaction):
        # ... 기존 준비 코드 ...

        # 입금 대기 시작 전 로그 먼저 전송
        log_msg = None
        try:
            log_view = ui.LayoutView(timeout=None)
            log_con = ui.Container()
            log_con.accent_color = 0xFEE75C
            log_con.add_item(ui.TextDisplay(
                f"### <:acy2:1489883409001091142>  충전 신청\n"
                f"-# - **유저**: {it.user.mention}\n"
                f"-# - **입금자명**: `{self.depositor.value}`\n"
                f"-# - **충전 금액**: {int(self.amount.value):,}원\n"
                f"-# - **상태**: 입금 대기 중"
            ))

            approve_btn = ui.Button(
                label="승인",
                style=discord.ButtonStyle.gray,
                emoji="<:upvote:1489930275868770305>",
                custom_id=f"approve_{it.user.id}_{self.amount.value}"
            )
            reject_btn = ui.Button(
                label="거부",
                style=discord.ButtonStyle.gray,
                emoji="<:downvote:1489930277450158080>",
                custom_id=f"reject_{it.user.id}_{self.amount.value}"
            )

            async def on_approve(inter: discord.Interaction):
                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?",
                        (str(it.user.id), int(self.amount.value), int(self.amount.value))
                    )
                    cur.execute(
                        "INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'charge')",
                        ("".join(random.choices(string.ascii_uppercase + string.digits, k=10)), str(it.user.id), int(self.amount.value), 0)
                    )
                    conn.commit()

                # 버튼 비활성화
                done_view = ui.LayoutView(timeout=None)
                done_con = ui.Container()
                done_con.accent_color = 0x57F287
                done_con.add_item(ui.TextDisplay(
                    f"### <:acy2:1489883409001091142>  충전 승인\n"
                    f"-# - **유저**: {it.user.mention}\n"
                    f"-# - **입금자명**: `{self.depositor.value}`\n"
                    f"-# - **충전 금액**: {int(self.amount.value):,}원\n"
                    f"-# - **상태**: 승인됨\n"
                    f"-# - **처리자**: {inter.user.mention}"
                ))
                done_btn1 = ui.Button(label="승인됨", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>", disabled=True)
                done_btn2 = ui.Button(label="거부", style=discord.ButtonStyle.gray, emoji="<:downvote:1489930277450158080>", disabled=True)
                done_con.add_item(ui.ActionRow(done_btn1, done_btn2))
                done_view.add_item(done_con)
                await inter.response.edit_message(view=done_view)

                try:
                    await it.user.send(f"<:acy2:1489883409001091142> **충전이 승인되었습니다**\n- 충전 금액: {int(self.amount.value):,}원")
                except Exception:
                    pass

            async def on_reject(inter: discord.Interaction):
                done_view = ui.LayoutView(timeout=None)
                done_con = ui.Container()
                done_con.accent_color = 0xED4245
                done_con.add_item(ui.TextDisplay(
                    f"### <:downvote:1489930277450158080>  충전 거부\n"
                    f"-# - **유저**: {it.user.mention}\n"
                    f"-# - **입금자명**: `{self.depositor.value}`\n"
                    f"-# - **충전 금액**: {int(self.amount.value):,}원\n"
                    f"-# - **상태**: 거부됨\n"
                    f"-# - **처리자**: {inter.user.mention}"
                ))
                done_btn1 = ui.Button(label="승인", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>", disabled=True)
                done_btn2 = ui.Button(label="거부됨", style=discord.ButtonStyle.gray, emoji="<:downvote:1489930277450158080>", disabled=True)
                done_con.add_item(ui.ActionRow(done_btn1, done_btn2))
                done_view.add_item(done_con)
                await inter.response.edit_message(view=done_view)

                try:
                    await it.user.send(f"<:downvote:1489930277450158080> **충전이 거부되었습니다**\n- 충전 금액: {int(self.amount.value):,}원")
                except Exception:
                    pass

            approve_btn.callback = on_approve
            reject_btn.callback = on_reject
            log_con.add_item(ui.ActionRow(approve_btn, reject_btn))
            log_view.add_item(log_con)

            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT value FROM config WHERE key = 'charge_log'")
                row = cur.fetchone()

            if row:
                channel = bot.get_channel(int(row[0]))
                if channel:
                    log_msg = await channel.send(view=log_view)

        except Exception as e:
            print(f"[충전로그 실패] {e}")

        # 기존 입금 대기 로직
        key = f"{self.depositor.value}_{self.amount.value}"
        success = False
        for _ in range(60):
            if pending_deposits.get(key):
                success = True
                del pending_deposits[key]
                break
            await asyncio.sleep(5)

        # 자동충전 성공시 로그 버튼 비활성화
        if success:
            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?",
                    (str(it.user.id), int(self.amount.value), int(self.amount.value))
                )
                cur.execute(
                    "INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'charge')",
                    ("".join(random.choices(string.ascii_uppercase + string.digits, k=10)), str(it.user.id), int(self.amount.value), 0)
                )
                conn.commit()

            # 로그 메시지 버튼 비활성화
            if log_msg:
                try:
                    done_view = ui.LayoutView(timeout=None)
                    done_con = ui.Container()
                    done_con.accent_color = 0x57F287
                    done_con.add_item(ui.TextDisplay(
                        f"### <:acy2:1489883409001091142>  충전 로그\n"
                        f"-# - **유저**: {it.user.mention}\n"
                        f"-# - **입금자명**: `{self.depositor.value}`\n"
                        f"-# - **충전 금액**: {int(self.amount.value):,}원\n"
                        f"-# - **상태**: 자동 승인됨"
                    ))
                    done_btn1 = ui.Button(label="승인됨", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>", disabled=True)
                    done_btn2 = ui.Button(label="거부", style=discord.ButtonStyle.gray, emoji="<:downvote:1489930277450158080>", disabled=True)
                    done_con.add_item(ui.ActionRow(done_btn1, done_btn2))
                    done_view.add_item(done_con)
                    await log_msg.edit(view=done_view)
                except Exception as e:
                    print(f"[로그 업데이트 실패] {e}")
