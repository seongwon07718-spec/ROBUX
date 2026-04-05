            if not passes:

                fail_view = ui.LayoutView(timeout=60)
                fail_con = ui.Container()
                fail_con.accent_color = 0xED4245
                fail_con.add_item(ui.TextDisplay(
                    f"### <:downvote:1489930277450158080>  게임패스 없음\n"
                    f"-# - **게임**: {game_name}\n"
                    f"-# - 판매 중인 게임패스가 없습니다"
                ))
                fail_view.add_item(fail_con)
                await interaction.edit_original_response(view=fail_view)
                return

            pass_view = ui.LayoutView(timeout=60)
            pass_con = ui.Container()
            pass_con.accent_color = 0x5865F2

            pass_con.add_item(ui.TextDisplay(
                f"### <:acy2:1489883409001091142>  게임패스 선택\n"
                f"-# - **선물 대상**: {target_name}\n"
                f"-# - **게임**: {game_name}\n"
                f"-# - 선물할 게임패스를 선택해주세요"
            ))

            pass_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            pass_select = ui.Select(
                placeholder="게임패스를 선택해주세요",
                custom_id=str(uuid.uuid4()).replace("-", "")[:40]
            )

            for p in passes[:25]:
                pass_select.add_option(
                    label=f"{p.get('name', '이름없음')[:80]} ({p.get('price', 0):,} R$)",
                    value=str(p.get("id")),
                )

            async def on_pass_select(inter: discord.Interaction):

                selected_id = int(inter.data["values"][0])
                pass_data = next((p for p in passes if p.get("id") == selected_id), None)

                if not pass_data:
                    await inter.response.send_message("오류가 발생했습니다.", ephemeral=True)
                    return

                # 할인율 조회
                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()

                    cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
                    r = cur.fetchone()
                    rate = int(r[0]) if r else 1000

                    cur.execute(
                        "SELECT value FROM config WHERE key = ?",
                        (f"discount_{inter.user.id}",)
                    )
                    d = cur.fetchone()
                    discount = int(d[0]) if d else 0

                base_money = int((pass_data.get("price", 0) / rate) * 10000)
                final_money = int(base_money * (1 - discount / 100)) if discount > 0 else base_money

                discount_text = (
                    f"-# - **할인율**: {discount}%\n"
                    f"-# - **원래 가격**: ~~{base_money:,}원~~\n"
                    f"-# - **최종 가격**: {final_money:,}원"
                ) if discount > 0 else (
                    f"-# - **결제 금액**: {final_money:,}원"
                )

                result_view = ui.LayoutView(timeout=60)
                result_con = ui.Container()
                result_con.accent_color = 0x5865F2

                result_con.add_item(ui.TextDisplay(
                    f"### <:acy2:1489883409001091142>  선물 정보 확인\n"
                    f"-# - **선물 대상**: {target_name}\n"
                    f"-# - **게임**: {game_name}\n"
                    f"-# - **게임패스**: {pass_data.get('name', '이름없음')}\n"
                    f"-# - **가격**: {pass_data.get('price', 0):,}로벅스\n"
                    f"{discount_text}"
                ))

                result_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

                proceed_btn = ui.Button(
                    label="진행하기",
                    style=discord.ButtonStyle.gray,
                    emoji="<:success:1489875582874554429>",
                    custom_id=str(uuid.uuid4()).replace("-", "")[:40]
                )

                async def on_proceed(proceed_inter: discord.Interaction):

                    await proceed_inter.response.edit_message(
                        view=await get_container_view(
                            "<a:1792loading:1487444148716965949>  게임 실행 중",
                            "-# - 잠시만 기다려주세요...",
                            0x5865F2
                        )
                    )

                    settings_path = os.path.expandvars(r"%LOCALAPPDATA%\Roblox\Versions")
                    try:
                        for ver in os.listdir(settings_path):
                            cfg_path = os.path.join(
                                settings_path, ver,
                                "ClientSettings", "ClientAppSettings.json"
                            )
                            os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
                            with open(cfg_path, "w") as f:
                                json.dump({
                                    "FFlagHandleAltEnterFullscreenManually": "False",
                                    "FFlagDebugFullscreenTitlebarRevamp": "False"
                                }, f)
                    except:
                        pass

                    subprocess.Popen([
                        "cmd", "/c",
                        f"start roblox://experiences/start?placeId={selected_place_id}"
                    ])

                    await asyncio.sleep(8)

                    await proceed_inter.edit_original_response(
                        view=await get_container_view(
                            "✅ 게임 실행됨",
                            f"-# - **게임**: {game_name}\n"
                            f"-# - **선물 대상**: {target_name}",
                            0x57F287
                        )
                    )

                proceed_btn.callback = on_proceed

                result_con.add_item(ui.ActionRow(proceed_btn))

                result_view.add_item(result_con)

                await inter.response.edit_message(view=result_view)

            pass_select.callback = on_pass_select

            pass_con.add_item(ui.ActionRow(pass_select))

            pass_view.add_item(pass_con)

            await interaction.edit_original_response(view=pass_view)
