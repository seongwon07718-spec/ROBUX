import discord
import asyncio
import aiohttp # 로블록스 API 통신용
import re # 닉네임 정규식 검사
from discord import app_commands
from discord.ext import commands

# 설정
CATEGORY_ID = 1455820042368450580
ADMIN_ROLE_ID = 1455824154283606195

# --- 로블록스 닉네임 유효성 검사 함수 ---
async def check_roblox_user(username):
    # 영어, 숫자, _ 만 허용하며 3글자 이상인지 확인
    if not re.match(r"^[A-Za-z0-9_]{3,}$", username):
        return None, "형식 불일치 (영어/숫자/_ 3자 이상)"
    
    url = "https://users.roblox.com/v1/usernames/users"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"usernames": [username], "excludeBannedUsers": True}) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data['data']:
                    return data['data'][0]['name'], "존재함" # 실제 대소문자 구분된 이름 반환
                else:
                    return None, "존재하지 않는 닉네임"
            return None, "API 오류"

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
            if message.content.isdigit() and 17 <= len(message.content) <= 20:
                try:
                    target_user = await message.guild.fetch_member(int(message.content))
                    await message.channel.set_permissions(target_user, read_messages=True, send_messages=True, embed_links=True, attach_files=True)
                    await message.channel.edit(topic=f"invited:{target_user.id}")
                    await message.channel.send(embed=discord.Embed(description=f"**{target_user.mention}님이 초대되었습니다**", color=0xffffff), delete_after=10.0)
                    try: await message.delete(delay=10.0)
                    except: pass
                except: pass
        await self.process_commands(message)

bot = MyBot()

# --- 거래 정보 입력 모달 ---
class InfoModal(discord.ui.Modal, title="거래 정보 입력"):
    seller = discord.ui.TextInput(label="판매자 로블록스 닉네임", placeholder="영어/숫자/_ 3자 이상", required=False)
    buyer = discord.ui.TextInput(label="구매자 로블록스 닉네임", placeholder="영어/숫자/_ 3자 이상", required=False)

    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view
        if self.original_view.seller_nick: self.seller.default = self.original_view.seller_nick
        if self.original_view.buyer_nick: self.buyer.default = self.original_view.buyer_nick

    async def on_submit(self, interaction: discord.Interaction):
        # 판매자 검사
        if self.seller.value:
            real_name, msg = await check_roblox_user(self.seller.value)
            if real_name: self.original_view.seller_nick = real_name
            else: self.original_view.seller_nick = f"❌ {msg}"
        
        # 구매자 검사
        if self.buyer.value:
            real_name, msg = await check_roblox_user(self.buyer.value)
            if real_name: self.original_view.buyer_nick = real_name
            else: self.original_view.buyer_nick = f"❌ {msg}"

        # 비활성화 오류 해결: 닉네임이 둘 다 "실제 존재"할 때만 비활성화를 풉니다.
        # (문자열에 '❌'가 포함되어 있지 않고 '미입력'이 아닐 때)
        s_ok = self.original_view.seller_nick and "❌" not in self.original_view.seller_nick and self.original_view.seller_nick != "미입력"
        b_ok = self.original_view.buyer_nick and "❌" not in self.original_view.buyer_nick and self.original_view.buyer_nick != "미입력"
        
        if s_ok and b_ok:
            self.original_view.confirm_trade_button.disabled = False
            self.original_view.confirm_trade_button.style = discord.ButtonStyle.green
        else:
            self.original_view.confirm_trade_button.disabled = True
            self.original_view.confirm_trade_button.style = discord.ButtonStyle.gray

        embed = discord.Embed(color=0xffffff)
        embed.add_field(name="판매자", value=f"```{self.original_view.seller_nick or '미입력'}```", inline=True)
        embed.add_field(name="구매자", value=f"```{self.original_view.buyer_nick or '미입력'}```", inline=True)
        embed.description = f"**진행 현황 = ({len(self.original_view.confirmed_users)}/2) 확인 완료**\n\n**⚠️ 반드시 실제 존재하는 닉네임을 입력해야 진행 버튼이 활성화됩니다.**"
        embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1455875683703193711/IMG_0728.png")
        
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
        # 버튼을 변수로 저장하여 직접 제어 (비활성화 오류 해결)
        self.confirm_trade_button.disabled = True

    @discord.ui.button(label="거래정보 수정", style=discord.ButtonStyle.secondary)
    async def edit_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InfoModal(self))

    @discord.ui.button(label="계속진행", style=discord.ButtonStyle.gray) # 초기엔 회색
    async def confirm_trade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.owner_id, self.target_id]:
            return await interaction.response.send_message("**거래 당사자만 누를 수 있습니다**", ephemeral=True)
        
        self.confirmed_users.add(interaction.user.id)
        
        if len(self.confirmed_users) >= 2:
            button.disabled = True
            await interaction.response.edit_message(content="**두 명 모두 확인되었습니다\n봇이 아이템을 전달받을 준비를 합니다**", view=self)
        else:
            embed = interaction.message.embeds[0]
            embed.description = f"**진행 현황 = ({len(self.confirmed_users)}/2) 확인 완료**"
            await interaction.response.edit_message(embed=embed, view=self)

# --- 이후 코드는 동일 (TicketControlView, EscrowView 등) ---
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
        topic = interaction.channel.topic
        if not topic or "invited:" not in topic:
            return await interaction.response.send_message("**상대방을 먼저 초대해야 거래를 진행할 수 있습니다**", ephemeral=True)
        target_id = int(topic.split(":")[1])
        button.disabled = True
        for child in self.children:
            if child.custom_id == "close_ticket": child.disabled = True
        await interaction.response.edit_message(view=self)
        
        embed = discord.Embed(title="거래 정보 확인", description="**거래 정보 수정 버튼을 눌러 닉네임을 적어주세요\n두 분 모두 '계속진행'을 눌러야 다음 단계로 이동합니다**", color=0xffffff)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1455875683703193711/IMG_0728.png")
        await interaction.followup.send(embed=embed, view=TradeStepView(self.owner_id, target_id))

class EscrowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="중개문의 티켓열기", style=discord.ButtonStyle.gray, custom_id="start_escrow", emoji="<:emoji_2:1455814454490038305>")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        ticket_channel = await guild.create_text_channel(name=f"중개-{user.name}", category=category, overwrites=overwrites)
        await interaction.response.send_message(f"**{ticket_channel.mention} 채널이 생성되었습니다**", ephemeral=True)
        embed1 = discord.Embed(title="중개 티켓 안내", description=f"**티켓 생성자 = {user.mention}\n\n티켓 생성 완료**", color=0xffffff)
        embed2 = discord.Embed(description="**상대방의 유저 ID를 입력해주세요**", color=0xffffff)
        embed2.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1455875683703193711/IMG_0728.png")
        await ticket_channel.send(content=f"@everyone", embed=embed1)
        await ticket_channel.send(view=TicketControlView(user.id), embed=embed2)

@bot.tree.command(name="muddleman", description="중개 패널 전송")
async def escrow_panel(interaction: discord.Interaction):
    embed = discord.Embed(title="자동중개 - AMP 전용", description="**버튼을 눌러 중개 절차를 시작해주세요**", color=0xffffff)
    embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1455875683703193711/IMG_0728.png")
    await interaction.response.send_message(embed=embed, view=EscrowView())

if __name__ == "__main__":
    bot.run('YOUR_TOKEN')
