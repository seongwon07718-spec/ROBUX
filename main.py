import discord
from discord import app_commands
from discord.ext import commands

# 설정
CATEGORY_ID = 1455820042368450580  # 중개 티켓이 생성될 카테고리 ID
ADMIN_ROLE_ID = 1454398431996018724  # 중개 관리자 역할 ID

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"커맨드 동기화 완료: {self.user.name}")

    # 추가: 유저 ID 입력 시 자동 초대 로직
    async def on_message(self, message):
        if message.author.bot: return
        if isinstance(message.channel, discord.TextChannel) and message.channel.name.startswith("중개-"):
            if message.content.isdigit() and 17 <= len(message.content) <= 20:
                try:
                    target_user = await message.guild.fetch_member(int(message.content))
                    await message.channel.set_permissions(target_user, read_messages=True, send_messages=True, embed_links=True, attach_files=True)
                    await message.channel.send(embed=discord.Embed(description=f"✅ {target_user.mention}님이 초대되었습니다.", color=0x00ff00))
                except:
                    pass
        await self.process_commands(message)

bot = MyBot()

class EscrowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="중개문의 티켓열기", 
        style=discord.ButtonStyle.gray, 
        custom_id="start_escrow",
        emoji="<:emoji_2:1455814454490038305>"
    )
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # 티켓 채널 생성 로직
        category = guild.get_channel(CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
            guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        ticket_channel = await guild.create_text_channel(name=f"중개-{user.name}", category=category, overwrites=overwrites)
        await interaction.response.send_message(f"✅ {ticket_channel.mention} 채널이 생성되었습니다.", ephemeral=True)

        # 임베드 1: 이용 안내
        embed1 = discord.Embed(
            title="🛡️ 중개 거래 안내",
            description="본 시스템은 봇이 아이템을 보관한 뒤 거래를 확정하는 방식입니다.\n관리자의 지시가 있기 전까지 아이템을 넘기지 마세요.",
            color=0xffffff
        )
        # 임베드 2: 유저 초대 안내
        embed2 = discord.Embed(
            title="👤 거래 상대방 초대",
            description="거래를 진행할 **상대방의 유저 ID(숫자)**를 입력해주세요.\n봇이 자동으로 상대방을 이 채널에 초대합니다.",
            color=0xffffff
        )
        
        await ticket_channel.send(embed=embed1)
        await ticket_channel.send(content=f"{user.mention}", embed=embed2)

# 중개 커맨드 설정
@bot.tree.command(name="입양중개", description="입양 중개 패널 전송")
async def escrow_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="자동중개 - AMP 전용",
        description=(
            "**안전 거래하기 위해서는 중개가 필수입니다\n아래 버튼을 눌려 중개 절차를 시작해주세요\n\n┗ 티켓 여시면 중개봇이 안내해줍니다\n┗ 상호작용 오류시 문의부탁드려요\n\n[중개 이용약관](https://swnx.shop)      [디스코드 TOS](https://discord.com/terms)**"
        ),
        color=0xffffff
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1455811337937747989/IMG_0723.png?ex=69561576&is=6954c3f6&hm=daf60069947d93e54dcb3b85facb151b9ecea1de76c234b91e68c36d997384b2&")
    
    await interaction.response.send_message(embed=embed, view=EscrowView())

if __name__ == "__main__":
    bot.run('YOUR_TOKEN_HERE') # 토큰을 입력하세요
