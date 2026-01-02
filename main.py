import discohook
import asyncio

# 관리자 채널의 웹훅 URL
ADMIN_WEBHOOK_URL = "여기에_웹훅_URL_입력"

async def send_verify_webhook(user, roblox_name):
    # 1. 클라이언트 생성 (비동기 세션 방식)
    # discohook 라이브러리의 Webhook.from_url을 사용합니다.
    fh_webhook = discohook.Webhook.from_url(ADMIN_WEBHOOK_URL)

    # 2. 임베드 생성 (discohook 라이브러리 방식)
    embed = discohook.Embed(
        title="🛡️ 로블록스 인증 완료",
        description=f"{user.mention}님이 인증을 완료했습니다.",
        color=0x58b9ff
    )
    
    embed.add_field(name="디스코드 이름", value=user.name, inline=True)
    embed.add_field(name="로블록스 닉네임", value=roblox_name, inline=True)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text="Der System GAME")

    # 3. 전송
    # discohook 라이브러리는 .send()를 통해 메시지를 전송합니다.
    await fh_webhook.send(embed=embed)
