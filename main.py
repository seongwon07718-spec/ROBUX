@bot.tree.command(name="인증하기", description="인증하기 컨테이너를 전송합니다")
async def authenticate(it: discord.Interaction):
    # 1. 컨테이너 및 디자인 설정
    res_con = ui.Container()
    res_con.accent_color = 0xffffff  # 화이트 액센트
    
    res_con.add_item(ui.TextDisplay("## 인증하기"))
    res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    res_con.add_item(ui.TextDisplay(
        "아래 버튼을 눌러 인증하셔야 서버 이용 가능합니다\n"
        "**`IP, 이메일, 통신사`** 등은 일절 수집하지 않습니다."
    ))
    res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    # 2. OAuth2 인증 URL 생성
    auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds.join"
        f"&state={it.guild_id}"
    )
    
    # 3. 버튼 추가 (사용자님의 커스텀 이모지 유지)
    auth_btn = ui.Button(
        label="인증하기", 
        url=auth_url, 
        style=discord.ButtonStyle.link, 
        emoji="<:emoji_14:1484745886696476702>"
    )
    res_con.add_item(ui.ActionRow(auth_btn))

    # 4. 레이아웃 뷰 생성 및 전송
    view = ui.LayoutView().add_item(res_con)
    
    # "인증하기가 전송되었습니다" 메시지와 함께 컨테이너 전송
    await it.response.send_message(
        content="✅ 인증하기가 전송되었습니다.", 
        view=view, 
        ephemeral=False
    )
