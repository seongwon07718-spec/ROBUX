    async def on_proceed(proceed_inter: discord.Interaction):
        # 1. 고유 주문 ID 생성
        order_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

        # 2. DB에 주문 데이터 삽입
        try:
            with sqlite3.connect(DATABASE) as conn:
                conn.execute(
                    "INSERT INTO gift_queue (order_id, target_id, pass_id, status) VALUES (?, ?, ?, ?)",
                    (order_id, str(target_id), str(selected_id), "processing")
                )
                conn.commit()
        except Exception as e:
            await proceed_inter.response.edit_message(
                view=await get_container_view(
                    "<:downvote:1489930277450158080>  DB 오류",
                    f"-# - 주문 생성 중 오류가 발생했습니다\n-# - {e}",
                    0xED4245
                )
            )
            return

        # 3. 선물 진행 중 메시지
        await proceed_inter.response.edit_message(
            view=await get_container_view(
                "<a:1792loading:1487444148716965949>  선물 진행 중",
                f"-# - **대상**: {target_name} (`{target_id}`)\n"
                f"-# - 봇이 게임 내에서 선물을 처리하고 있습니다\n"
                f"-# - 결과가 나올 때까지 잠시만 기다려주세요",
                0x5865F2
            )
        )

        # 4. 완료 감시 (최대 60초)
        success = False
        final_status = "timeout"

        for _ in range(30):
            await asyncio.sleep(2)
            try:
                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT status FROM gift_queue WHERE order_id = ?",
                        (order_id,)
                    )
                    row = cur.fetchone()

                if row:
                    if row[0] == "completed":
                        success = True
                        final_status = "completed"
                        break
                    elif row[0] == "failed":
                        success = False
                        final_status = "failed"
                        break
            except Exception as e:
                print(f"[폴링 오류] {e}")

        # 5. 최종 결과
        if success:
            await proceed_inter.edit_original_response(
                view=await get_container_view(
                    "<:success:1489875582874554429>  선물 완료",
                    f"-# - **대상**: {target_name}\n"
                    f"-# - **아이템**: {pass_data.get('name', '게임패스')}\n"
                    f"-# - 성공적으로 선물이 전달되었습니다",
                    0x57F287
                )
            )
        else:
            reason = "시간 초과" if final_status == "timeout" else "인게임 오류"
            await proceed_inter.edit_original_response(
                view=await get_container_view(
                    "<:downvote:1489930277450158080>  선물 실패",
                    f"-# - **사유**: {reason}\n"
                    f"-# - 봇 콘솔 또는 로벅스 잔액을 확인해주세요",
                    0xED4245
                )
            )

        # 6. 처리된 주문 정리
        try:
            with sqlite3.connect(DATABASE) as conn:
                conn.execute(
                    "DELETE FROM gift_queue WHERE order_id = ?",
                    (order_id,)
                )
                conn.commit()
        except Exception:
            pass
