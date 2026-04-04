        # ... 상단 코드 생략 ...
        con.add_item(ui.TextDisplay("### <:emoji_18:1487422236838334484>  실시간 재고\n"))
        
        # 단일 이미지 삽입 (리스트 내 요소를 하나만 유지)
        single_image = ui.MediaItem(url="https://your-image-url.com/stock.png")
        con.add_item(ui.MediaGallery(items=[single_image])) 
        
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        # ... 하단 코드 생략 ...
