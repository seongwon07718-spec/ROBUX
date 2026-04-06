    @tasks.loop(minutes=2.0)
    async def stock_updater(self):

        # 쿠키 만료 감지
        try:
            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
                cookie_row = cur.fetchone()
                cur.execute("SELECT value FROM config WHERE key = 'admin_id'")
                admin_row = cur.fetchone()
                cur.execute("SELECT value FROM config WHERE key = 'cookie_alert_sent'")
                alert_row = cur.fetchone()

            cookie = cookie_row[0] if cookie_row else None
            is_valid, result = get_roblox_data(cookie)

            if not is_valid and admin_row:
                # 이미 알림 보냈으면 스킵
                if not alert_row or alert_row[0] == "0":
                    admin = await self.fetch_user(int(admin_row[0]))
                    if admin:
                        await admin.send(
                            f"<:downvote:1489930277450158080> **쿠키 만료 감지**\n"
                            f"- 사유: {result}\n"
                            f"- `/쿠키등록` 으로 쿠키를 갱신해주세요"
                        )
                    with sqlite3.connect(DATABASE) as conn:
                        cur = conn.cursor()
                        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('cookie_alert_sent', '1')")
                        conn.commit()
            else:
                # 쿠키 정상이면 알림 초기화
                if alert_row and alert_row[0] == "1":
                    with sqlite3.connect(DATABASE) as conn:
                        cur = conn.cursor()
                        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('cookie_alert_sent', '0')")
                        conn.commit()
        except Exception as e:
            print(f"[쿠키감지 실패] {e}")

        # 기존 자판기 업데이트 코드
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
