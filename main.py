# --- [ 전역 설정 구역: 웹훅 URL 사전 등록 ] ---
WEBHOOK_CONFIG = {
    "공지": "https://discord.com/api/webhooks/...", # 공지 채널 웹훅 URL
}
# --------------------------------------------------

@bot.tree.command(name="업데이트_공지", description="설정된 웹훅으로 컨테이너 공지를 전송합니다")
@app_commands.describe(내용="공지할 내용을 입력하세요 (\\n으로 줄바꿈)")
async def update_notice_container(it: discord.Interaction, 내용: str):
    if not it.user.guild_permissions.administrator:
        return await it.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)

    # 1. 설정된 웹훅 URL 확인
    target_url = WEBHOOK_CONFIG.get("공지")
    if not target_url or "http" not in target_url:
        return await it.response.send_message("❌ 웹훅 URL이 설정되지 않았습니다. 코드 상단을 확인해주세요.", ephemeral=True)

    await it.response.defer(ephemeral=True)

    # 2. 컨테이너 디자인 구성 (자판기 UI와 동일)
    notice_con = ui.Container(ui.TextDisplay("## 📢 업데이트 안내"), accent_color=0x3498db)
    notice_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    # 줄바꿈 처리
    processed_content = 내용.replace("\\n", "\n")
    notice_con.add_item(ui.TextDisplay(processed_content))
    
    notice_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    notice_con.add_item(ui.TextDisplay(f"-# 작성자: {it.user.display_name} | 일시: {time.strftime('%Y-%m-%d %H:%M')}"))

    # 3. 웹훅을 통해 LayoutView 전송
    async with aiohttp.ClientSession() as session:
        # 웹훅 객체 생성
        webhook = discord.Webhook.from_url(target_url, session=session)
        try:
            # 컨테이너를 LayoutView에 담아서 전송
            view = ui.LayoutView().add_item(notice_con)
            
            await webhook.send(
                content="@everyone", # 멘션 포함
                view=view,
                username="업데이트 알림",
                avatar_url=bot.user.avatar.url if bot.user.avatar else None
            )
            await it.followup.send("✅ 컨테이너 공지가 웹훅으로 전송되었습니다.", ephemeral=True)
        except Exception as e:
            await it.followup.send(f"❌ 전송 실패: {e}", ephemeral=True)
