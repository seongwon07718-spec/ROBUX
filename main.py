import discord

class EscrowDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="충전문의 티켓열기", description="충전 문의 티켓을 생성합니다.", emoji="💳"),
            # 추가 옵션을 원하면 여기에 더 넣으세요
        ]
        super().__init__(placeholder="원하는 작업을 선택하세요", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "충전문의 티켓열기":
            verify_role = interaction.guild.get_role(VERIFY_ROLE_ID)
            if verify_role not in interaction.user.roles:
                await interaction.response.send_message("**인증된 사용자만 티켓을 열 수 있습니다**", ephemeral=True)
                return

            guild = interaction.guild
            user = interaction.user
            category = guild.get_channel(CATEGORY_ID)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
                guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            ticket_channel = await guild.create_text_channel(name=f"충전-{user.name}", category=category, overwrites=overwrites)
            await interaction.response.send_message(f"**{ticket_channel.mention} 채널이 생성되었습니다**", ephemeral=True)
            
            embed1 = discord.Embed(title="충전 안내", description=f"**티켓 생성자 = {user.mention}\n10분동안 충전 미진행시 자동으로 채널 삭제됩니다**", color=0xffffff)
            embed1.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1456494848457572433/IMG_0753.png")
            view = TwicketControlView(owner_id=user.id)
            await ticket_channel.send(content=f"@everyone", embed=embed1, view=view)

class EscrowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(EscrowDropdown())
