            if status in ("finished", "confirmed", "sending"):

                fee_percent = COIN_FEE.get(coin_id, 0)
                final_amount = int(krw_amount * (1 - fee_percent / 100))

                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?",
                        (str(it.user.id), final_amount, final_amount)
                    )
                    cur.execute("UPDATE orders SET status = 'charge' WHERE order_id = ?", (order_id,))
                    conn.commit()

                # ✅ 충전 로그 전송
                try:
                    log_view = ui.LayoutView(timeout=None)
                    log_con = ui.Container()
                    log_con.accent_color = 0x57F287
                    log_con.add_item(ui.TextDisplay(
                        f"### <:acy2:1489883409001091142>  코인 충전 로그\n"
                        f"-# - **유저**: {it.user.mention}\n"
                        f"-# - **코인**: {coin_name}\n"
                        f"-# - **결제 금액**: {krw_amount:,}원\n"
                        f"-# - **수수료**: {fee_percent}% (-{krw_amount - final_amount:,}원)\n"
                        f"-# - **실제 충전**: {final_amount:,}원\n"
                        f"-# - **주문 ID**: `{order_id}`\n"
                        f"-# - **상태**: 자동 승인"
                    ))
                    approve_btn = ui.Button(label="승인됨", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>", disabled=True)
                    reject_btn = ui.Button(label="거부", style=discord.ButtonStyle.gray, emoji="<:downvote:1489930277450158080>", disabled=True)
                    log_con.add_item(ui.ActionRow(approve_btn, reject_btn))
                    log_view.add_item(log_con)
                    await send_log("charge_log", log_view)
                except Exception as e:
                    print(f"[코인충전로그 실패] {e}")
