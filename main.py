    async def setup_hook(self):
        self.stock_updater.start()
        await self.tree.sync()

        # DB에서 자판기 메시지 불러오기 + 뷰 재등록
        try:
            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT channel_id, msg_id FROM vending_messages")
                rows = cur.fetchall()

            for channel_id, msg_id in rows:
                self.vending_msg_info[int(channel_id)] = int(msg_id)

                # 뷰 재등록 - 버튼 콜백 살리기
                view = RobuxVending(self)
                await view.build_main_menu()
                self.add_view(view)

            print(f"[자판기] {len(rows)}개 복구됨")
        except Exception as e:
            print(f"[자판기 복구 실패] {e}")
