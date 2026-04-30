@bot.tree.command(name="라이센스_생성", description="라이센스 키를 생성합니다")
@app_commands.describe(기간="라이센스 기간 선택", 수량="생성할 수량 (최대 100개)")
@app_commands.choices(기간=[
    app_commands.Choice(name="7일",  value=7),
    app_commands.Choice(name="30일", value=30),
    app_commands.Choice(name="60일", value=60),
    app_commands.Choice(name="90일", value=90),
])
async def create_license(interaction: discord.Interaction, 기간: app_commands.Choice[int], 수량: int):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message(
            view=SimpleLayout("## 권한 없음", "이 명령어는 봇 관리자만 사용할 수 있습니다.", discord.Color.red()),
            ephemeral=True
        )
        return

    if 수량 < 1 or 수량 > 100:
        await interaction.response.send_message(
            view=SimpleLayout("## 잘못된 수량", "수량은 1개 이상 100개 이하로 입력해주세요.", discord.Color.red()),
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    conn = sqlite3.connect(LICENSE_DB)
    c = conn.cursor()
    keys = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for _ in range(수량):
        key = create_unique_key()
        c.execute("INSERT INTO licenses (key, days, created_at) VALUES (?, ?, ?)", (key, 기간.value, now))
        keys.append(key)

    conn.commit()
    conn.close()

    txt = "VOUT 라이센스 키 목록\n"
    txt += f"생성일시: {now}\n"
    txt += f"기간: {기간.value}일 / 수량: {수량}개\n"
    txt += "=" * 40 + "\n\n"
    for i, key in enumerate(keys, 1):
        txt += f"{i:>3}. {key}\n"

    fname = f"licenses_{기간.value}일_{수량}개_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    file_bytes = io.BytesIO(txt.encode("utf-8"))
    
    # 실제 파일 객체 생성 (메시지와 함께 업로드할 것)
    discord_file = discord.File(fp=file_bytes, filename=fname)

    # Container 안에서는 attachment://filename 으로 참조
    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 라이센스 생성 완료"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"요청하신 {수량}개의 라이센스가 생성되었습니다.\n아래 파일을 내려받아 확인하세요."),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.File(  # ← 여기서 attachment:// 사용
            url=f"attachment://{fname}",
            # spoiler=False (필요시 True)
        ),
        accent_color=discord.Color.green()
    )
    view.add_item(container)

    # 중요: file= 매개변수로 실제 파일 전달
    await interaction.followup.send(view=view, file=discord_file, ephemeral=True)
