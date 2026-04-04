        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### <:emoji_18:1487422236838334484>  지급방식\n-# - 겜패 선물 방식\n-# - 인게임 선물 방식"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        con.add_item(ui.TextDisplay("### <:emoji_18:1487422236838334484>  실시간 재고\n"))

        # --- 이 부분을 딕셔너리 형태로 수정하세요 ---
        media_gallery = {
            "type": 13,  # Media Gallery 타입 번호
            "items": [
                {
                    "media": "https://cdn.discordapp.com/attachments/...", # 본인의 이미지 URL
                    "description": "실시간 재고 이미지"
                }
            ]
        }
        # con.add_item 대신 로우 데이터를 직접 컨테이너 컴포넌트 리스트에 추가하거나,
        # 아래와 같이 to_dict를 활용하는 트릭이 필요할 수 있습니다.
        # 가장 속 편한 방법은 아래 '완전 수동 방식' 섹션을 참고하세요.
