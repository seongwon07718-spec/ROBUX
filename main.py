import discord
import asyncio
from discord import app_commands
from discord.ext import commands

# 설정
CATEGORY_ID = 1455820042368450580  # 중개 티켓이 생성될 카테고리 ID
ADMIN_ROLE_ID = 1455824154283606195  # 중개 관리자 역할 ID

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
                    await message.channel.send(embed=discord.Embed(description=f"**{target_user.mention}님이 초대되었습니다**", color=0xffffff))
                except:
                    pass
        await self.process_commands(message)

bot = MyBot()

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        @discord.ui.button(label="티켓닫기", style=discord.ButtonStyle.red, custom_id="close_ticket")
        async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("**티켓이 5초 후에 삭제됩니다**")
            await asyncio.sleep(5)
            await interaction.channel.delete()

        @discord.ui.button(label="거래진행", style=discord.ButtonStyle.green, custom_id="continue_trade")
        async def continue_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("**거래가 계속 진행됩니다**")
            button.disabled = True
            await interaction.message.edit(view=self)

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
        await interaction.response.send_message(f"**{ticket_channel.mention} 채널이 생성되었습니다**", ephemeral=True)

        # 임베드 1: 이용 안내
        embed1 = discord.Embed(
            title="중개 티켓 안내",
            description=f"**티켓 생성자 = {user.mention}\n\n티켓 생성 완료\n┗ 10분동안 거래 미진행시 자동으로 채널 삭제됩니다**",
            color=0xffffff
        )
        # 임베드 2: 유저 초대 안내
        embed2 = discord.Embed(
            description="**상대방의 유저 ID를 입력해주세요\n┗ 유저 ID는 상대방 프로필 우클릭 후 'ID 복사'로 확인 가능합니다\n┗ 숫자만 입력해주세요 (예: 123456789012345678)**",
            color=0xffffff
        )
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1455875683703193711/IMG_0728.png?ex=69565163&is=6954ffe3&hm=cfe6eb46fbdded19351688d874402fa4b8ceaf1d7624aec0a3d4594f07656793&"
        embed2.set_image(url=img_url)

        await ticket_channel.send(content=f"@everyone", embed=embed1)
        await ticket_channel.send(view=TicketControlView(), embed=embed2)

# 중개 커맨드 설정
@bot.tree.command(name="muddleman", description="중개 패널 전송")
async def escrow_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="자동중개 - AMP 전용",
        description=(
            "**안전 거래하기 위해서는 중개가 필수입니다\n아래 버튼을 눌려 중개 절차를 시작해주세요\n\n┗ 티켓 여시면 중개봇이 안내해줍니다\n┗ 상호작용 오류시 문의부탁드려요\n\n[중개 이용약관](https://swnx.shop)      [디스코드 TOS](https://discord.com/terms)**"
        ),
        color=0xffffff
    )
    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1455875683703193711/IMG_0728.png?ex=69565163&is=6954ffe3&hm=cfe6eb46fbdded19351688d874402fa4b8ceaf1d7624aec0a3d4594f07656793&"
    embed.set_image(url=img_url)

    await interaction.response.send_message(embed=embed, view=EscrowView())

if __name__ == "__main__":
    bot.run('') # 토큰을 입력하세요
