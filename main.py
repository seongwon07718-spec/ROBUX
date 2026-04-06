        if res["success"]:

            # 구매 성공 컨테이너
            view = ui.LayoutView()
            con = ui.Container()
            con.accent_color = 0x5865F2
            con.add_item(ui.TextDisplay(
                f"### <:acy2:1489883409001091142>  구매 성공\n"
                f"-# - **게임패스**: {self.pass_info.get('name', '알 수 없음')}\n"
                f"-# - **가격**: {self.pass_info.get('price', 0):,}로벅스\n"
                f"-# - **결제금액**: {self.money:,}원\n"
                f"-# - **처리시간**: {elapsed}초\n"
                f"-# - **거래ID**: `{res['order_id']}`"
            ))
            view.add_item(con)
            await it.edit_original_response(view=view)

            screenshot = res.get("screenshot")

            # DM 전송
            try:
                user = it.user
                if screenshot and os.path.exists(screenshot):
                    await user.send(
                        content=f"@{user.name} 구매 완료",
                        file=discord.File(screenshot, filename="success.png")
                    )
                else:
                    await user.send(content=f"@{user.name} 구매 완료")
            except Exception:
                pass

            # 구매 로그 채널 전송
            try:
                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT value FROM config WHERE key = 'log_channel_id'")
                    log_row = cur.fetchone()

                if log_row:
                    log_channel = it.client.get_channel(int(log_row[0]))
                    if log_channel:
                        await log_channel.send(
                            f"{it.user.mention} ({self.pass_info.get('price', 0):,}로벅스) 구매 감사합니다"
                        )
            except Exception:
                pass
