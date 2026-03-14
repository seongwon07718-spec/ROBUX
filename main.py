import aiohttp
import discord
from discord import app_commands

# --- [ 전역 설정 구역: 웹훅 URL을 여기에 미리 적어두세요 ] ---
WEBHOOK_CONFIG = {
    "일반": "https://discord.com/api/webhooks/...", # 일반 공지 채널 웹훅
    "중요": "https://discord.com/api/webhooks/...", # 중요 공지 채널 웹훅
    "업데이트": "https://discord.com/api/webhooks/..." # 업데이트 전용 웹훅
}
# --------------------------------------------------

@bot.tree.command(name="업데이트_공지", description="설정된 웹훅으로 공지를 전송합니다")
@app_commands.describe(타입="공지 종류를 선택하세요", 내용="공지할 내용을 입력하세요 (\\n으로 줄바꿈)")
@app_commands.choices(타입=[
    app_commands.Choice(name="일반 공지", value="일반"),
    app_commands.Choice(name="중요 공지 (Everyone 언급)", value="중요"),
    app_commands.Choice(name="업데이트 소식", value="업데이트")
])
async def update_notice_fixed(it: discord.Interaction, 타입: str, 내용: str):
    if not it.user.guild_permissions.administrator:
        return await it.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)

    # 1. 설정된 URL 가져오기
    target_url = WEBHOOK_CONFIG.get(타입)
    if not target_url or "http" not in target_url:
        return await it.response.send_message(f"❌ '{타입}'에 대한 웹훅 URL이 설정되지 않았습니다. 코드를 확인해주세요.", ephemeral=True)

    await it.response.defer(ephemeral=True)

    # 2. 내용 처리 및 Embed 디자인
    processed_content = 내용.replace("\\n", "\n")
    mention = "@everyone " if 타입 == "중요" else ""
    
    embed = discord.Embed(
        title=f"📢 [{타입}] 안내 드립니다",
        description=processed_content,
        color=0x3498db if 타입 != "중요" else 0xff0000, # 중요 공지는 빨간색
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=f"작성자: {it.user.display_name} | {타입} 시스템")
    if it.user.avatar:
        embed.set_author(name=it.user.display_name, icon_url=it.user.avatar.url)

    # 3. 전송 로직
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(target_url, session=session)
        try:
            await webhook.send(
                content=mention, 
                embed=embed,
                username=f"{타입} 알림 봇", # 웹훅 이름 자동 변경
                avatar_url=bot.user.avatar.url if bot.user.avatar else None
            )
            await it.followup.send(f"✅ [{타입}] 웹훅 전송 성공!", ephemeral=True)
        except Exception as e:
            await it.followup.send(f"❌ 전송 실패: {e}", ephemeral=True)
