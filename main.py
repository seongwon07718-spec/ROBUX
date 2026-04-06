            screenshot = res.get("screenshot")

            try:
                user = it.user
                if screenshot and os.path.exists(screenshot):
                    await user.send(
                        content=f"<:acy2:1489883409001091142> **@{user.name} 구매 완료 - 거래ID: `{res['order_id']}`**",
                        file=discord.File(screenshot, filename="success.png")
                    )
                else:
                    await user.send(content=f"<:acy2:1489883409001091142> **@{user.name} 구매 완료 - 거래ID: `{res['order_id']}`**\n- 게임패스: {self.pass_info.get('name', '알 수 없음')}\n- 가격: {self.pass_info.get('price', 0):,}로벅스\n- 결제금액: {self.money:,}원\n- 처리시간: {elapsed}초")
            except Exception:
                pass

            try:
                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT value FROM config WHERE key = 'log_channel_id'")
                    log_row = cur.fetchone()

                if log_row:
                    log_channel = it.client.get_channel(int(log_row[0]))
                    if log_channel:
                        await log_channel.send(
                            f"<:acy2:1489883409001091142> **{it.user.mention} / {self.pass_info.get('price', 0):,}로벅스 구매 감사합니다**"
                        )
            except Exception:
                pass
