import aiohttp
import discord

# 봇의 로블록스 ID 및 정보 설정
BOT_DATA = {
    "머더": [
        {"name": "머더 봇 1호기", "id": "12345678", "link": "https://www.roblox.com/games/share/브섭1"},
        {"name": "머더 봇 2호기", "id": "23456789", "link": "https://www.roblox.com/games/share/브섭2"}
    ],
    "입양": [
        {"name": "입양 봇 1호기", "id": "34567890", "link": "https://www.roblox.com/games/share/브섭3"}
    ]
}

async def check_online(roblox_id):
    """로블록스 API로 봇의 실시간 접속 상태를 확인합니다."""
    url = "https://presence.roblox.com/v1/presence/users"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"userIds": [int(roblox_id)]}) as resp:
            data = await resp.json()
            if data and "userPresences" in data:
                # Type 2(웹/앱 접속), 3(게임 중) 일 때 접속 중으로 간주
                status = data["userPresences"][0].get("userPresenceType")
                return status in [2, 3]
    return False

class BotDropdown(discord.ui.Select):
    def __init__(self, category, options):
        self.category = category
        self.bot_info = options # 선택 시 링크 연결을 위해 저장
        super().__init__(
            placeholder="충전할 봇을 선택해 주세요...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # 선택한 봇의 링크 찾기
        selected_bot = next((bot for bot in BOT_DATA[self.category] if bot["name"] in self.values[0]), None)
        
        if selected_bot:
            embed = discord.Embed(title="🚀 브이아이피 서버 안내", color=0x00ff00)
            embed.description = f"**{selected_bot['name']}**이 대기 중인 서버입니다.\n\n[여기를 클릭하여 입장하기]({selected_bot['link']})"
            await interaction.response.send_message(embed=embed, ephemeral=True)

class BotSelectView(discord.ui.View):
    def __init__(self, category, dropdown_options):
        super().__init__(timeout=60)
        self.add_item(BotDropdown(category, dropdown_options))

# 드롭바 선택 시 실행될 메인 로직
async def show_bot_selector(interaction: discord.Interaction, category: str):
    """카테고리(머더/입양)에 따른 봇 목록을 드롭다운으로 표시합니다."""
    
    # 1. 즉시 응답 지연 (API 호출 시간 벌기)
    await interaction.response.defer(ephemeral=True)
    
    dropdown_options = []
    
    # 2. 봇들의 실시간 상태를 체크하여 옵션 생성
    for bot in BOT_DATA.get(category, []):
        is_online = await check_online(bot["id"])
        emoji = "🟢" if is_online else "🔴"
        status_text = "접속 중" if is_online else "미접속"
        
        # 미접속인 경우 옵션을 비활성화하고 싶다면 아래 주석 해제 (단, 전체 드롭다운은 열림)
        dropdown_options.append(discord.SelectOption(
            label=f"{emoji} {bot['name']}",
            description=f"현재 상태: {status_text}",
            value=f"{bot['name']}"
        ))

    # 3. 임베드와 함께 드롭다운 전송
    embed = discord.Embed(
        title="🤖 충전할 봇을 선택해주세요",
        description=f"아래 드롭다운에서 **{category}** 전용 봇을 선택하세요.\n(🟢: 접속 중 / 🔴: 미접속)",
        color=0xffffff
    )
    
    await interaction.followup.send(embed=embed, view=BotSelectView(category, dropdown_options), ephemeral=True)
