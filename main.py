import discord
import asyncio
from discord import app_commands
from discord.ext import commands

# 설정
CATEGORY_ID = 1455820042368450580
ADMIN_ROLE_ID = 1455824154283606195

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"커맨드 동기화 완료: {self.user.name}")

    async def on_message(self, message):
        if message.author.bot: return
        if isinstance(message.channel, discord.TextChannel) and message.channel.name.startswith("중개-"):
            # 입력된 내용이 17~20자리 숫자(ID)인 경우
            if message.content.isdigit() and 17 <= len(message.content) <= 20:
                try:
                    target_user = await message.guild.fetch_member(int(message.content))
                    # 채널 권한 부여
                    await message.channel.set_permissions(target_user, read_messages=True, send_messages=True, embed_links=True, attach_files=True)
                    
                    # 초대된 유저 ID 저장 (Topic 활용)
                    await message.channel.edit(topic=f"invited:{target_user.id}")
                    
                    # 1. 초대 성공 임베드 전송 (10초 뒤 자동 삭제)
                    success_msg = await message.channel.send(
                        embed=discord.Embed(description=f"**{target_user.mention}님이 초대되었습니다**", color=0xffffff),
                        delete_after=10.0 # 10초 후 삭제
                    )
                    
                    # 2. 유저가 입력한 ID 숫자 메시지도 삭제 (선택 사항)
                    try:
                        await message.delete(delay=10.0)
                    except:
                        pass # 봇에게 메시지 관리 권한이 없을 경우 대비
                        
                except Exception as e:
                    # 유저를 찾지 못했을 때 안내 (이것도 5초 뒤 삭제)
                    fail_msg = await message.channel.send(f"**유저를 찾을 수 없습니다: {e}**", delete_after=5.0)
        
        await self.process_commands(message)

bot = MyBot()

# --- 거래 정보 입력 모달 (필수 입력 해제 및 데이터 보존) ---
class InfoModal(discord.ui.Modal, title="거래 정보 입력"):
    # required=False로 설정하여 자기 것만 적을 수 있게 함
    seller = discord.ui.TextInput(label="판매자 로블록스 닉네임", placeholder="본인이 판매자라면 입력해주세요", required=False)
    buyer = discord.ui.TextInput(label="구매자 로블록스 닉네임", placeholder="본인이 구매자라면 입력해주세요", required=False)

    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view
        # 기존에 입력된 값이 있다면 모달창에 미리 표시
        if self.original_view.seller_nick: self.seller.default = self.original_view.seller_nick
        if self.original_view.buyer_nick: self.buyer.default = self.original_view.buyer_nick

    async def on_submit(self, interaction: discord.Interaction):
        # 입력된 값이 있을 때만 업데이트 (비워두면 기존 값 유지)
        if self.seller.value: self.original_view.seller_nick = self.seller.value
        if self.buyer.value: self.original_view.buyer_nick = self.buyer.value
        
        # 판매자와 구매자 정보가 모두 존재할 때만 '계속진행' 버튼 활성화
        if self.original_view.seller_nick and self.original_view.buyer_nick:
            for child in self.original_view.children:
                if child.label == "계속진행":
                    child.disabled = False
        
        embed = discord.Embed(color=0xffffff)
        embed.add_field(name="판매자", value=f"```{self.original_view.seller_nick or '미입력'}```", inline=True)
        embed.add_field(name="구매자", value=f"```{self.original_view.buyer_nick or '미입력'}```", inline=True)
        embed.description = f"**진행 현황 = ({len(self.original_view.confirmed_users)}/2) 확인 완료**"
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1455875683703193711/IMG_0728.png"
        embed.set_image(url=img_url)
        await interaction.response.edit_message(embed=embed, view=self.original_view)

# --- 거래 단계 뷰 ---
class TradeStepView(discord.ui.View):
    def __init__(self, owner_id, target_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.target_id = target_id
        self.confirmed_users = set()
        self.seller_nick = "미입력"
        self.buyer_nick = "미입력"

    @discord.ui.button(label="거래정보 수정", style=discord.ButtonStyle.secondary)
    async def edit_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InfoModal(self))

    @discord.ui.button(label="계속진행", style=discord.ButtonStyle.gray)
    async def confirm_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.owner_id, self.target_id]:
            return await interaction.response.send_message("**거래 당사자만 누를 수 있습니다**", ephemeral=True)
        
        self.confirmed_users.add(interaction.user.id)
        
        if len(self.confirmed_users) >= 2:
            # 두 명 다 눌렀을 때
            button.disabled = True
            await interaction.response.edit_message(content="**두 명 모두 확인되었습니다\n봇이 아이템을 전달받을 준비를 합니다**", view=self)
        else:
            # 한 명만 눌렀을 때
            embed = interaction.message.embeds[0]
            embed.description = f"**진행 현황 = ({len(self.confirmed_users)}/2) 확인 완료**"
            await interaction.response.edit_message(embed=embed, view=self)

# --- 티켓 제어 뷰 (초기) ---
class TicketControlView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(label="티켓닫기", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**티켓이 5초 후에 삭제됩니다**")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="거래진행", style=discord.ButtonStyle.green, custom_id="continue_trade")
    async def continue_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 상대방 초대 여부 확인 (Topic에 저장된 ID 추출)
        topic = interaction.channel.topic
        if not topic or "invited:" not in topic:
            return await interaction.response.send_message("**상대방을 먼저 초대해야 거래를 진행할 수 있습니다**", ephemeral=True)
        
        target_id = int(topic.split(":")[1])
        
        # 버튼 상태 변경
        button.disabled = True
        # 티켓닫기 버튼 찾아서 비활성화 (보통 첫 번째 버튼)
        for child in self.children:
            if child.custom_id == "close_ticket":
                child.disabled = True
        
        await interaction.response.edit_message(view=self)
        
        # 새 거래 진행 임베드와 버튼 전송
        embed = discord.Embed(
            title="거래 정보 확인",
            description="**거래 정보 수정 버튼을 눌러 닉네임을 적어주세요\n두 분 모두 '계속진행'을 눌러야 다음 단계로 이동합니다**",
            color=0xffffff
        )
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1455875683703193711/IMG_0728.png"
        embed.set_image(url=img_url)
        await interaction.followup.send(embed=embed, view=TradeStepView(self.owner_id, target_id))

class EscrowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="중개문의 티켓열기", style=discord.ButtonStyle.gray, custom_id="start_escrow", emoji="<:emoji_2:1455814454490038305>")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
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

        embed1 = discord.Embed(title="중개 티켓 안내", description=f"**티켓 생성자 = {user.mention}\n\n티켓 생성 완료\n┗ 10분동안 거래 미진행시 자동으로 채널 삭제됩니다**", color=0xffffff)
        embed2 = discord.Embed(description="**상대방의 유저 ID를 입력해주세요\n┗ 숫자만 입력해주세요 (예: 123456789012345678)**", color=0xffffff)
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1455875683703193711/IMG_0728.png"
        embed2.set_image(url=img_url)

        await ticket_channel.send(content=f"@everyone", embed=embed1)
        await ticket_channel.send(view=TicketControlView(user.id), embed=embed2)

@bot.tree.command(name="muddleman", description="중개 패널 전송")
async def escrow_panel(interaction: discord.Interaction):
    embed = discord.Embed(title="자동중개 - AMP 전용", description="**안전 거래하기 위해서는 중개가 필수입니다\n아래 버튼을 눌려 중개 절차를 시작해주세요\n\n┗ 티켓 여시면 중개봇이 안내해줍니다\n┗ 상호작용 오류시 문의부탁드려요\n\n[중개 이용약관](https://swnx.shop) / [디스코드 TOS](https://discord.com/terms)**", color=0xffffff)
    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1455875683703193711/IMG_0728.png"
    embed.set_image(url=img_url)
    await interaction.response.send_message(embed=embed, view=EscrowView())

if __name__ == "__main__":
    bot.run('')
