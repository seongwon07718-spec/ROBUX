class EscrowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="중개문의 티켓열기", style=discord.ButtonStyle.gray, custom_id="start_escrow", emoji=discord.PartialEmoji(name="enable", id=1455996417335365643))
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # (기존 티켓 생성 로직 유지)
        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
            guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        ticket_channel = await guild.create_text_channel(name=f"중개-{user.name}", category=category, overwrites=overwrites)
        await interaction.response.send_message(f"**{ticket_channel.mention} 채널이 생성되었습니다**", ephemeral=True)
        
        embed1 = discord.Embed(title="중개 안내", description=f"**티켓 생성자 = {user.mention}\n┗ 10분동안 거래 미진행시 자동으로 채널 삭제됩니다**", color=0xffffff)
        embed2 = discord.Embed(description="**상대방의 유저 ID를 입력해주세요\n┗ 숫자만 입력해주세요 (예: 123456789012345678)**", color=0xffffff)
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1455922358417358848/IMG_0741.png"
        embed2.set_image(url=img_url)
        await ticket_channel.send(content=f"@everyone", embed=embed1)
        await ticket_channel.send(view=TicketControlView(user.id), embed=embed2)

    # --- [새로 추가된 중개방식 버튼] ---
    @discord.ui.button(label="중개방식 확인", style=discord.ButtonStyle.secondary, emoji="❓")
    async def trade_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 버튼을 누른 사람에게만 보이는 안내 문구
        guide_embed = discord.Embed(
            title="❓ 중개 방식 안내",
            description=(
                "**1. 티켓 생성 및 상대방 초대**\n"
                "┗ 하단 버튼으로 티켓을 열고 거래 상대방의 ID를 입력해 초대합니다.\n\n"
                "**2. 봇 자동화 접속**\n"
                "┗ 거래 정보를 입력하면 봇이 전용 서버로 접속하여 대기합니다.\n\n"
                "**3. 아이템 전달 및 검수**\n"
                "┗ 판매자가 봇에게 아이템을 주면 봇이 스크린샷을 찍어 디스코드에 올립니다.\n\n"
                "**4. 구매자 확인 및 송금**\n"
                "┗ 구매자가 아이템을 확인한 뒤 '수락'을 누르면 봇이 템을 받고 거래가 종료됩니다."
            ),
            color=0xffffff
        )
        await interaction.response.send_message(embed=guide_embed, ephemeral=True)

# --- [커맨드 부분] ---
@bot.tree.command(name="amp_panel", description="입양 중개 패널 전송")
async def escrow_panel(interaction: discord.Interaction):
    # 본인에게만 전송 완료 알림
    await interaction.response.send_message("**✅ 중개 패널을 전송했습니다.**", ephemeral=True)

    embed = discord.Embed(
        title="자동중개 - AMP 전용", 
        description="**안전 거래하기 위해서는 중개가 필수입니다\n아래 버튼을 눌려 중개 절차를 시작해주세요\n\n┗ 티켓 여시면 중개봇이 안내해줍니다\n┗ 상호작용 오류시 문의부탁드려요**", 
        color=0xffffff
    )
    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1455922358417358848/IMG_0741.png"
    embed.set_image(url=img_url)
    
    # 수정된 EscrowView 전송 (버튼 2개가 포함됨)
    await interaction.channel.send(embed=embed, view=EscrowView())
