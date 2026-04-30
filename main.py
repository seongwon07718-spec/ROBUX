# ── 라이센스 키 생성 명령어 수정 ──────────────────────────
@bot.tree.command(name="라이센스생성", description="[관리자] 라이센스 키를 생성합니다.")
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
    file_data = discord.File(fp=io.BytesIO(txt.encode("utf-8")), filename=fname)

    # V2 컨테이너 내부에 파일 배치
    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🔑 라이센스 생성 완료"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"요청하신 {수량}개의 라이센스가 생성되었습니다.\n아래 파일을 내려받아 확인하세요."),
        discord.ui.File(file=file_data), # 컨테이너 안에 파일 배치
        accent_color=discord.Color.green()
    )
    view.add_item(container)

    await interaction.followup.send(view=view, ephemeral=True)


# ── 라이센스 목록 조회 명령어 수정 ──────────────────────────
@bot.tree.command(name="라이센스목록", description="[관리자] 발급된 라이센스 키 목록을 조회합니다.")
@app_commands.describe(필터="조회할 상태 필터")
@app_commands.choices(필터=[
    app_commands.Choice(name="전체",   value="all"),
    app_commands.Choice(name="미사용", value="unused"),
    app_commands.Choice(name="사용됨", value="used"),
])
async def list_licenses(interaction: discord.Interaction, 필터: app_commands.Choice[str] = None):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message(
            view=SimpleLayout("## 권한 없음", "이 명령어는 봇 관리자만 사용할 수 있습니다.", discord.Color.red()),
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    conn = sqlite3.connect(LICENSE_DB)
    c = conn.cursor()

    filter_val = 필터.value if 필터 else "all"
    if filter_val == "unused":
        c.execute("SELECT key, days, used, guild_name, created_at FROM licenses WHERE used = 0")
    elif filter_val == "used":
        c.execute("SELECT key, days, used, guild_name, created_at FROM licenses WHERE used = 1")
    else:
        c.execute("SELECT key, days, used, guild_name, created_at FROM licenses")

    rows = c.fetchall()
    conn.close()

    filter_label = {"all": "전체", "unused": "미사용", "used": "사용됨"}.get(filter_val, "전체")

    if not rows:
        await interaction.followup.send(
            view=SimpleLayout(
                f"## 라이센스 목록 [{filter_label}]",
                "조회된 라이센스가 없습니다.",
                discord.Color.from_str("#5865F2")
            ),
            ephemeral=True
        )
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txt = f"VOUT 라이센스 목록 [{filter_label}]\n"
    txt += f"조회일시: {now} / 총 {len(rows)}개\n"
    txt += "=" * 60 + "\n\n"
    for i, (key, days, used, guild_name, created_at) in enumerate(rows, 1):
        status = f"사용됨 ({guild_name})" if used else "미사용"
        txt += f"{i:>3}. {key}  |  {days}일  |  {status}  |  생성: {created_at}\n"

    fname = f"license_list_{filter_val}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    file_data = discord.File(fp=io.BytesIO(txt.encode("utf-8")), filename=fname)

    # V2 컨테이너 내부에 파일 배치
    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"## 📋 라이센스 목록 ({filter_label})"),
        discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"현재 데이터베이스에 저장된 {len(rows)}개의 목록입니다."),
        discord.ui.File(file=file_data), # 컨테이너 안에 파일 배치
        accent_color=discord.Color.from_str("#5865F2")
    )
    view.add_item(container)

    await interaction.followup.send(view=view, ephemeral=True)
