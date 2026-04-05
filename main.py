# GIFT_GAMES에 place ID 그대로 사용
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

async def on_game_select(interaction: discord.Interaction):
    selected_place_id = interaction.data["values"][0]
    game_name = next((n for n, u in GIFT_GAMES if u == selected_place_id), "알 수 없음")

    loading_view = ui.LayoutView(timeout=60)
    loading_con = ui.Container()
    loading_con.accent_color = 0xFEE75C
    loading_con.add_item(ui.TextDisplay(
        f"### ⏳ 불러오는 중\n"
        f"-# - **게임**: `{game_name}`\n"
        f"-# - 게임패스 목록을 불러오는 중입니다..."
    ))
    loading_view.add_item(loading_con)
    await interaction.response.edit_message(view=loading_view)

    loop = asyncio.get_running_loop()

    # place ID → universe ID 변환
    def get_universe_id(place_id):
        resp = requests.get(
            f"https://apis.roproxy.com/universes/v1/places/{place_id}/universe"
        )
        if resp.status_code == 200:
            return resp.json().get("universeId")
        return None

    universe_id = await loop.run_in_executor(None, get_universe_id, selected_place_id)

    if not universe_id:
        fail_view = ui.LayoutView(timeout=60)
        fail_con = ui.Container()
        fail_con.accent_color = 0xED4245
        fail_con.add_item(ui.TextDisplay(f"### ❌ 오류\n-# - 게임 정보를 불러올 수 없습니다."))
        fail_view.add_item(fail_con)
        await interaction.edit_original_response(view=fail_view)
        return

    passes = await loop.run_in_executor(None, api.get_place_gamepasses, universe_id)
    # 나머지 동일...
