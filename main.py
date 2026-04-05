            async def on_pass_select(inter: discord.Interaction):

                selected_id = int(inter.data["values"][0])
                pass_data = next((p for p in passes if p.get("id") == selected_id), None)

                if not pass_data:
                    await inter.response.send_message("오류가 발생했습니다.", ephemeral=True)
                    return

                result_view = ui.LayoutView(timeout=60)
                result_con = ui.Container()
                result_con.accent_color = 0x5865F2

                result_con.add_item(ui.TextDisplay(
                    f"### <:acy2:1489883409001091142>  선물 정보 확인\n"
                    f"-# - **선물 대상**: {target_name}\n"
                    f"-# - **게임**: {game_name}\n"
                    f"-# - **게임패스**: {pass_data.get('name', '이름없음')}\n"
                    f"-# - **가격**: {pass_data.get('price', 0):,}로벅스"
                ))

                result_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

                proceed_btn = ui.Button(
                    label="진행하기",
                    style=discord.ButtonStyle.gray,
                    emoji="<:success:1489875582874554429>",
                    custom_id=str(uuid.uuid4()).replace("-", "")[:40]
                )
