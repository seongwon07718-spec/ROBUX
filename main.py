            if status in ("finished", "confirmed", "sending"):

                # 수수료 차감
                from main import COIN_FEE
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

                try:
                    await it.edit_original_response(
                        view=await get_container_view(
                            "<:upvote:1489930275868770305>  충전 완료",
                            f"-# - **코인**: {coin_name}\n"
                            f"-# - **결제 금액**: {krw_amount:,}원\n"
                            f"-# - **수수료**: {fee_percent}% (-{krw_amount - final_amount:,}원)\n"
                            f"-# - **실제 충전**: {final_amount:,}원\n"
                            f"-# - **주문 ID**: `{order_id}`",
                            0x57F287
                        )
                    )
                except Exception:
                    pass
