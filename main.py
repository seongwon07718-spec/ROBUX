class GiftModal(ui.Modal, title="글로벌 선물 방식"):
    roblox_name = ui.TextInput(
        label="로블록스 닉네임",
        placeholder="선물받을 유저의 닉네임을 입력하세요",
        required=True,
        max_length=20,
    )

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)

        target_name = self.roblox_name.value.strip()
        loop = asyncio.get_running_loop()
        api = RobloxAPI()
        target_id = await loop.run_in_executor(None, api.get_user_id, target_name)

        if not target_id:
            await it.followup.send(
                view=await get_container_view("❌ 실패", "-# 유저를 찾을 수 없습니다.", 0xED4245),
                ephemeral=True
            )
            return

        # 게임 선택 드롭다운
        view = ui.LayoutView(timeout=60)
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            f"### 🎁 글로벌 선물 방식\n"
            f"-# - **선물 대상**: `{target_name}`\n"
            f"-# - 선물할 게임을 선택해주세요"
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        select = ui.Select(placeholder="게임을 선택해주세요")
        for name, uid in GIFT_GAMES:
            select.add_option(label=name, value=uid)

        async def on_game_select(interaction: discord.Interaction):
            selected_uid = interaction.data["values"][0]
            game_name = next((n for n, u in GIFT_GAMES if u == selected_uid), "알 수 없음")

            loading_view = ui.LayoutView(timeout=60)
            loading_con = ui.Container()
            loading_con.accent_color = 0xFEE75C
            loading_con.add_item(ui.TextDisplay(
                f"### ⏳ 불러오는 중\n"
                f"-# - **선물 대상**: `{target_name}`\n"
                f"-# - **게임**: `{game_name}`\n"
                f"-# - 게임패스 목록을 불러오는 중입니다..."
            ))
            loading_view.add_item(loading_con)
            await interaction.response.edit_message(view=loading_view)

            passes = await asyncio.get_running_loop().run_in_executor(
                None, api.get_place_gamepasses, int(selected_uid)
            )

            if not passes:
                fail_view = ui.LayoutView(timeout=60)
                fail_con = ui.Container()
                fail_con.accent_color = 0xED4245
                fail_con.add_item(ui.TextDisplay(
                    f"### ❌ 게임패스 없음\n"
                    f"-# - **게임**: `{game_name}`\n"
                    f"-# - 판매 중인 게임패스가 없습니다."
                ))
                fail_view.add_item(fail_con)
                await interaction.edit_original_response(view=fail_view)
                return

            pass_view = ui.LayoutView(timeout=60)
            pass_con = ui.Container()
            pass_con.accent_color = 0x5865F2
            pass_con.add_item(ui.TextDisplay(
                f"### 🎁 게임패스 선택\n"
                f"-# - **선물 대상**: `{target_name}`\n"
                f"-# - **게임**: `{game_name}`\n"
                f"-# - 선물할 게임패스를 선택해주세요"
            ))
            pass_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            pass_select = ui.Select(placeholder="게임패스를 선택해주세요")
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

                result_view = ui.LayoutView(timeout=60)
                result_con = ui.Container()
                result_con.accent_color = 0x57F287
                result_con.add_item(ui.TextDisplay(
                    f"### 🎁 선물 정보 확인\n"
                    f"-# - **선물 대상**: `{target_name}`\n"
                    f"-# - **게임**: `{game_name}`\n"
                    f"-# - **게임패스**: `{pass_data.get('name', '이름없음')}`\n"
                    f"-# - **가격**: `{pass_data.get('price', 0):,}` R$\n"
                    f"-# ⚠️ 글로벌 선물 방식은 준비 중입니다"
                ))
                result_view.add_item(result_con)
                await inter.response.edit_message(view=result_view)

            pass_select.callback = on_pass_select
            pass_con.add_item(ui.ActionRow(pass_select))
            pass_view.add_item(pass_con)
            await interaction.edit_original_response(view=pass_view)

        select.callback = on_game_select
        con.add_item(ui.ActionRow(select))
        view.add_item(con)
        await it.followup.send(view=view, ephemeral=True)
