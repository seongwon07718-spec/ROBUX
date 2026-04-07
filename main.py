                async def on_proceed(proceed_inter: discord.Interaction):
                    order_id = str(uuid.uuid4())[:8]
                    
                    # 1. 진행 중 상태로 변경
                    await proceed_inter.response.edit_message(
                        view=await get_container_view(
                            "<a:1792loading:1487444148716965949>  선물 진행 중",
                            f"### <:acy2:1489883409001091142>  Rivals 선물 프로세스\n"
                            f"-# - **대상**: {target_name} ({target_id})\n"
                            f"-# - 봇이 게임에 접속하여 선물을 전송 중입니다.\n"
                            f"-# - 잠시만 기다려주세요... (약 1분 소요)",
                            0xFEE75C
                        )
                    )

                    # DB에 주문 데이터 삽입
                    with sqlite3.connect(DATABASE) as conn:
                        conn.execute(
                            "INSERT INTO gift_queue (order_id, target_id, pass_id, status) VALUES (?, ?, ?, ?)",
                            (order_id, target_id, selected_id, 'processing')
                        )
                        conn.commit()

                    # 2. 로블록스 실행
                    subprocess.Popen(["cmd", "/c", f"start roblox://experiences/start?placeId={selected_place_id}"])

                    # 3. 완료 감시 (Polling)
                    success = False
                    for _ in range(30): # 60초 대기
                        await asyncio.sleep(2)
                        with sqlite3.connect(DATABASE) as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT status FROM gift_queue WHERE order_id = ?", (order_id,))
                            row = cur.fetchone()
                            if row and row[0] == 'completed':
                                success = True
                                break
                            elif row and row[0] == 'failed':
                                break

                    # 4. 결과 업데이트
                    if success:
                        await proceed_inter.edit_original_response(
                            view=await get_container_view(
                                "<:success:1489875582874554429>  선물 완료",
                                f"### <:acy2:1489883409001091142>  선물 성공!\n"
                                f"-# - **대상**: {target_name}\n"
                                f"-# - 모든 절차가 정상적으로 완료되었습니다.",
                                0x57F287
                            )
                        )
                    else:
                        await proceed_inter.edit_original_response(
                            view=await get_container_view(
                                "<:downvote:1489930277450158080>  선물 실패",
                                f"### <:acy2:1489883409001091142>  선물 전송 실패\n"
                                f"-# - **사유**: 시간 초과 또는 인게임 오류\n"
                                f"-# - 봇의 로벅스 잔액이나 게임 상태를 확인하세요.",
                                0xED4245
                            )
                        )
