import discord
import aiohttp
import time

# 관리자 채널의 웹훅 URL (반드시 정확한 URL을 입력하세요)
ADMIN_WEBHOOK_URL = "여기에_복사한_웹훅_URL_붙여넣기"

async def send_verify_webhook(user, roblox_name):
    # aiohttp 세션을 열어 웹훅 전송
    async with aiohttp.ClientSession() as session:
        try:
            # discord.py 내장 웹훅 기능 사용
            webhook = discord.Webhook.from_url(ADMIN_WEBHOOK_URL, session=session)
            
            embed = discord.Embed(
                title="🛡️ 신규 유저 인증 완료",
                description=f"새로운 유저가 인증을 마쳤습니다.",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="디스코드", value=f"{user.mention} ({user.name})", inline=True)
            embed.add_field(name="로블록스", value=f"**{roblox_name}**", inline=True)
            embed.add_field(name="인증 시간", value=f"<t:{int(time.time())}:F>", inline=False)
            
            # 웹훅 전송
            await webhook.send(embed=embed, username="인증 알림 봇")
            print(f"웹훅 전송 성공: {user.name}")
            
        except Exception as e:
            print(f"웹훅 전송 중 에러 발생: {e}")
