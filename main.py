import discord
import asyncio # 비동기 작업을 위해 필요합니다.
# 다른 필요한 import 문들도 여기에 유지됩니다.

# --- 설정 (기본 유지) ---
# 기존 설정값 (CATEGORY_ID, ADMIN_ROLE_ID, VERIFY_ROLE_ID 등)이 여기에 있다고 가정합니다.
# 실제 코드에는 해당 설정값이 위에 정의되어 있어야 합니다.
CATEGORY_ID = 1455820042368450580 # 예시 값
ADMIN_ROLE_ID = 1455824154283606195 # 예시 값
VERIFY_ROLE_ID = 1456531768109961287 # 예시 값

# MyBot 클래스 정의
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"커맨드 동기화 완료: {self.user.name}")

bot = MyBot()

# --- TwicketControlView (이전에 정의된 대로 유지) ---
class TwicketControlView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(label="티켓닫기", style=discord.ButtonStyle.red, custom_id="close_ticket", emoji=discord.PartialEmoji(name="close", id=1455996415976407102))
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**티켓이 5초 후에 삭제됩니다**")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="거래진행", style=discord.ButtonStyle.green, custom_id="continue_trade", emoji=discord.PartialEmoji(name="check2", id=1455996406748942501))
    async def continue_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(view=self)
        embed = discord.Embed(title="거래 정보 확인", description="**거래 정보 수정 버튼을 눌러 로블 닉네임을 적어주세요\n두 분 모두 '계속진행'을 눌러야 다음 단계로 이동합니다**", color=0xffffff)
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1456321236643741728/IMG_0751.png"
        embed.set_image(url=img_url)
        await interaction.followup.send(embed=embed)


# --- EscrowDropdown: 충전문의 드롭다운 (수정된 부분) ---
class EscrowDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="입양하세요", description="입양하세요 충전 티켓을 생성합니다.", emoji="🧸", value="adopt_me"),
            discord.SelectOption(label="머더 미스터리", description="머더 미스터리 충전 티켓을 생성합니다.", emoji="🔪", value="murder_mystery"),
            # 나중에 추가하고 싶은 다른 게임 옵션도 여기에 추가할 수 있습니다.
        ]
        super().__init__(placeholder="충전할 게임을 선택하세요", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_game_value = self.values[0] # 사용자가 선택한 옵션의 value

        # 인증된 사용자인지 먼저 확인
        verify_role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if verify_role not in interaction.user.roles:
            await interaction.response.send_message("**인증된 사용자만 티켓을 열 수 있습니다**", ephemeral=True)
            return

        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(CATEGORY_ID)

        # 채널 이름 결정
        channel_name_prefix = ""
        if selected_game_value == "adopt_me":
            channel_name_prefix = "입양충전-"
        elif selected_game_value == "murder_mystery":
            channel_name_prefix = "머더충전-"
        else:
            # 예상치 못한 선택이 발생한 경우
            await interaction.response.send_message("선택하신 게임에 대한 티켓을 생성할 수 없습니다.", ephemeral=True)
            return

        ticket_channel_name = f"{channel_name_prefix}{user.name}"

        # 권한 설정
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
            guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # 티켓 채널 생성
        ticket_channel = await guild.create_text_channel(name=ticket_channel_name, category=category, overwrites=overwrites)
        
        await interaction.response.send_message(f"**{ticket_channel.mention} 채널이 생성되었습니다**", ephemeral=True)
        
        # 충전 안내 임베드는 동일하게 사용
        embed1 = discord.Embed(title="충전 안내", description=f"**티켓 생성자 = {user.mention}\n10분동안 충전 미진행시 자동으로 채널 삭제됩니다**", color=0xffffff)
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1456494848457572433/IMG_0753.png"
        embed1.set_image(url=img_url)
    
        view = TwicketControlView(owner_id=user.id)
        await ticket_channel.send(content=f"@everyone", embed=embed1, view=view)


# --- EscrowView: 충전 패널에 드롭다운 추가 ---
class EscrowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(EscrowDropdown()) # 드롭다운을 뷰에 추가합니다.

# --- 나머지 봇 명령어 및 코드 (기존대로 유지) ---
@bot.tree.command(name="game", description="로블록스 전용 플립 패널")
async def escrow_panel(interaction: discord.Interaction):
    # 1. 명령어 입력자에게만 보이는 완료 문구 전송
    await interaction.response.send_message("**DONE**", ephemeral=True)

    # 2. 실제 채널에 전송될 패널 임베드 설정
    embed = discord.Embed(
        title="로블록스 - GAME BOT", 
        description=(
            "**아이템을 베팅하여 아이템을 불려보세요**\n"
            "**아래 버튼을 눌려 충전진행 하시면됩니다**\n\n"
            "**┗   티켓 여시면 중개봇이 안내해줍니다**\n"
            "**┗   상호작용 오류시 문의부탁드려요**\n\n"
            "**[게임 이용약관](https://swnx.shop)         [디스코드 TOS](https://discord.com/terms)**"
        ), 
        color=0xffffff
    )

    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1456494848457572433/IMG_0753.png"
    embed.set_image(url=img_url)

    # 3. interaction.channel.send를 사용하여 실제 패널 전송
    await interaction.channel.send(embed=embed, view=EscrowView()) # EscrowView가 이제 드롭다운을 포함합니다.

# 이 외의 나머지 봇 코드는 기존대로 유지됩니다.
# 예를 들어 /verify 명령어와 관련된 모든 클래스 및 명령어 정의
# ...

if __name__ == "__main__":
    bot.run('YOUR_BOT_TOKEN') # 실제 봇 토큰으로 교체해주세요.
