    # ... (목록 생성 부분은 그대로)

    fname = f"license_list_{filter_val}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    file_bytes = io.BytesIO(txt.encode("utf-8"))
    discord_file = discord.File(fp=file_bytes, filename=fname)

    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"## 라이센스 목록 ({filter_label})"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"현재 데이터베이스에 저장된 {len(rows)}개의 목록입니다."),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.File(url=f"attachment://{fname}"),
        accent_color=discord.Color.from_str("#5865F2")
    )
    view.add_item(container)

    await interaction.followup.send(view=view, file=discord_file, ephemeral=True)
