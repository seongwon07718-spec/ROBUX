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
        f"### <:acy2:1489883409001091142> 선물 정보 확인\n"
        f"-# - **선물 대상**: {target_name}\n"
        f"-# - **게임**: {game_name}\n"
        f"-# - **게임패스**: {pass_data.get('name', '이름없음')}\n"
        f"-# - **가격**: {pass_data.get('price', 0):,}로벅스\n"
    ))
    result_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

    proceed_btn = ui.Button(
        label="진행하기",
        style=discord.ButtonStyle.gray,
        emoji="<:upvote:1489930275868770305>"
    )

    async def on_proceed(proceed_inter: discord.Interaction):
        await proceed_inter.response.edit_message(
            view=await get_container_view(
                "<a:1792loading.:1487444148716965949> 처리 중",
                "-# - 로블록스 실행 중...",
                0x57F287
            )
        )

        # 로블록스 창모드로 실행
        import subprocess
        import requests as req

        # 봇 계정 쿠키로 인증 티켓 발급
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
            row = cur.fetchone()

        if not row:
            await proceed_inter.edit_original_response(
                view=await get_container_view("❌ 실패", "-# 관리자 쿠키 없음", 0xED4245)
            )
            return

        cookie = row[0].strip()
        if "=" in cookie:
            cookie = cookie.split("=", 1)[-1]

        # 인증 티켓 발급
        session = req.Session()
        session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
        ticket_resp = session.post("https://auth.roblox.com/v1/authentication-ticket", headers={
            "Referer": "https://www.roblox.com",
            "Content-Type": "application/json"
        })
        ticket = ticket_resp.headers.get("rbx-authentication-ticket")

        if not ticket:
            await proceed_inter.edit_original_response(
                view=await get_container_view("❌ 실패", "-# 인증 티켓 발급 실패", 0xED4245)
            )
            return

        place_id = selected_place_id
        launch_url = (
            f"roblox-player:1+launchmode:play"
            f"+gameinfo:{ticket}"
            f"+launchtime:{int(time.time() * 1000)}"
            f"+placelauncherurl:https://assetgame.roblox.com/game/PlaceLauncher.ashx"
            f"?request=RequestGame%26placeId={place_id}%26isPartyLeader=false"
            f"+browsertrackerid:0"
            f"+robloxLocale:ko_kr"
            f"+gameLocale:ko_kr"
            f"+channel:"
        )

        # 창모드 설정 (ClientAppSettings.json)
        import os, json
        settings_path = os.path.expandvars(
            r"%LOCALAPPDATA%\Roblox\Versions"
        )
        try:
            for ver in os.listdir(settings_path):
                cfg_path = os.path.join(settings_path, ver, "ClientSettings", "ClientAppSettings.json")
                os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
                with open(cfg_path, "w") as f:
                    json.dump({"FFlagHandleAltEnterFullscreenManually": "False"}, f)
        except:
            pass

        subprocess.Popen(["cmd", "/c", f"start {launch_url}"])

        await proceed_inter.edit_original_response(
            view=await get_container_view(
                "✅ 로블록스 실행됨",
                f"-# - **게임**: {game_name}\n"
                f"-# - **선물 대상**: {target_name}\n"
                f"-# - 게임 접속 후 선물이 자동으로 진행됩니다",
                0x57F287
            )
        )

    proceed_btn.callback = on_proceed
    result_con.add_item(ui.ActionRow(proceed_btn))
    result_view.add_item(result_con)
    await inter.response.edit_message(view=result_view)
