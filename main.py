@bot.tree.command(name="인증하기", description="인증하기 컨테이너를 전송합니다")
async def authenticate(it: discord.Interaction):
    res_con = ui.Container()
    res_con.accent_color = 0xffffff 
    
    res_con.add_item(ui.TextDisplay("## 인증하기"))
    res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    res_con.add_item(ui.TextDisplay(
        "아래 버튼을 눌려 인증하셔야 서버 이용 가능합니다\n"
        "`IP, 이메일, 통신사` 등 일절 수집 안 합니다"
    ))
    res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds.join"
        f"&state={it.guild_id}"
    )
    
    auth_btn = ui.Button(label="인증하기", url=auth_url, style=discord.ButtonStyle.link, emoji="<:emoji_14:1484745886696476702>")
    res_con.add_item(ui.ActionRow(auth_btn))

    view = ui.LayoutView().add_item(res_con)
    await it.response.send_message(view=view, ephemeral=False)
