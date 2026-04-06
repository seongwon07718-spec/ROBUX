                if current_robux > last_robux and last_robux > 0:
                    try:
                        with sqlite3.connect(DATABASE) as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT value FROM config WHERE key = 'stock_log'")
                            stock_row = cur.fetchone()

                        if stock_row:
                            stock_channel = self.get_channel(int(stock_row[0]))
                            if stock_channel:
                                added = current_robux - last_robux
                                embed = discord.Embed(
                                    title=f"{added:,}로벅스 재고 입고 완료",
                                    color=0x57F287
                                )
                                embed.add_field(name="원래 재고", value=f"{last_robux:,}로벅스", inline=True)
                                embed.add_field(name="현재 재고", value=f"{current_robux:,}로벅스", inline=True)
                                await stock_channel.send(content="@everyone", embed=embed)
                    except Exception as e:
                        print(f"[재고로그 실패] {e}")
