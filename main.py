                        # 게임 직접 접속 URL
                        launch_url = (
                            f"roblox-player:1+launchmode:play"
                            f"+gameinfo:0"
                            f"+launchtime:0"
                            f"+placelauncherurl:https://assetgame.roblox.com/game/PlaceLauncher.ashx"
                            f"?request=RequestGame"
                            f"%26placeId={selected_place_id}"
                            f"%26isPartyLeader=false"
                            f"+browsertrackerid:0"
                            f"+robloxLocale:ko_kr"
                            f"+gameLocale:ko_kr"
                            f"+channel:"
                        )

                        subprocess.Popen(["cmd", "/c", f"start {launch_url}"])
