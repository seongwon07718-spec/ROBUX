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
                                log_view = ui.LayoutView(timeout=None)
                                log_con = ui.Container()
                                log_con.accent_color = 0x57F287
                                log_con.add_item(ui.TextDisplay(
                                    f"### <:acy2:1489883409001091142>  {added:,}로벅스 재고 입고 완료\n"
                                    f"-# - **원래 재고**: {last_robux:,}로벅스\n"
                                    f"-# - **현재 재고**: {current_robux:,}로벅스"
                                ))
                                log_view.add_item(log_con)
                                await stock_channel.send(content="@everyone", view=log_view)
                    except Exception as e:
                        print(f"[재고로그 실패] {e}")
