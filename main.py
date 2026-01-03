import aiohttp
import discord

# 봇 데이터 설정 (실제 로블록스 숫자 ID와 브섭 링크 입력)
BOT_DATA = {
    "머더 미스테리": [
        {"name": "머더봇 01", "id": "123456789", "link": "https://www.roblox.com/..."},
        {"name": "머더봇 02", "id": "234567890", "link": "https://www.roblox.com/..."}
    ],
    "입양하세요": [
        {"name": "입양봇 01", "id": "345678901", "link": "https://www.roblox.com/..."}
    ]
}

async def get_bot_status(roblox_id):
    """로블록스 API로 봇의 실시간 접속 여부 확인"""
    url = "https://presence.roblox.com/v1/presence/users"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"userIds": [int(roblox_id)]}) as resp:
            data = await resp.json()
            if data and "userPresences" in data:
                # Type 2(온라인), 3(게임중)이면 접속중으로 판단
                return data["userPresences"][0].get("userPresenceType") in [2, 3]
    return False

class BotStatusSelect(discord.ui.Select):
    def __init__(self, category, options):
        super().__init__(placeholder=f"{category} 전용 봇을 선택하세요...", options=options)
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        # 선택한 봇의 브섭 링크 찾기
        selected_name = self.values[0].split(" ")[1] # 이모지 제외 이름만 추출
        bot_list = BOT_DATA.get(self.category, [])
        target = next((b for b in bot_list if b["name"] in selected_name), None)
        
        if target:
            embed = discord.Embed(title="🚀 브이아이피 서버 접속 안내", color=0x00ff00)
            embed.description = f"**{target['name']}** 서버로 이동합니다.\n\n[여기를 클릭하여 입장하기]({target['link']})"
            await interaction.response.send_message(embed=embed, ephemeral=True)

# 사진 34번의 EscrowDropdown 내부에 추가할 콜백 로직
async def callback(self, interaction: discord.Interaction):
    game_choice = self.values[0] # '머더 미스테리' 또는 '입양하세요'
    await interaction.response.defer(ephemeral=True) # API 조회 시간 벌기

    bot_options = []
    for bot in BOT_DATA.get(game_choice, []):
        is_online = await get_bot_status(bot["id"])
        emoji = "🟢" if is_online else "🔴"
        status_txt = "접속 중" if is_online else "미접속"
        
        bot_options.append(discord.SelectOption(
            label=f"{emoji} {bot['name']}",
            description=f"현재 {status_txt} 상태입니다.",
            value=f"{emoji} {bot['name']}"
        ))

    embed = discord.Embed(
        title="🤖 충전할 봇을 선택해주세요",
        description=f"선택하신 **{game_choice}**의 봇 목록입니다.\n🟢은 즉시 이용 가능, 🔴은 대기 중입니다.",
        color=0xffffff
    )
    
    view = discord.ui.View()
    view.add_item(BotStatusSelect(game_choice, bot_options))
    
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
