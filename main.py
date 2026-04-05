GIFT_GAMES = [
    ("Rivals", "17625359962"),
    ("Blade Ball", "13772394625"),
    ("Blox Fruits", "2753915549"),
    ("Pet Simulator 99", "8737899170"),
    ("Brookhaven", "4924922222"),
    ("Adopt Me!", "920587237"),
    ("Murder Mystery 2", "142823291"),
    ("Tower of Hell", "1962086868"),
    ("Arsenal", "286090429"),
    ("Jailbreak", "606849621"),
    ("Anime Adventures", "8874607894"),
    ("The Mimic", "7704844595"),
    ("Dress to Impress", "12699763399"),
    ("Deepwoken", "4111023553"),
    ("Da Hood", "2788229376"),
]


class GiftModal(ui.Modal, title="글로벌 선물 방식"):
    roblox_name = ui.TextInput(
        label="로블록스 닉네임",
        placeholder="선물받을 유저의 닉네임을 입력하세요",
        required=True,
        max_length=20,
    )

    game_select = ui.Select(
        placeholder="선물할 게임을 선택해주세요",
        options=[
            discord.SelectOption(label=name, value=uid)
            for name, uid in GIFT_GAMES
        ]
    )

    def __init__(self):
        super().__init__(title="글로벌 선물 방식")
        self.add_item(ui.Label(
            text="선물할 게임을 선택해주세요",
            component=self.game_select
        ))

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)

        target_name = self.roblox_name.value.strip()

        if not self.game_select.values:
            await it.followup.send(
                view=await get_container_view("❌ 실패", "-# 게임을 선택해주세요.", 0xED4245),
                ephemeral=True
            )
            return

        selected_uid = self.game_select.values[0]
        game_name = next((n for n, u in GIFT_GAMES if u == selected_uid), "알 수 없음")

        loop = asyncio.get_running_loop()
        api = RobloxAPI()
        target_id = await loop.run_in_executor(None, api.get_user_id, target_name)

        if not target_id:
            await it.followup.send(
                view=await get_container_view("❌ 실패", "-# 유저를 찾을 수 없습니다.", 0xED4245),
                ephemeral=True
            )
            return

        # 게임패스 로딩
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
        await it.followup.send(view=loading_view, ephemeral=True)

        passes = await loop.run_in_executor(None, api.get_place_gamepasses, int(selected_uid))

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
            await it.edit_original_response(view=fail_view)
            return

        # 게임패스 선택 뷰
        view = ui.LayoutView(timeout=60)
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            f"### 🎁 게임패스 선택\n"
            f"-# - **선물 대상**: `{target_name}`\n"
            f"-# - **게임**: `{game_name}`\n"
            f"-# - 선물할 게임패스를 선택해주세요"
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        select = ui.Select(placeholder="게임패스를 선택해주세요")
        for p in passes[:25]:
            select.add_option(
                label=f"{p.get('name', '이름없음')[:80]} ({p.get('price', 0):,} R$)",
                value=str(p.get("id")),
            )

        async def on_pass_select(interaction: discord.Interaction):
            selected_id = int(interaction.data["values"][0])
            pass_data = next((p for p in passes if p.get("id") == selected_id), None)
            if not pass_data:
                await interaction.response.send_message("오류가 발생했습니다.", ephemeral=True)
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
            await interaction.response.edit_message(view=result_view)

        select.callback = on_pass_select
        con.add_item(ui.ActionRow(select))
        view.add_item(con)
        await it.edit_original_response(view=view)


# shop_callback 수정
async def shop_callback(self, it: discord.Interaction):
    con = ui.Container()
    con.accent_color = 0x5865F2

    con.add_item(ui.TextDisplay("### <:acy2:1489883409001091142>  구매 방식 선택"))
    con.add_item(ui.TextDisplay("-# - 원하시는 구매 방식을 선택해주세요"))
    con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

    btn_gp = ui.Button(label="게임패스 방식", style=discord.ButtonStyle.gray, emoji="<:opt_online:1489872305138962452>")
    btn_ingame = ui.Button(label="글로벌 선물 방식", style=discord.ButtonStyle.gray, emoji="<:opt_online:1489872305138962452>")
    btn_group = ui.Button(label="그룹 지급 방식", style=discord.ButtonStyle.gray, emoji="<:opt_offline:1489886702368723087>", disabled=True)

    btn_gp.callback = lambda i: i.response.send_modal(NicknameSearchModal())
    btn_ingame.callback = lambda i: i.response.send_modal(GiftModal())

    async def method_callback(interaction):
        await interaction.response.send_message(f"**{interaction.data['label']}** 방식 상품 준비 중입니다.", ephemeral=True)

    btn_group.callback = method_callback

    con.add_item(ui.ActionRow(btn_gp, btn_group, btn_ingame))

    new_view = ui.LayoutView(timeout=None)
    new_view.add_item(con)

    await it.response.send_message(view=new_view, ephemeral=True)
