    async def do_buy(self, it: discord.Interaction):

        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'maintenance'")
            m = cur.fetchone()

        if m and m[0] == "1":
            await it.response.edit_message(
                view=await get_container_view(
                    "<:downvote:1489930277450158080>  점검 중",
                    "-# - 현재 점검 중입니다\n-# - 잠시 후 다시 시도해주세요",
                    0xED4245
                )
            )
            return

        start_time = asyncio.get_event_loop().time()

        await it.response.edit_message(
            view=await get_container_view(
                "<a:1792loading:1487444148716965949>  대기 중",
                "-# - 대기열에 등록되었습니다\n-# - 잠시만 기다려주세요...",
                0x5865F2
            )
        )

        loop = asyncio.get_running_loop()
        from buy_gamepass import queue_status

        order_ref = {"id": None}

        async def update_position():
            while True:
                await asyncio.sleep(3)
                try:
                    for oid, info in list(queue_status.items()):
                        if order_ref["id"] and oid != order_ref["id"]:
                            continue
                        if info["status"] == "waiting":
                            pos = info["position"]
                            try:
                                await it.edit_original_response(
                                    view=await get_container_view(
                                        "<a:1792loading:1487444148716965949>  대기 중",
                                        f"-# - 대기열: **{pos}번째**\n-# - 앞에 {pos - 1}명이 있습니다",
                                        0x5865F2
                                    )
                                )
                            except Exception:
                                pass
                        elif info["status"] == "processing":
                            try:
                                await it.edit_original_response(
                                    view=await get_container_view(
                                        "<a:1792loading:1487444148716965949>  구매 진행 중",
                                        "-# - 로블록스 서버 API 연결 중입니다\n-# - 구매를 진행하는데 약간의 시간이 소요될 수 있습니다",
                                        0x57F287
                                    )
                                )
                            except Exception:
                                pass
                except Exception:
                    pass

        update_task = asyncio.create_task(update_position())

        res = await loop.run_in_executor(
            None, process_manual_buy_selenium,
            self.pass_info["id"], self.user_id, self.money
        )

        update_task.cancel()

        elapsed = round(asyncio.get_event_loop().time() - start_time, 1)

        if res["success"]:
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

            try:
                if screenshot and os.path.exists(screenshot):
                    await it.user.send(
                        content=f"<:acy2:1489883409001091142> **@{it.user.name} 구매 완료 - 거래ID: `{res['order_id']}`**",
                        file=discord.File(screenshot, filename="success.png")
                    )
                else:
                    await it.user.send(
                        content=f"<:acy2:1489883409001091142> **@{it.user.name} 구매 완료 - 거래ID: `{res['order_id']}`**\n- 게임패스: {self.pass_info.get('name', '알 수 없음')}\n- 가격: {self.pass_info.get('price', 0):,}로벅스\n- 결제금액: {self.money:,}원\n- 처리시간: {elapsed}초"
                    )
            except Exception as e:
                print(f"[DM 실패] {e}")

            try:
                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT value FROM config WHERE key = 'purchase_log'")
                    log_row = cur.fetchone()

                if log_row:
                    log_channel = bot.get_channel(int(log_row[0]))
                    if log_channel:
                        if screenshot and os.path.exists(screenshot):
                            await log_channel.send(
                                content=f"<:acy2:1489883409001091142> **{it.user.mention} / {self.pass_info.get('price', 0):,}로벅스 구매 감사합니다**\n- 게임패스: {self.pass_info.get('name', '알 수 없음')}\n- 결제금액: {self.money:,}원\n- 거래ID: `{res['order_id']}`",
                                file=discord.File(screenshot, filename="success.png")
                            )
                        else:
                            await log_channel.send(
                                content=f"<:acy2:1489883409001091142> **{it.user.mention} / {self.pass_info.get('price', 0):,}로벅스 구매 감사합니다**\n- 게임패스: {self.pass_info.get('name', '알 수 없음')}\n- 결제금액: {self.money:,}원\n- 거래ID: `{res['order_id']}`"
                            )
            except Exception as e:
                print(f"[로그 실패] {e}")

        elif res.get("message") and "이미 소유" in res["message"]:
            view = ui.LayoutView()
            con = ui.Container()
            con.accent_color = 0xED4245
            con.add_item(ui.TextDisplay(
                f"### <:downvote:1489930277450158080>  구매 불가\n"
                f"-# - **게임패스**: {self.pass_info.get('name', '알 수 없음')}\n"
                f"-# - 이미 보유 중인 게임패스입니다\n"
                f"-# - 다른 게임패스를 선택해주세요"
            ))
            view.add_item(con)
            await it.edit_original_response(view=view)

        else:
            await it.edit_original_response(
                view=await get_container_view(
                    "<:downvote:1489930277450158080>  결제 실패",
                    f"-# {res.get('message', '알 수 없는 오류')}",
                    0xED4245
                )
            )
