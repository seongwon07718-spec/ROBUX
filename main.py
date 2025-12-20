import aiohttp
import asyncio

async def fetch_all(cookie):
    headers = {"Cookie": f".ROBLOSECURITY={cookie}"}
    async with aiohttp.ClientSession(headers=headers) as session:
        # 유저 기본 정보 가져오기
        async with session.get("https://users.roblox.com/v1/users/authenticated") as resp:
            if resp.status != 200: return None
            user_data = await resp.json()
        
        user_id = user_data.get('id')
        
        # 병렬 요청 (속도 최적화)
        tasks = [
            session.get("https://economy.roblox.com/v1/user/currency"),
            session.get(f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership")
        ]
        results = await asyncio.gather(*tasks)
        
        robux_data = await results[0].json()
        premium_data = await results[1].json()
        
        return {
            "name": user_data.get('name'),
            "id": user_id,
            "robux": robux_data.get('robux', 0),
            "premium": premium_data
        }
