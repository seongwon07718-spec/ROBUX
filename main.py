import aiohttp

# 관리자 채널의 웹훅 URL을 입력하세요
ADMIN_WEBHOOK_URL = "여기에_디스코드_웹훅_URL_입력"

async def send_verify_webhook(user, roblox_name):
    async with aiohttp.ClientSession() as session:
        webhook_data = {
            "embeds": [{
                "title": "🛡️ 신규 유저 인증 완료",
                "description": f"새로운 유저가 로블록스 인증을 완료했습니다.",
                "color": 0x00ff00, # 초록색
                "fields": [
                    {"name": "디스코드 계정", "value": f"{user.mention} ({user.name})", "inline": True},
                    {"name": "로블록스 닉네임", "value": f"**[{roblox_name}](https://www.roblox.com/users/profile?username={roblox_name})**", "inline": True},
                    {"name": "인증 일시", "value": f"<t:{int(time.time())}:F>", "inline": False}
                ],
                "thumbnail": {"url": user.display_avatar.url}
            }]
        }
        await session.post(ADMIN_WEBHOOK_URL, json=webhook_data)
