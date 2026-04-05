                    async def on_proceed(proceed_inter: discord.Interaction):

                        await proceed_inter.response.edit_message(
                            view=await get_container_view(
                                "<a:1792loading.:1487444148716965949> 처리 중",
                                "-# - 로블록스 실행 중...",
                                0x57F287
                            )
                        )

                        import subprocess, os, json

                        # 창모드 설정
                        settings_path = os.path.expandvars(r"%LOCALAPPDATA%\Roblox\Versions")
                        try:
                            for ver in os.listdir(settings_path):
                                cfg_path = os.path.join(
                                    settings_path, ver,
                                    "ClientSettings", "ClientAppSettings.json"
                                )
                                os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
                                with open(cfg_path, "w") as f:
                                    json.dump({"FFlagHandleAltEnterFullscreenManually": "False"}, f)
                        except:
                            pass

                        # 그냥 URL로 바로 실행
                        launch_url = f"https://www.roblox.com/games/{selected_place_id}"
                        subprocess.Popen(["cmd", "/c", f"start {launch_url}"])

                        await proceed_inter.edit_original_response(
                            view=await get_container_view(
                                "✅ 로블록스 실행됨",
                                f"-# - **게임**: {game_name}\n"
                                f"-# - **선물 대상**: {target_name}",
                                0x57F287
                            )
                        )
