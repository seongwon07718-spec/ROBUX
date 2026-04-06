                if current_robux > last_robux and last_robux > 0:
                    try:
                        with sqlite3.connect(DATABASE) as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT value FROM config WHERE key = 'stock_log'")
                            stock_row = cur.fetchone()

                        if stock_row:
                            stock_channel = self.get_channel(int(stock_row[0]))
                            if stock_channel:
                                import requests as req
                                import io
                                img_resp = req.get(
                                    "https://www.roblox.com/asset/?id=80950593",
                                    timeout=5
                                )
                                if img_resp.status_code == 200:
                                    img_file = discord.File(
                                        io.BytesIO(img_resp.content),
                                        filename="robux.png"
                                    )
                                    await stock_channel.send(
                                        content=(
                                            "@everyone\n"
                                            f"<:acy2:1489883409001091142> **{current_robux:,} 로벅스 재고 입고 완료**\n"
                                            f"-# - 원래 재고: {last_robux:,}로벅스\n"
                                            f"-# - 현재 재고: {current_robux:,}로벅스"
                                        ),
                                        file=img_file
                                    )
                                else:
                                    await stock_channel.send(
                                        content=(
                                            "@everyone\n"
                                            f"<:acy2:1489883409001091142> **{current_robux:,} 로벅스 재고 입고 완료**\n"
                                            f"-# - 원래 재고: {last_robux:,}로벅스\n"
                                            f"-# - 현재 재고: {current_robux:,}로벅스"
                                        )
                                    )
                    except Exception as e:
                        print(f"[재고로그 실패] {e}")
