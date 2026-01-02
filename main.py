# --- 티켓 제어 뷰 (티켓 채널 내부용) ---
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="티켓 닫기", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("***티켓이 5초 후에 삭제됩니다.***", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- 티켓 생성 뷰 (패널용) ---
class TicketLaunchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="티켓 열기", style=discord.ButtonStyle.primary, custom_id="open_ticket", emoji="🎫")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        
        # 티켓이 생성될 카테고리 확인
        category = guild.get_channel(CATEGORY_ID)
        
        # 권한 설정: 티켓 생성자와 관리자만 보이게 설정
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
            guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # 채널 생성 (문의-디스코드ID 형식)
        channel_name = f"문의-{user.id}"
        
        # 이미 같은 이름의 채널이 있는지 체크 (중복 생성 방지 선택 사항)
        existing_channel = discord.utils.get(guild.channels, name=channel_name)
        if existing_channel:
            return await interaction.response.send_message(f"이미 생성된 티켓이 있습니다: {existing_channel.mention}", ephemeral=True)

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        await interaction.response.send_message(f"{ticket_channel.mention} 티켓이 생성되었습니다.", ephemeral=True)

        # 티켓 채널 내부 메시지
        embed = discord.Embed(
            title="🎫 문의 티켓",
            description=f"{user.mention}님, 무엇을 도와드릴까요?\n관리자가 확인하기 전까지 내용을 미리 남겨주세요.\n\n티켓을 닫으려면 아래 **티켓 닫기** 버튼을 눌러주세요.",
            color=discord.Color.blue()
        )
        await ticket_channel.send(content=f"{user.mention} @everyone", embed=embed, view=TicketControlView())

# --- /ticket_panel 명령어 ---
@bot.tree.command(name="ticket_panel", description="티켓 생성 패널을 전송합니다.")
@app_commands.checks.has_permissions(administrator=True) # 관리자만 사용 가능
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="고객센터 티켓 문의",
        description=(
            "도움이 필요하신가요?\n"
            "아래 버튼을 클릭하여 티켓을 생성해 주세요.\n\n"
            "**운영 시간**: 24시간 접수 가능"
        ),
        color=discord.Color.white()
    )
    # 이미지 주소가 있다면 추가 가능
    # embed.set_image(url="이미지링크")
    
    await interaction.response.send_message("패널을 전송했습니다.", ephemeral=True)
    await interaction.channel.send(embed=embed, view=TicketLaunchView())
