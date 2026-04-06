    @tasks.loop(minutes=2.0)
    async def stock_updater(self):

        # 재고 변화 감지
        try:
            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
                cookie_row = cur.fetchone()
                cur.execute("SELECT value FROM config WHERE key = 'last_robux'")
                last_row = cur.fetchone()
                cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
                admin_row = cur.fetchone()
                cur.execute("SELECT value FROM config WHERE key = 'cookie_alert_sent'")
                alert_row = cur.fetchone()

            cookie = cookie_row[0] if cookie_row else None
            is_valid, current_robux = get_roblox_data(cookie)
            last_robux = int(last_row[0]) if last_row else 0

            if is_valid:
                # 쿠키 알림 초기화
                if alert_row and alert_row[0] == "1":
                    with sqlite3.connect(DATABASE) as conn:
                        cur = conn.cursor()
                        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('cookie_alert_sent', '0')")
                        conn.commit()

                # ✅ 재고 증가 감지
                if current_robux > last_robux and last_robux > 0:
                    try:
                        with sqlite3.connect(DATABASE) as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT value FROM config WHERE key = 'stock_log'")
                            stock_row = cur.fetchone()

                        if stock_row:
                            stock_channel = self.get_channel(int(stock_row[0]))
                            if stock_channel:
                                # 로벅스 이미지 다운로드
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
                                            f"<:acy2:1489883409001091142> **{current_robux:,} 로벅스 재고 채웠습니다**\n"
                                            f"- 원래 수량: {last_robux:,} R$\n"
                                            f"- 지금 수량: {current_robux:,} R$"
                                        ),
                                        file=img_file
                                    )
                                else:
                                    await stock_channel.send(
                                        content=(
                                            f"<:acy2:1489883409001091142> **{current_robux:,} 로벅스 재고 채웠습니다**\n"
                                            f"- 원래 수량: {last_robux:,} R$\n"
                                            f"- 지금 수량: {current_robux:,} R$"
                                        )
                                    )
                    except Exception as e:
                        print(f"[재고로그 실패] {e}")

                # 현재 재고 저장
                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT OR REPLACE INTO config (key, value) VALUES ('last_robux', ?)",
                        (str(current_robux),)
                    )
                    conn.commit()

            else:
                # 쿠키 만료 감지
                if not alert_row or alert_row[0] == "0":
                    if admin_row:
                        try:
                            admin = await self.fetch_user(int(admin_row[0]))
                            if admin:
                                await admin.send(
                                    f"<:downvote:1489930277450158080> **쿠키 만료 감지**\n"
                                    f"- 사유: {current_robux}\n"
                                    f"- `/쿠키등록` 으로 쿠키를 갱신해주세요"
                                )
                        except Exception:
                            pass
                    with sqlite3.connect(DATABASE) as conn:
                        cur = conn.cursor()
                        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('cookie_alert_sent', '1')")
                        conn.commit()

        except Exception as e:
            print(f"[재고감지 실패] {e}")

        # 자판기 업데이트
        if not self.vending_msg_info:
            return
        for channel_id, msg_id in list(self.vending_msg_info.items()):
            try:
                channel = self.get_channel(channel_id)
                if not channel:
                    continue
                msg = await channel.fetch_message(msg_id)
                view = RobuxVending(self)
                con = await view.build_main_menu()
                await msg.edit(view=ui.LayoutView(timeout=None).add_item(con))
            except Exception as e:
                print(f"Update Error: {e}")
