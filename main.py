            # 구매 로그 채널
            try:
                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT value FROM config WHERE key = 'purchase_log'")
                    log_row = cur.fetchone()

                if log_row:
                    log_channel = bot.get_channel(int(log_row[0]))
                    if log_channel:
                        card_image = res.get("card_image")
                        if card_image and os.path.exists(card_image):
                            await log_channel.send(
                                file=discord.File(card_image, filename="card.png")
                            )
                        else:
                            await log_channel.send(
                                content=f"<:acy2:1489883409001091142> **{it.user.mention} / {self.pass_info.get('price', 0):,}로벅스 구매 감사합니다**"
                            )
            except Exception as e:
                print(f"[로그 실패] {e}")
