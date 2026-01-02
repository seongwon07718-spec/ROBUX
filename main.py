import aiohttp # 파일 상단에 이 줄이 있는지 확인하세요

async def send_verify_webhook(user, roblox_name):
    # 관리자 채널의 웹훅 URL을 여기에 넣으세요
    WEBHOOK_URL = "여기에_실제_웹훅_주소를_넣으세요"
    
    async with aiohttp.ClientSession() as session:
        # discohook.Webhook 대신 discord.Webhook을 사용합니다.
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
        
        embed = discord.Embed(
            title="🛡️ 로블록스 - 신규 유저 인증",
            description=f"{user.mention}님이 인증을 완료했습니다.",
            color=0x58b9ff
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="디스코드", value=user.name, inline=True)
        embed.add_field(name="로블록스", value=roblox_name, inline=True)
        
        await webhook.send(embed=embed, username="인증 알림")
